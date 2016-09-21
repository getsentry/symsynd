import subprocess
from cffi import FFI

sym_ffi = FFI()
sym_ffi.cdef(subprocess.Popen([
    'cc', '-E', '-DPYTHON_HEADER',
    'libsymbolizer/llvm-symbolizer.h'],
    stdout=subprocess.PIPE).communicate()[0])
sym_ffi.set_source('symsynd._symbolizer', None)

demangle_ffi = FFI()
demangle_ffi.cdef(subprocess.Popen([
    'cc', '-E', '-DDM_NOINCLUDE',
    'demangle/demangle.h'],
    stdout=subprocess.PIPE).communicate()[0])

with open('demangle/demangle-all.cpp') as source:
    demangle_ffi.set_source(
        'symsynd._demangler',
        source.read(),
        include_dirs=['demangle'],
        extra_compile_args=['-std=c++11'],
        source_extension='.cpp'
    )
