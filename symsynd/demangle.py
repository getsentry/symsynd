from _symsynd_demangler import ffi, lib


def _make_buffer():
    return ffi.new('char[16000]')


def _demangle(func, sym, buffer=None):
    if buffer is None:
        buffer = _make_buffer()
    rv = func(sym, buffer, len(buffer))
    if rv:
        return ffi.string(buffer)


def demangle_swift_symbol(symbol):
    return _demangle(lib.demangle_swift, symbol)


def demangle_cpp_symbol(symbol):
    return _demangle(lib.demangle_cpp, symbol)


def demangle_symbol(symbol):
    buffer = _make_buffer()
    for func in lib.demangle_swift, lib.demangle_cpp:
        rv = _demangle(func, symbol, buffer)
        if rv is not None:
            return rv
