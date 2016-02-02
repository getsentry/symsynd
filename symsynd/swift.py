from _symsynd_swift_demangler import ffi, lib


def demangle_symbol(symbol):
    buffer = ffi.new('char[4000]')
    rv = lib.demangle_swift(symbol, buffer, 4000)
    if rv:
        return ffi.string(buffer)
