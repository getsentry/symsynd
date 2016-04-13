import subprocess
from cffi import FFI

ffi = FFI()
ffi.cdef(subprocess.Popen([
    'cc', '-E', '-DDM_NOINCLUDE',
    'demangle/demangle.h'],
    stdout=subprocess.PIPE).communicate()[0])

with open('demangle/demangle-all.cpp') as source:
    ffi.set_source(
        '_symsynd_demangler',
        source.read(),
        include_dirs=['demangle'],
        extra_compile_args=['-std=c++1y'],
        source_extension='.cpp'
    )
