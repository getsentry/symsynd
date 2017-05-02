import os
from symsynd.exceptions import DwarfError
from symsynd._dwarf import ffi as _ffi
from symsynd._compat import to_bytes, text_type


_lib = _ffi.dlopen(os.path.join(os.path.dirname(__file__), '_libdwarf.so'))


special_errors = {}


def rustcall(func, *args):
    err = _ffi.new('dwarf_error_t *')
    rv = func(*(args + (err,)))
    if not err[0].failed:
        return rv
    try:
        cls = special_errors.get(err[0].code, DwarfError)
        exc = cls(_ffi.string(err[0].message).decode('utf-8', 'replace'))
    finally:
        _lib.dwarf_buffer_free(err[0].message)
    raise exc


class DebugInfo(object):

    def __init__(self):
        raise TypeError('Cannot instanciate debug infos')

    @staticmethod
    def _from_ptr(ptr):
        rv = object.__new__(DebugInfo)
        rv._ptr = ptr
        return rv

    @staticmethod
    def from_path(path):
        di = rustcall(_lib.dwarf_debug_info_open_path, to_bytes(path))
        return DebugInfo._from_ptr(di)

    def get_compilation_dir(self, cpu_name, path):
        rv = rustcall(_lib.dwarf_debug_info_get_compilation_dir,
                      self._ptr, to_bytes(cpu_name), to_bytes(path))
        rv = _ffi.string(rv)
        if isinstance(path, text_type):
            rv = rv.decode('utf-8')
        return rv

    def __del__(self):
        try:
            if self._ptr:
                _lib.dwarf_debug_info_free(self._ptr)
            self._ptr = None
        except Exception:
            pass
