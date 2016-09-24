#!/bin/bash

set -eu
cd -P -- "$(dirname -- "$0")"

SYMSYND_MANYLINUX=${SYMSYND_MANYLINUX:-0}

if [ x$SYMSYND_MANYLINUX == x1 ]; then
  DOCKERFILE=Dockerfile.manylinux
else
  DOCKERFILE=Dockerfile
fi

# Maybe we can do better here.  This has a high enough chance of being
# an unsafe race condition but this one is portable :P
CIDFILE=$(mktemp -u)

# Clean up after outselves on the way out.
cleanup() {
  if [ -f "$CIDFILE" ]; then
    CID=$(cat "$CIDFILE")
    docker rm "$CID" 2> /dev/null
  fi
  rm -f "$CIDFILE"
}

# trigger a build
build() {
  cleanup
  docker build -t symsynd:$1 -f $2 .
  docker run --cidfile="$CIDFILE" symsynd:$1 wheel
  CID=$(cat "$CIDFILE")
  docker cp "$CID:/usr/src/symsynd/dist/." dist
}

# Make sure we clean up before we exit in any case
trap cleanup EXIT

mkdir -p dist

if [ x$SYMSYND_MANYLINUX == x1 ]; then
  build dev32 Dockerfile.manylinux.32
  build dev64 Dockerfile.manylinux.64
else
  build dev Dockerfile
fi

ls -alh dist
