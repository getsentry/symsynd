prepare:
	if hash git 2> /dev/null; then git submodule update --init; fi

build: prepare
	./libsymbolizer/build.sh

develop:
	pip install -v --editable .

test: develop
	pip install pytest
	py.test --tb=short tests -vv

full-test: build test

clean:
	rm symsynd/*.so
