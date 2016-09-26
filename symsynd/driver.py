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
                  instruction_addr, cpu_name, uuid=None, silent=True):
        if self._closed:
            raise RuntimeError('Symbolizer is closed')
        if not is_valid_cpu_name(cpu_name):
            raise ValueError('"%s" is not a valid cpu name' % cpu_name)
        dsym_path = normalize_dsym_path(dsym_path)

        image_vmaddr = parse_addr(image_vmaddr)
        if not image_vmaddr:
            image_vmaddr = get_macho_vmaddr(dsym_path, cpu_name) or 0

        image_addr = parse_addr(image_addr)
        instruction_addr = parse_addr(instruction_addr)

        addr = image_vmaddr + instruction_addr - image_addr

        try:
            with self._lock:
                with timedsection('symbolize'):
                    sym = self.symbolizer.symbolize(dsym_path, addr, cpu_name)
            if sym[0] is None:
                raise SymbolicationError('Symbolizer could not find symbol')
        except SymbolicationError:
            if not silent:
                raise
            sym = (None, None, 0, 0)

        return {
            'symbol_name': demangle_symbol(sym[0]),
            'filename': sym[1],
            'line': sym[2],
            'column': sym[3],
            'uuid': uuid,
        }
