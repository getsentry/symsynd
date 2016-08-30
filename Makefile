prepare:
	git submodule update --init

build: prepare
	./libsymbolizer/build.sh

develop: build
	pip install --editable .

test: develop
	pip install pytest
	py.test --tb=short tests -vv

full-test: build test
