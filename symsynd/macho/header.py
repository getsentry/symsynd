"""
Utilities for reading and writing Mach-O headers
"""
import sys
import struct

from .mtypes import (LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_PREBOUND_DYLIB,
                     LC_REEXPORT_DYLIB, FAT_MAGIC, MH_MAGIC, MH_CIGAM,
                     MH_MAGIC_64, MH_CIGAM_64, LC_REGISTRY, LC_ID_DYLIB,
                     LC_SEGMENT, LC_SEGMENT_64, S_ZEROFILL,
                     MH_FILETYPE_SHORTNAMES, mach_header, mach_header_64,
                     fat_header, fat_arch, load_command, section,
                     section_64, sizeof)
from .util import FileView


_RELOCATABLE = set((
    # relocatable commands that should be used for dependency walking
    LC_LOAD_DYLIB,
    LC_LOAD_WEAK_DYLIB,
    LC_PREBOUND_DYLIB,
    LC_REEXPORT_DYLIB,
))

_RELOCATABLE_NAMES = {
    LC_LOAD_DYLIB: 'load_dylib',
    LC_LOAD_WEAK_DYLIB: 'load_weak_dylib',
    LC_PREBOUND_DYLIB: 'prebound_dylib',
    LC_REEXPORT_DYLIB: 'reexport_dylib',
}


def _should_relocate_command(cmd):
    """Should this command id be investigated for relocation?"""
    return cmd in _RELOCATABLE


class MachO(object):
    """
    Provides reading/writing the Mach-O header of a specific existing file
    """
    #   filename   - the original filename of this mach-o
    #   sizediff   - the current deviation from the initial mach-o size
    #   header     - the mach-o header
    #   commands   - a list of (load_command, somecommand, data)
    #                data is either a str, or a list of segment structures
    #   total_size - the current mach-o header size (including header)
    #   low_offset - essentially, the maximum mach-o header size
    #   id_cmd     - the index of my id command, or None

    def __init__(self, filename):

        # supports the ObjectGraph protocol
        self.graphident = filename
        self.filename = filename

        # initialized by load
        self.fat = None
        self.headers = []
        with open(filename, 'rb') as fp:
            self.load(fp)

    def __repr__(self):
        return "<MachO filename=%r>" % (self.filename,)

    def load(self, fh):
        assert fh.tell() == 0
        header = struct.unpack('>I', fh.read(4))[0]
        fh.seek(0)
        if header == FAT_MAGIC:
            self.load_fat(fh)
        else:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(0)
            self.load_header(fh, 0, size)

    def load_fat(self, fh):
        self.fat = fat_header.from_fileobj(fh)
        archs = [fat_arch.from_fileobj(fh) for i in range(self.fat.nfat_arch)]
        for arch in archs:
            self.load_header(fh, arch.offset, arch.size)

    def load_header(self, fh, offset, size):
        fh.seek(offset)
        header = struct.unpack('>I', fh.read(4))[0]
        fh.seek(offset)
        if header == MH_MAGIC:
            magic, hdr, endian = MH_MAGIC, mach_header, '>'
        elif header == MH_CIGAM:
            magic, hdr, endian = MH_CIGAM, mach_header, '<'
        elif header == MH_MAGIC_64:
            magic, hdr, endian = MH_MAGIC_64, mach_header_64, '>'
        elif header == MH_CIGAM_64:
            magic, hdr, endian = MH_CIGAM_64, mach_header_64, '<'
        else:
            raise ValueError("Unknown Mach-O header: 0x%08x in %r" % (
                header, fh))
        hdr = MachOHeader(self, fh, offset, size, magic, hdr, endian)
        self.headers.append(hdr)


