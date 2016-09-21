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
