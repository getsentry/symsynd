import os
import errno
from threading import RLock

from symsynd.libdebug import is_valid_cpu_name
from symsynd.utils import parse_addr, timedsection
from symsynd.exceptions import SymbolicationError
from symsynd.libsymbolizer import Symbolizer


def normalize_dsym_path(p):
    if '\x00' in p or '"' in p or '\n' in p or '\r' in p:
        raise ValueError('Invalid character in dsym path')
    p = os.path.abspath(p)
    if not os.path.isfile(p):
        raise IOError(errno.ENOENT, 'dsym file not found (%s)' % p)
    return p


class Driver(object):
    """The main symbolication driver.  This abstracts around a low level
    LLVM based symbolizer that works with DWARF files.  It's recommended to
    explicitly close the driver to ensure memory cleans up timely.
    """

    def __init__(self):
        self._lock = RLock()
        self._proc = None
        self._closed = False
        self._symbolizer = Symbolizer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def close(self):
        if not self._closed:
            self._symbolizer.close()
        self._closed = True

    def symbolize(self, dsym_path, image_vmaddr, image_addr,
                  instruction_addr, cpu_name,
                  symbolize_inlined=False):
        """Symbolizes a single frame based on the information provided.  If
        the symbolication fails a `SymbolicationError` is raised.

        `dsym_path` is the path to the dsym file on the file system.
        `image_vmaddr` is the slide of the image.  For most situations this
        can just be set to `0`.  If it's zero or unset we will attempt to
        find the slide from the dsym file.  `image_addr` is the canonical
        image address as loaded.  `instruction_addr` is the address where the
        error happened.

        `cpu_name` is the CPU name.  It follows general apple conventions and
        is used to special case certain behavior and look up the right
        symbols.  Common names are `armv7` and `arm64`.

        Additionally if `symbolize_inlined` is set to `True` then a list of
        frames is returned instead which might contain inlined frames.  In
        that case the return value might be an empty list instead.
        """
        if self._closed:
            raise RuntimeError('Symbolizer is closed')
        dsym_path = normalize_dsym_path(dsym_path)

        image_vmaddr = parse_addr(image_vmaddr)

        image_addr = parse_addr(image_addr)
        instruction_addr = parse_addr(instruction_addr)
        if not is_valid_cpu_name(cpu_name):
            raise SymbolicationError('"%s" is not a valid cpu name' % cpu_name)

        addr = image_vmaddr + instruction_addr - image_addr

        with self._lock:
            with timedsection('symbolize'):
                if symbolize_inlined:
                    return self._symbolizer.symbolize_inlined(
                        dsym_path, addr, cpu_name)
                return self._symbolizer.symbolize(
                    dsym_path, addr, cpu_name)
