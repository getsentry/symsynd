import sys
import subprocess
from cffi import FFI


def _to_source(x):
    if sys.version_info >= (3, 0) and isinstance(x, bytes):
        x = x.decode('utf-8')
    return x


sym_ffi = FFI()
sym_ffi.cdef(_to_source(subprocess.Popen([
    'cc', '-E', '-DPYTHON_HEADER',
    'libsymbolizer/llvm-symbolizer.h'],
    stdout=subprocess.PIPE).communicate()[0]))
sym_ffi.set_source('symsynd._symbolizer', None)

dwarf_ffi = FFI()
dwarf_ffi.cdef(_to_source(subprocess.Popen([
    'cc', '-E', '-DPYTHON_HEADER',
    'libdwarf/libdwarf.h'],
    stdout=subprocess.PIPE).communicate()[0]))
dwarf_ffi.set_source('symsynd._dwarf', None)

demangle_ffi = FFI()
demangle_ffi.cdef(_to_source(subprocess.Popen([
    'cc', '-E', '-DDM_NOINCLUDE',
    'demangle/demangle.h'],
    stdout=subprocess.PIPE).communicate()[0]))

with open('demangle/demangle-all.cpp') as source:
    demangle_ffi.set_source(
        'symsynd._demangler',
        _to_source(source.read()),
        include_dirs=['demangle'],
        extra_compile_args=['-std=c++11'],
        source_extension='.cpp'
    )
