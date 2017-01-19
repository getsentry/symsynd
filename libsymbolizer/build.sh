#!/bin/sh

set -eu
cd -P -- "$(dirname -- "$0")"

SYMSYND_MANYLINUX=${SYMSYND_MANYLINUX:-0}
MACOS_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-0}

export MACOSX_DEPLOYMENT_TARGET=

# Make sure we compile against the 10.9 SDK.  See also build-wheels.sh
if [ `uname` == "Darwin" && "x$MACOSX_DEPLOYMENT_TARGET" != x ]; then
  XCODE_SDKS="/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs"
  if [ ! -d "${XCODE_SDKS}/MacOSX${MACOSX_DEPLOYMENT_TARGET}.sdk" ]; then
    echo "abort: cannot find the ${MACOSX_DEPLOYMENT_TARGET} SDK. You can get it from https://github.com/phracker/MacOSX-SDKs and place in ${XCODE_SDKS}"
    exit 1
  fi
fi

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
