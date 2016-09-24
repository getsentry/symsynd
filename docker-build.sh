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
trap cleanup EXIT

mkdir -p dist
docker build -t symsynd:dev -f $DOCKERFILE .
docker run --cidfile="$CIDFILE" symsynd:dev wheel

CID=$(cat "$CIDFILE")

docker cp "$CID:/usr/src/symsynd/dist/." dist

ls -alh dist
