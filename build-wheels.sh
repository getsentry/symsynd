#!/bin/bash

set -eu
cd -P -- "$(dirname -- "$0")"

SYMSYND_MANYLINUX=${SYMSYND_MANYLINUX:-0}
WHEEL_OPTIONS=

# If we are building on OS X we make sure that our platform version is compiled
# OSX SDK 10.9 and then we ensure that we are building all our stuff with that
# version of the SDK as well.  We accept any python version that is compiled
# against that sdk or older.
#
# Since we build the libsymbolizer separately it's important the same deployment
# target is also used in the libsymbolizer/build.sh so we do it there as well.
if [ `uname` == "Darwin" ]; then
  python -c "if 1:
    import sys
    from distutils.util import get_platform
    ver = tuple(int(x) for x in get_platform().split('-')[1].split('.'))
    if ver > (10, 9):
        print 'abort: python is compiled against an OS X that is too new'
	sys.exit(1)
  "
  export MACOSX_DEPLOYMENT_TARGET=10.9
  WHEEL_OPTIONS="--plat-name=macosx-10.9-intel"
fi

# In case we build for manylinux we run for all 2.7 versions.  This assumes
# this script is run in our docker container where those python versions exist.
if [ x$SYMSYND_MANYLINUX == x1 ]; then
  for pypath in /opt/python/cp27-*; do
    # cffi stores some crap here which is not stable between ucs versions
    # so we need to make sure it goes away
    rm -rf .eggs build
    $pypath/bin/pip install wheel
    $pypath/bin/python setup.py bdist_wheel $WHEEL_OPTIONS
  done

# Otherwise just invoke normally.
else
  pip install wheel
  python setup.py bdist_wheel $WHEEL_OPTIONS
fi

# For manylinux wheels we make sure we run auditwheel repair to ensure the
# wheels are correct and to trigger a rename to the manylinux1 tag.
if [ x$SYMSYND_MANYLINUX == x1 ]; then
  echo "Auditing wheels"
  for wheel in dist/*-linux_*.whl; do
    auditwheel repair $wheel -w dist/
    rm $wheel
  done
fi
