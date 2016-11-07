from symsynd._demangler import ffi, lib
from symsynd._compat import text_type


def _make_buffer():
    return ffi.new('char[16000]')


def _demangle(func, sym, buffer=None):
    if buffer is None:
        buffer = _make_buffer()
    if isinstance(sym, text_type):
        sym = sym.encode('utf-8')
    rv = func(sym, buffer, len(buffer))
    if rv:
        return ffi.string(buffer).decode('utf-8', 'replace')


def demangle_swift_symbol(symbol, simplified=False):
    if simplified:
        return _demangle(lib.demangle_swift_simplified, symbol)
    else:
        return _demangle(lib.demangle_swift, symbol)


def demangle_cpp_symbol(symbol):
    return _demangle(lib.demangle_cpp, symbol)


def demangle_symbol(symbol):
    if symbol is None:
        return None
    buffer = _make_buffer()
    for func in lib.demangle_swift, lib.demangle_cpp:
        rv = _demangle(func, symbol, buffer)
        if rv is not None:
            return rv
    return symbol
