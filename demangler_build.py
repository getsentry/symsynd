import subprocess
from cffi import FFI

ffi = FFI()
ffi.cdef(subprocess.Popen([
    'cc', '-E', '-DDM_NOINCLUDE',
    'demangle-swift/demangle-swift.h'],
    stdout=subprocess.PIPE).communicate()[0])

with open('demangle-swift/demangle-all.cpp') as source:
    ffi.set_source(
        '_symsynd_swift_demangler',
        source.read(),
        include_dirs=['demangle-swift'],
        extra_compile_args=['-std=c++1y'],
        source_extension='.cpp'
    )
