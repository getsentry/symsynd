llvm/CMakeLists.txt:
	git submodule update --init

symsynd/_libsymbolizer.so: llvm/CMakeLists.txt
	./libsymbolizer/build.sh

build: symsynd/_libsymbolizer.so

develop:
	pip install -v --editable .

test: develop
	pip install pytest
	py.test --tb=short tests -vv

clean:
	rm symsynd/*.so

.PHONY: build develope test clean
