import os
import uuid
from symsynd import exceptions
from symsynd._debug import ffi as _ffi
from symsynd._compat import to_bytes, text_type


_lib = _ffi.dlopen(os.path.join(os.path.dirname(__file__), '_libdebug.so'))


special_errors = {
    2: exceptions.NoSuchArch,
    3: exceptions.NoSuchSection,
    4: exceptions.NoSuchAttribute,
}


def str_from_slice(ptr):
    return bytes(_ffi.buffer(ptr.s, ptr.len)).decode('utf-8')


def rustcall(func, *args):
    err = _ffi.new('debug_error_t *')
    rv = func(*(args + (err,)))
    if not err[0].failed:
        return rv
    try:
        cls = special_errors.get(err[0].code, exceptions.DwarfError)
        exc = cls(_ffi.string(err[0].message).decode('utf-8', 'replace'))
    finally:
        _lib.debug_buffer_free(err[0].message)
    raise exc


class Variant(object):

    def __init__(self, struct):
        self.cpu_name = str_from_slice(struct.cpu_name)
        self.uuid = uuid.UUID(bytes=struct.uuid)
        self.name = str_from_slice(struct.name)
        self.vmaddr = struct.vmaddr
        self.vmsize = struct.vmsize

    def __repr__(self):
        return '<Variant %r (%s)>' % (
            self.cpu_name,
            self.uuid,
        )


def get_cpu_name(type, subtype):
    try:
        return str_from_slice(rustcall(_lib.debug_get_cpu_name, type, subtype))
    except exceptions.NoSuchArch:
        pass


def get_cpu_type_tuple(name):
    try:
        struct = rustcall(_lib.debug_get_cpu_type, to_bytes(name))
        return (struct.cputype, struct.cpusubtype)
    except exceptions.NoSuchArch:
        pass


def is_valid_cpu_name(name):
    return get_cpu_type_tuple(name) is not None


class DebugInfo(object):

    def __init__(self):
        raise TypeError('Cannot instanciate debug infos')

    @staticmethod
    def _from_ptr(ptr):
        rv = object.__new__(DebugInfo)
        rv._ptr = ptr
        return rv

    @staticmethod
    def open_path(path):
        di = rustcall(_lib.debug_info_open_path, to_bytes(path))
        return DebugInfo._from_ptr(di)

    def _get_ptr(self):
        if self._ptr is None:
            raise RuntimeError('Debug info closed')
        return self._ptr

    def get_compilation_dir(self, cpu_name, path):
        ptr = self._get_ptr()

        try:
            rv = rustcall(_lib.debug_info_get_compilation_dir,
                          ptr, to_bytes(cpu_name), to_bytes(path))
            rv = _ffi.string(rv)
            if isinstance(path, text_type):
                rv = rv.decode('utf-8')
            return rv
        except exceptions.DwarfLookupError:
            pass

    def get_variants(self):
        ptr = self._get_ptr()
        count = _ffi.new('int *')
        arr = rustcall(_lib.debug_info_get_variants, ptr, count)
        return [Variant(arr[x]) for x in range(count[0])]

    def get_variant(self, uuid_or_cpu_name):
        if isinstance(uuid_or_cpu_name, uuid.UUID):
            id = uuid_or_cpu_name
            cpu_name = None
        else:
            try:
                id = uuid.UUID(uuid_or_cpu_name)
                cpu_name = None
            except ValueError:
                id = None
                cpu_name = uuid_or_cpu_name
        for variant in self.get_variants():
            if (id is not None and variant.uuid == id) or \
               (cpu_name is not None and variant.cpu_name == cpu_name):
                return variant

    def close(self):
        if self._ptr:
            _lib.debug_info_free(self._ptr)
        self._ptr = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
