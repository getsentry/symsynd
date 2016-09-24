set(LLVM_LINK_COMPONENTS
  DebugInfoDWARF
  DebugInfoPDB
  Object
  Support
  Symbolize
)

add_llvm_library(LLVMSymbolizer
  SHARED;
  llvm-symbolizer.cpp
)
#set_target_properties(LLVMSymbolizer PROPERTIES COMPILE_FLAGS "-fPIC")

if ("$ENV{SYMSYND_MANYLINUX}" STREQUAL "1")
  set_target_properties(LLVMSymbolizer PROPERTIES LINK_FLAGS
	  "-static-libstdc++ -static-libgcc")
endif()
