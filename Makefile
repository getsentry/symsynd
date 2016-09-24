llvm/CMakeLists.txt:
	mkdir llvm
	wget -O- https://github.com/llvm-mirror/llvm/archive/922af1cb4.tar.gz | tar -xz --strip-components=1 -C llvm

build: llvm/CMakeLists.txt
	./libsymbolizer/build.sh

build-wheel: build
	pip install wheel
	python setup.py bdist_wheel
	if [ x$$SYMSYND_MANYLINUX == x1 ]; then auditwheel show dist/*.whl; fi

develop:
	pip install -v --editable .

test: develop
	pip install pytest
	py.test --tb=short tests -vv

clean:
	rm symsynd/*.so

clean-docker:
	docker rmi -f symsynd:dev

build-docker-wheel:
	SYMSYND_MANYLINUX=1 ./docker-build.sh

.PHONY: build build-wheel develop test clean clean-docker build-docker-wheel
