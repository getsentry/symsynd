#!/bin/sh

set -eu

# Prepare llvm build
mkdir -p build/llvm
cd build/llvm
cmake ../../../llvm

# Build the llvm symbolizer command line utility.  This will also
# build all of our dependencies
cd tools/llvm-symbolizer
make

# Make our build
cd ../../..
mkdir -p sym
cd sym
LLVM_DIR=`pwd`/../llvm cmake -D CMAKE_CXX_FLAGS=-std=c++11 ../..
make

# Copy result out
cd ../..
cp build/sym/libLLVMSymbolizer.dylib ../symsynd
