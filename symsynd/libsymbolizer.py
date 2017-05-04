import os
import posixpath
from threading import Lock

from symsynd.exceptions import SymbolicationError
from symsynd.libdebug import DebugInfo
from symsynd._symbolizer import ffi
from symsynd._compat import to_bytes, itervalues


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
        self._debug_infos = {}

    def close(self):
        if self._ptr is not None:
            lib.llvm_symbolizer_free(self._ptr)
            self._ptr = None
        if self._debug_infos:
            for di in itervalues(self._debug_infos):
                di.close()
            self._debug_infos.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def get_debug_info(self, dsym_path):
        rv = self._debug_infos.get(dsym_path)
        if rv is None:
            rv = DebugInfo.open_path(dsym_path)
            self._debug_infos[dsym_path] = rv
        return rv

    def _make_frame(self, dsym_path, cpu_name, struct):
        symbol = _symstr(struct.name)
        if not symbol:
            return

        filename = None
        abs_path = _symstr(struct.filename)
        if abs_path:
            di = self.get_debug_info(dsym_path)
            comp_dir = di.get_compilation_dir(cpu_name, abs_path)
            if comp_dir and abs_path.startswith(comp_dir):
                filename = posixpath.relpath(abs_path, comp_dir)

        return {
            'symbol': symbol,
            'filename': filename,
            'abs_path': abs_path,
            'lineno': struct.lineno,
            'colno': struct.column,
        }

    def symbolize(self, dsym_path, offset, cpu_name, is_data=False):
        if self._ptr is None:
            raise RuntimeError('Symbolizer closed')

        rv = lib.llvm_symbolizer_symbolize(
            self._ptr, to_bytes(dsym_path + ':' + cpu_name),
            offset, is_data and 1 or 0)
        try:
            if rv.error:
                raise SymbolicationError(_symstr(rv.error))

            return self._make_frame(dsym_path, cpu_name, rv)
        finally:
            lib.llvm_symbol_free(rv)

    def symbolize_inlined(self, dsym_path, offset, cpu_name):
        if self._ptr is None:
            raise RuntimeError('Symbolizer closed')

        sym_out = ffi.new('llvm_symbol_t ***')
        sym_count_out = ffi.new('size_t *')

        err = lib.llvm_symbolizer_symbolize_inlined(
            self._ptr, to_bytes(dsym_path + ':' + cpu_name),
            offset, sym_out, sym_count_out)
        try:
            if err:
                assert err.error, 'Error witohut error indicated'
                raise SymbolicationError(_symstr(err.error))

            rv = []
            for count in xrange(sym_count_out[0]):
                frm = self._make_frame(dsym_path, cpu_name,
                                       sym_out[0][count])
                if frm:
                    rv.append(frm)
            lib.llvm_bulk_symbol_free(sym_out[0], sym_count_out[0])

            return rv
        finally:
            lib.llvm_symbol_free(err)
