import os
from threading import Lock

from symsynd.exceptions import SymbolicationError
from symsynd._symbolizer import ffi


lib = ffi.dlopen(os.path.join(os.path.dirname(__file__), '_libsymbolizer.so'))


_lib_lock = Lock()
_initialized = False


def _init_lib():
    global _initialized
    if _initialized:
        return
    with _lib_lock:
        if _initialized:
            return
        lib.llvm_symbolizer_lib_init()
        _initialized = True


def _symstr(ptr):
    if ptr == ffi.NULL:
        return None
    val = ffi.string(ptr)
    if val == '<invalid>':
        return None
    return val.decode('utf-8', 'replace')


class Symbolizer(object):

    def __init__(self):
        _init_lib()
        self._ptr = lib.llvm_symbolizer_new()

    def close(self):
        if self._ptr is not None:
            lib.llvm_symbolizer_free(self._ptr)
            self._ptr = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def symbolize(self, module, offset, arch, is_data=False):
        if self._ptr is None:
            raise RuntimeError('Symbolizer closed')

        if arch is not None:
            module += ':' + arch

        rv = lib.llvm_symbolizer_symbolize(
            self._ptr, module, offset, is_data and 1 or 0)
        try:
            if rv.error:
                raise SymbolicationError(_symstr(rv.error))

            return (
                _symstr(rv.name),
                _symstr(rv.filename),
                rv.lineno,
                rv.column,
            )
        finally:
            lib.llvm_symbol_free(rv)
