import sys
import errno
import struct

from . import mtypes

MAGIC = [
    struct.pack('!L', getattr(mtypes, 'MH_' + _))
    for _ in ['MAGIC', 'CIGAM', 'MAGIC_64', 'CIGAM_64']
]
FAT_MAGIC_BYTES = struct.pack('!L', mtypes.FAT_MAGIC)
MAGIC_LEN = 4


def is_macho_file(filename):
    try:
        with open(filename, 'rb') as f:
            header = f.read(MAGIC_LEN)
            return header in MAGIC or header == FAT_MAGIC_BYTES
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
        return False


class FileView(object):
    """
    A proxy for file-like objects that exposes a given view of a file
    """

    def __init__(self, fileobj, start, size):
        self._fileobj = fileobj
        self._start = start
        self._end = start + size

    def __repr__(self):
        return '<FileView [%d, %d] %r>' % (
            self._start, self._end, self._fileobj)

    def tell(self):
        return self._fileobj.tell() - self._start

    def _checkwindow(self, seekto, op):
        if not (self._start <= seekto <= self._end):
            raise IOError("%s to offset %d is outside window [%d, %d]" % (
                op, seekto, self._start, self._end))

    def seek(self, offset, whence=0):
        seekto = offset
        if whence == 0:
            seekto += self._start
        elif whence == 1:
            seekto += self._fileobj.tell()
        elif whence == 2:
            seekto += self._end
        else:
            raise IOError("Invalid whence argument to seek: %r" % (whence,))
        self._checkwindow(seekto, 'seek')
        self._fileobj.seek(seekto)

    def write(self, bytes):
        here = self._fileobj.tell()
        self._checkwindow(here, 'write')
        self._checkwindow(here + len(bytes), 'write')
        self._fileobj.write(bytes)

    def read(self, size=sys.maxsize):
        if size < 0:
            raise ValueError("Invalid size %s while reading from %s",
                             size, self._fileobj)
        here = self._fileobj.tell()
        self._checkwindow(here, 'read')
        bytes = min(size, self._end - here)
        return self._fileobj.read(bytes)
