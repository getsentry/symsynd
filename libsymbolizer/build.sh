#!/bin/sh

set -eu
cd -P -- "$(dirname -- "$0")"

SYMSYND_MANYLINUX=${SYMSYND_MANYLINUX:-0}

mkdir -p build
cd build

if [ x$SYMSYND_MANYLINUX == x1 ]; then
  export PYTHON_LIBRARY=/opt/python/cp27-cp27mu/lib
  export PYTHON_INCLUDE_DIR=/opt/python/cp27-cp27mu/include/python2.7
  export PYTHON_EXECUTABLE=/opt/python/cp27-cp27mu/bin/python2.7
  CC=/opt/rh/devtoolset-2/root/usr/bin/gcc
  CXX=/opt/rh/devtoolset-2/root/usr/bin/g++
else
  CC=clang
  CXX=clang++
fi

cmake \
  -DCMAKE_BUILD_TYPE=MinSizeRel \
  -DCMAKE_C_COMPILER=$CC \
  -DCMAKE_CXX_COMPILER=$CXX \
  -DCMAKE_OSX_ARCHITECTURES="i386;x86_64" \
  -DCMAKE_CXX_FLAGS="-std=c++11" \
  -DLLVM_ENABLE_RTTI=1 \
  -DLLVM_ENABLE_PIC=1 \
  -DLLVM_EXTERNAL_PROJECTS=Symbolizer \
  -DLLVM_EXTERNAL_SYMBOLIZER_SOURCE_DIR=../ ${SYMSYND_LLVM_DIR:-../../llvm}

cd tools/Symbolizer
make
