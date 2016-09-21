#!/bin/bash

set -eu
cd -P -- "$(dirname -- "$0")"

mkdir -p dist
docker build -t symsynd:dev .
docker run --rm -v $PWD/llvm:/symsynd/llvm -v $PWD/dist:/symsynd/dist symsynd:dev "$@"
