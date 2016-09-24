#!/bin/bash

set -eu
cd -P -- "$(dirname -- "$0")"

SYMSYND_MANYLINUX=${SYMSYND_MANYLINUX:-0}

if [ x$SYMSYND_MANYLINUX == x1 ]; then
  for pypath in /opt/python/cp27-*; do
    # cffi stores some crap here which is not stable between ucs versions
    # so we need to make sure it goes away
    rm -rf .eggs build
    $pypath/bin/pip install wheel
    $pypath/bin/python setup.py bdist_wheel
  done
else
  pip install wheel
  python setup.py bdist_wheel
fi

if [ x$SYMSYND_MANYLINUX == x1 ]; then
  echo "Auditing wheels"
  for wheel in dist/*-linux_*.whl; do
    auditwheel repair $wheel -w dist/
    rm $wheel
  done
fi