class MachOHeader(object):
    """
    Provides reading/writing the Mach-O header of a specific existing file
    """
    #   filename   - the original filename of this mach-o
    #   sizediff   - the current deviation from the initial mach-o size
    #   header     - the mach-o header
    #   commands   - a list of (load_command, somecommand, data)
    #                data is either a str, or a list of segment structures
    #   total_size - the current mach-o header size (including header)
    #   low_offset - essentially, the maximum mach-o header size
    #   id_cmd     - the index of my id command, or None

    def __init__(self, parent, fh, offset, size, magic, hdr, endian):
        self.MH_MAGIC = magic
        self.mach_header = hdr

        # These are all initialized by self.load()
        self.parent = parent
        self.offset = offset
        self.size = size

        self.endian = endian
        self.header = None
        self.commands = None
        self.id_cmd = None
        self.sizediff = None
        self.total_size = None
        self.low_offset = None
        self.filetype = None
        self.headers = []

        self.load(fh)

    def __repr__(self):
        return "<%s filename=%r offset=%d size=%d endian=%r>" % (
            type(self).__name__, self.parent.filename, self.offset, self.size,
            self.endian)

    def load(self, fh):
        fh = FileView(fh, self.offset, self.size)
        fh.seek(0)

        self.sizediff = 0
        kw = {'_endian_': self.endian}
        header = self.mach_header.from_fileobj(fh, **kw)
        self.header = header

        cmd = self.commands = []

        self.filetype = self.get_filetype_shortname(header.filetype)

        read_bytes = 0
        low_offset = sys.maxsize
        for i in range(header.ncmds):
            # read the load command
            cmd_load = load_command.from_fileobj(fh, **kw)

            # read the specific command
            klass = LC_REGISTRY.get(cmd_load.cmd, None)
            if klass is None:
                raise ValueError("Unknown load command: %d" % (cmd_load.cmd,))
            cmd_cmd = klass.from_fileobj(fh, **kw)

            if cmd_load.cmd == LC_ID_DYLIB:
                # remember where this command was
                if self.id_cmd is not None:
                    raise ValueError("This dylib already has an id")
                self.id_cmd = i

            if cmd_load.cmd in (LC_SEGMENT, LC_SEGMENT_64):
                # for segment commands, read the list of segments
                segs = []
                # assert that the size makes sense
                if cmd_load.cmd == LC_SEGMENT:
                    section_cls = section
                else: # LC_SEGMENT_64
                    section_cls = section_64

                expected_size = (
                    sizeof(klass) + sizeof(load_command) +
                    (sizeof(section_cls) * cmd_cmd.nsects)
                )
                if cmd_load.cmdsize != expected_size:
                    raise ValueError("Segment size mismatch")
                # this is a zero block or something
                # so the beginning is wherever the fileoff of this command is
                if cmd_cmd.nsects == 0:
                    if cmd_cmd.filesize != 0:
                        low_offset = min(low_offset, cmd_cmd.fileoff)
                else:
                    # this one has multiple segments
                    for j in range(cmd_cmd.nsects):
                        # read the segment
                        seg = section_cls.from_fileobj(fh, **kw)
                        # if the segment has a size and is not zero filled
                        # then its beginning is the offset of this segment
                        not_zerofill = ((seg.flags & S_ZEROFILL) != S_ZEROFILL)
                        if seg.offset > 0 and seg.size > 0 and not_zerofill:
                            low_offset = min(low_offset, seg.offset)
                        if not_zerofill:
                            c = fh.tell()
                            fh.seek(seg.offset)
                            sd = fh.read(seg.size)
                            seg.add_section_data(sd)
                            fh.seek(c)
                        segs.append(seg)
                # data is a list of segments
                cmd_data = segs

            else:
                # data is a raw str
                data_size = (
                    cmd_load.cmdsize - sizeof(klass) - sizeof(load_command)
                )
                cmd_data = fh.read(data_size)
            cmd.append((cmd_load, cmd_cmd, cmd_data))
            read_bytes += cmd_load.cmdsize

        # make sure the header made sense
        if read_bytes != header.sizeofcmds:
            raise ValueError("Read %d bytes, header reports %d bytes" % (
                read_bytes, header.sizeofcmds))
        self.total_size = sizeof(self.mach_header) + read_bytes
        self.low_offset = low_offset

        # this header overwrites a segment, what the heck?
        if self.total_size > low_offset:
            raise ValueError("total_size > low_offset (%d > %d)" % (
                self.total_size, low_offset))

    def get_filetype_shortname(self, filetype):
        if filetype in MH_FILETYPE_SHORTNAMES:
            return MH_FILETYPE_SHORTNAMES[filetype]
        else:
            return 'unknown'
