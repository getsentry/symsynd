cmake_minimum_required(VERSION 3.4.3)
project(LLVM)

find_package(LLVM REQUIRED CONFIG)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")
message(STATUS "Using LLVM cmake dir: ${LLVM_CMAKE_DIR}")

list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")
include_directories(${LLVM_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})
include(AddLLVM)

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
