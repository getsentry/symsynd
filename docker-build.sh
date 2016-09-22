#!/bin/bash

set -eu
cd -P -- "$(dirname -- "$0")"

# Maybe we can do better here
CIDFILE=$(mktemp -u)

mkdir -p dist
docker build -t symsynd:dev .
docker run --cidfile="$CIDFILE" symsynd:dev build-wheel

CID=$(cat "$CIDFILE")
rm -f "$CIDFILE"

docker cp "$CID:/usr/src/symsynd/dist/." dist
docker rm "$CID"

ls -alh dist
