import subprocess
from cffi import FFI

ffi = FFI()
ffi.cdef(subprocess.Popen([
    'cc', '-E', '-DPYTHON_HEADER',
    'libsymbolizer/llvm-symbolizer.h'],
    stdout=subprocess.PIPE).communicate()[0])

ffi.set_source(
    '_symsynd_symbolizer',
    '#include <llvm-symbolizer.h>',
    include_dirs=['libsymbolizer'],
    library_dirs=['libsymbolizer/build/sym',
                  'libsymbolizer/build/llvm/lib'],
    libraries=[
        'z',
        'ncurses',
        'LLVMBitReader',
        'LLVMMC',
        'LLVMCore',
        'LLVMMCParser',
        'LLVMDebugInfoCodeView',
        'LLVMObject',
        'LLVMDebugInfoDWARF',
        'LLVMSupport',
        'LLVMDebugInfoMSF',
        'LLVMSymbolize',
        'LLVMDebugInfoPDB',
        'LLVMSymbolizer',
    ],
    extra_compile_args=['-std=c++11'],
    source_extension='.cpp'
)
