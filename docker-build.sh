#!/bin/bash

set -eu
cd -P -- "$(dirname -- "$0")"

mkdir -p dist
docker build -t symsynd:dev .
docker run --rm symsynd:dev | tar -xC dist
ls dist/*
