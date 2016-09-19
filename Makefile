prepare:
	git submodule update --init

build: prepare
	./libsymbolizer/build.sh

develop:
	pip install -v --editable .

test: develop
	pip install pytest
	py.test --tb=short tests -vv

full-test: build test
