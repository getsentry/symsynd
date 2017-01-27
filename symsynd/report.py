import os
import bisect

from symsynd.macho.arch import get_cpu_name, get_macho_uuids
from symsynd.utils import timedsection, parse_addr
from symsynd.exceptions import SymbolicationError
from symsynd._compat import string_types


SIGILL = 4
SIGBUS = 10
SIGSEGV = 11


def combine_frame(reference, override):
    """Combines a reference frame with override data.  In case the override
    data does not have a symbol in it, then `None` is returned.
    """
    if override['symbol_name'] is None:
        return None
    rv = dict(reference)
    for key in 'symbol_name', 'filename', 'line', 'column':
        val = override.get(key)
        if val is not None or key not in rv:
            rv[key] = val
    return rv


def combine_frames(reference, overrides):
    rv = []
    for frame in overrides:
        new_frame = combine_frame(reference, frame)
        if new_frame is not None:
            rv.append(new_frame)
    return rv


def get_previous_instruction(addr, cpu_name):
    if cpu_name.startswith('arm64'):
        return (addr & -4) - 4
    elif cpu_name.startswith('arm'):
        return (addr & -2) - 2
    else:
        return addr - 1


def get_next_instruction(addr, cpu_name):
    if cpu_name.startswith('arm64'):
        return (addr & -4) + 4
    elif cpu_name.startswith('arm'):
        return (addr & -2) + 2
    else:
        return addr + 1


def truncate_instruction(addr, cpu_name):
    if cpu_name.startswith('arm64'):
        return addr & -4
    elif cpu_name.startswith('arm'):
        return addr & -2
    return addr


def get_image_cpu_name(image):
    cpu_name = image.get('cpu_name')
    if cpu_name is not None:
        return cpu_name
    return get_cpu_name(image['cpu_type'], image['cpu_subtype'])


def get_ip_register(registers, cpu_name):
    if not registers:
        rv = None
    elif cpu_name[:3] == 'arm':
        rv = registers.get('pc')
    elif cpu_name == 'x86_64':
        rv = registers.get('rip')
    if rv is not None:
        return parse_addr(rv)


def find_debug_images(dsym_paths, binary_images):
    images_to_load = set()

    with timedsection('iterimages0'):
        for image in binary_images:
            if get_image_cpu_name(image) is not None:
                images_to_load.add(image['uuid'].lower())

    images = {}

    # Step one: load images that are named by their UUID
    with timedsection('loadimages-fast'):
        for uuid in list(images_to_load):
            for dsym_path in dsym_paths:
                fn = os.path.join(dsym_path, uuid)
                if os.path.isfile(fn):
                    images[uuid] = fn
                    images_to_load.discard(uuid)
                    break

    # Otherwise fall back to loading images from the dsym bundle.  Because
    # this loading strategy is pretty slow we do't actually want to use it
    # unless we have a path that looks like a bundle.  As a result we
    # find all the paths which are bundles and then only process those.
    if images_to_load:
        slow_paths = []
        for dsym_path in dsym_paths:
            if os.path.isdir(os.path.join(dsym_path, 'Contents')):
                slow_paths.append(dsym_path)

        with timedsection('loadimages-slow'):
            for dsym_path in slow_paths:
                dwarf_base = os.path.join(dsym_path, 'Contents',
                                          'Resources', 'DWARF')
                if os.path.isdir(dwarf_base):
                    for fn in os.listdir(dwarf_base):
                        # Looks like a UUID we loaded, skip it
                        if fn in images:
                            continue
                        full_fn = os.path.join(dwarf_base, fn)
                        uuids = get_macho_uuids(full_fn)
                        for _, uuid in uuids:
                            if uuid in images_to_load:
                                images[uuid] = full_fn
                                images_to_load.discard(uuid)

    rv = {}

    # Now resolve all the images.
    with timedsection('resolveimages'):
        for image in binary_images:
            cpu_name = get_image_cpu_name(image)
            if cpu_name is None:
                continue
            uid = image['uuid'].lower()
            if uid not in images:
                continue
            rv[image['image_addr']] = {
                'uuid': uid,
                'image_addr': image['image_addr'],
                'dsym_path': images[uid],
                'image_vmaddr': image.get('image_vmaddr') or 0,
                'cpu_name': cpu_name,
            }

    return rv


