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


def find_instruction(addr, cpu_name):
    if cpu_name.startswith('arm64'):
        return (addr & -4) - 1
    elif cpu_name.startswith('arm'):
        return (addr & -2) - 1
    else:
        return addr - 1


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

    def __init__(self, symbolizer_path=None):
        # symbolizer_path is no longer used.
        self._lock = RLock()
        self._proc = None
        self._closed = False
        self.symbolizer = Symbolizer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def close(self):
        if not self._closed:
            self.symbolizer.close()
        self._closed = True

    def symbolize(self, dsym_path, image_vmaddr, image_addr,
                  instruction_addr, cpu_name, silent=True,
                  demangle=True, symbolize_inlined=False,
                  frame_number=None):
        """Symbolizes a single frame based on the information provided.  If
        the symbolication fails `None` is returned in default more or a
        an exception is raised if `silent` is disabled.

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

        try:
            if not is_valid_cpu_name(cpu_name):
                raise SymbolicationError('"%s" is not a valid cpu name' % cpu_name)

            instruction_addr = find_instruction(instruction_addr, cpu_name)
            addr = image_vmaddr + instruction_addr - image_addr

            with self._lock:
                with timedsection('symbolize'):
                    if symbolize_inlined:
                        syms = self.symbolizer.symbolize_inlined(
                            dsym_path, addr, cpu_name)
                        return [convert_symbol(sym, demangle) for sym in syms]
                    else:
                        sym = self.symbolizer.symbolize(
                            dsym_path, addr, cpu_name)
                        return convert_symbol(sym, demangle)
        except SymbolicationError:
            if not silent:
                raise
            if symbolize_inlined:
                return []
            return None
