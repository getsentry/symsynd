import ctypes
from threading import Lock

from symsynd.exceptions import SymbolicationError


lib = ctypes.CDLL('/Users/mitsuhiko/Development/symsynd/llvm/'
                  'build/lib/libLLVMSymbolizer.dylib')

symfunc = ctypes.CFUNCTYPE(
    None,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_int,
)

errfunc = ctypes.CFUNCTYPE(
    None,
    ctypes.c_char_p,
)

llvm_symbolizer_new = lib.llvm_symbolizer_new
llvm_symbolizer_new.restype = ctypes.c_void_p

llvm_symbolizer_free = lib.llvm_symbolizer_free
llvm_symbolizer_free.argtypes = (ctypes.c_void_p,)

llvm_symbolizer_symbolize = lib.llvm_symbolizer_symbolize
llvm_symbolizer_symbolize.argtypes = (
    ctypes.c_void_p,
    symfunc,
    errfunc,
    ctypes.c_char_p,
    ctypes.c_uint64,
    ctypes.c_int,
)
llvm_symbolizer_symbolize.restype = ctypes.c_int


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


def invalid_to_none(value):
    if value != '<invalid>':
        return value


class Symbolizer(object):

    def __init__(self):
        _init_lib()
        self._ptr = llvm_symbolizer_new()

    def close(self):
        if self._ptr is not None:
            llvm_symbolizer_free(self._ptr)
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

        rv = []
        errors = []

        def success(name, filename, lineno, column):
            rv.append((invalid_to_none(name),
                       invalid_to_none(filename), lineno, column))

        def failure(message):
            errors.append(message)

        llvm_symbolizer_symbolize(
            self._ptr, symfunc(success),
            errfunc(failure), module, offset, is_data and 1 or 0)

        if rv:
            return rv[0]
        if errors:
            raise SymbolicationError(errors[0])