class ReportSymbolizer(object):
    """A report symbolizer can symbolize apple style crash reports.  For
    information on some of the parameters also make sure to refer to the
    underlying `Driver` which needs to be passed in.

    `dsym_paths` is a list of paths where dsym files can be found on the
    file system.  `binary_images` is a list of binary images.  The
    images need to be given as dictionaries with the following keys:
    ``uuid``, ``image_addr``, ``dsym_path``, ``image_vmaddr`` (can be left
    out), ``cpu_type``, ``cpu_subtype`` (alternatively ``cpu_name`` is
    also accepted).
    """

    def __init__(self, driver, dsym_paths, binary_images):
        if isinstance(dsym_paths, string_types):
            dsym_paths = [dsym_paths]
        self.driver = driver
        with timedsection('findimages'):
            self.images = find_debug_images(dsym_paths, binary_images)

        # This mapping is the mapping that the report symbolizer actually
        # uses.  The `images` mapping is primarily for extenral consumers
        # that want to see what images exist in the symbolizer.
        self._image_addresses = []
        self._image_references = {}
        for img in self.images.itervalues():
            img_addr = parse_addr(img['image_addr'])
            self._image_addresses.append(img_addr)
            self._image_references[img_addr] = img
        self._image_addresses.sort()

        # This should always succeed but you never quite know.
        self.cpu_name = None
        for img in self.images.itervalues():
            cpu_name = img['cpu_name']
            if self.cpu_name is None:
                self.cpu_name = cpu_name
            elif self.cpu_name != cpu_name:
                self.cpu_name = None
                break

    def find_image(self, addr):
        """Given an instruction address this locates the image this address
        is contained in.
        """
        idx = bisect.bisect_left(self._image_addresses, parse_addr(addr))
        if idx > 0:
            return self._image_references[self._image_addresses[idx - 1]]

    def find_best_instruction(self, addr, cpu_name=None, meta=None):
        """Given an instruction and meta information this attempts to find
        the best instruction for the frame.  In some circumstances we can
        fix it up a bit to improve the accuracy.  For more information see
        `symbolize_frame`.
        """
        addr = parse_addr(addr)
        cpu_name = cpu_name or self.cpu_name

        # In case we're not on the crashing frame we apply a simple heuristic:
        # since we're most likely dealing with return addresses we just assume
        # that the call is one instruction behind the current one.
        if not meta or meta.get('frame_number') != 0:
            return get_previous_instruction(addr, cpu_name)

        # In case registers are available we can check if the PC register
        # does not match the given address we have from the first frame.
        # If that is the case and we got one of a few signals taht are likely
        # it seems that going with one instruction back is actually the
        # correct thing to do.
        regs = meta.get('registers')

        ip = get_ip_register(regs, cpu_name)
        if ip is not None and ip != addr and \
           meta.get('signal') in (SIGILL, SIGBUS, SIGSEGV):
            return get_previous_instruction(addr, cpu_name)

        return addr

    def symbolize_frame(self, frame, silent=True, demangle=True,
                        symbolize_inlined=False, meta=None):
        """Symbolizes a frame in the context of the report data.  For
        more information see the `Driver.symbolize` method.

        Unlike the lower level driver, this one can perform heuristics on the
        crash if `meta` is provided.

        `meta` is a dictionary of meta information that can help with
        the symbolication process.  If it's empty then all heuristics are
        disabled.  The following keys are currently supported:

        -   ``frame_number``: the number of the source frame.  If this is set
            to ``0`` then the crashing frame is assumed and various heuristics
            are enabled.
        -   ``signal``: the posix signal number if the execution was aborted
            with a posix signal.  In particular this can help fix some issues
            with assuming wrong addresses in limited circumstances.
        -   ``registers``: a dictionary of register values.  The key is the
            name of the register and the value is the register value as
            hexadecimal string or integer.  The only register that currently
            matters is ``pc`` on arm CPUs however this might change in the
            future.
        """
        img_addr = frame.get('object_addr') or frame.get('image_addr')
        cpu_name = frame.get('cpu_name') or (
            meta and meta.get('cpu_name')) or self.cpu_name

        try:
            if cpu_name is None:
                raise SymbolicationError('The CPU name was not provided')

            instruction_addr = self.find_best_instruction(
                frame['instruction_addr'], cpu_name, meta)

            img = self.find_image(instruction_addr)
            if img is not None:
                rv = self.driver.symbolize(
                    img['dsym_path'], img['image_vmaddr'],
                    img['image_addr'], instruction_addr,
                    cpu_name, demangle=demangle,
                    symbolize_inlined=symbolize_inlined)
                if not symbolize_inlined:
                    return combine_frame(frame, rv)
                return combine_frames(frame, rv)
        except SymbolicationError:
            if not silent:
                raise

        # Default return value for missing matches
        if symbolize_inlined:
            return []

    def symbolize_backtrace(self, backtrace, demangle=True, meta=None,
                            symbolize_inlined=True):
        """Symbolizes an entire stacktrace.  The crashing frame is expected
        to be the first item in the list.
        """
        rv = []
        meta = dict(meta or {}, frame_number=None)
        for idx, frame in enumerate(backtrace):
            meta['frame_number'] = idx
            symrv = self.symbolize_frame(frame, demangle=demangle,
                                         symbolize_inlined=symbolize_inlined,
                                         meta=meta)
            if symbolize_inlined:
                if symrv:
                    rv.extend(symrv)
                    continue
            else:
                if symrv is not None:
                    rv.append(symrv)
                    continue
            rv.append(frame)
        return rv
