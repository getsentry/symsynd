#!/bin/sh

set -eu
cd -P -- "$(dirname -- "$0")"

mkdir -p build
cd build

cmake \
  -DCMAKE_BUILD_TYPE=MinSizeRel \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_OSX_ARCHITECTURES="i386;x86_64" \
  -DCMAKE_CXX_FLAGS=-std=c++11 \
  -DLLVM_ENABLE_RTTI=1 \
  -DLLVM_ENABLE_PIC=1 \
  -DLLVM_EXTERNAL_PROJECTS=Symbolizer \
  -DLLVM_EXTERNAL_SYMBOLIZER_SOURCE_DIR=../ ${SYMSYND_LLVM_DIR:-../../llvm}

cd tools/Symbolizer
make
