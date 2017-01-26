import os
import errno
from threading import RLock

from symsynd.utils import parse_addr, timedsection
from symsynd.macho.arch import is_valid_cpu_name, get_macho_vmaddr
from symsynd.demangle import demangle_symbol
from symsynd.exceptions import SymbolicationError
from symsynd.libsymbolizer import Symbolizer


def qm_to_none(value):
    if value == '??':
        return None
    return value


def normalize_dsym_path(p):
    if '\x00' in p or '"' in p or '\n' in p or '\r' in p:
        raise ValueError('Invalid character in dsym path')
    p = os.path.abspath(p)
    if not os.path.isfile(p):
        raise IOError(errno.ENOENT, 'dsym file not found (%s)' % p)
    return p


def convert_symbol(sym, demangle=True):
    symbol_name = sym[0]
    if demangle:
        symbol_name = demangle_symbol(symbol_name)
    return {
        'symbol_name': symbol_name,
        'filename': sym[1],
        'line': sym[2],
        'column': sym[3],
    }


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
                  instruction_addr, cpu_name, demangle=True,
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

        The `demangle` parameter controls if demangling should be performed
        or not.  Currently C++ and (some version of) Swift demangling is
        supported.

        Additionally if `symbolize_inlined` is set to `True` then a list of
        frames is returned instead which might contain inlined frames.  In
        that case the return value might be an empty list instead.
        """
        if self._closed:
            raise RuntimeError('Symbolizer is closed')
        dsym_path = normalize_dsym_path(dsym_path)

        image_vmaddr = parse_addr(image_vmaddr)
        if not image_vmaddr:
            image_vmaddr = get_macho_vmaddr(dsym_path, cpu_name) or 0

        image_addr = parse_addr(image_addr)
        instruction_addr = parse_addr(instruction_addr)
        if not is_valid_cpu_name(cpu_name):
            raise SymbolicationError('"%s" is not a valid cpu name' % cpu_name)

        addr = image_vmaddr + instruction_addr - image_addr

        with self._lock:
            with timedsection('symbolize'):
                if symbolize_inlined:
                    syms = self._symbolizer.symbolize_inlined(
                        dsym_path, addr, cpu_name)
                    return [convert_symbol(sym, demangle) for sym in syms]
                else:
                    sym = self._symbolizer.symbolize(
                        dsym_path, addr, cpu_name)
                    return convert_symbol(sym, demangle)
