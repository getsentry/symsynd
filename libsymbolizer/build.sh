#!/bin/sh

set -eu

CACHE_FLAGS="-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_OSX_ARCHITECTURES='i386;x86_64'"

# Prepare llvm build
mkdir -p build/llvm
cd build/llvm
cmake $CACHE_FLAGS ../../../llvm

# Build the llvm symbolizer command line utility.  This will also
# build all of our dependencies
cd tools/llvm-symbolizer
make

# Make our build
cd ../../..
mkdir -p sym
cd sym
LLVM_DIR=`pwd`/../llvm cmake -D CMAKE_CXX_FLAGS=-std=c++11 $CACHE_FLAGS ../..
make
