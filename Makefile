MANYLINUX=0
LLVM_VERSION=922af1cb46bb89a7bdbf68dfe77b15d1347441d7

llvm/CMakeLists.txt:
	mkdir llvm
	wget -O- https://github.com/llvm-mirror/llvm/archive/$(LLVM_VERSION).tar.gz | tar -xz --strip-components=1 -C llvm

build: llvm/CMakeLists.txt
	./libsymbolizer/build.sh
	cd libdebug; cargo build --release

sdist: llvm/CMakeLists.txt
	python setup.py sdist --formats=zip

wheel:
	SYMSYND_MANYLINUX="$(MANYLINUX)" ./build-wheels.sh

develop:
	pip install -v --editable .

fast-test:
	py.test --tb=short tests -vv

test: develop
	pip install pytest==3.0.6
	$(MAKE) fast-test

clean:
	rm symsynd/*.so

clean-docker:
	docker rmi -f symsynd:dev
	docker rmi -f symsynd:dev32
	docker rmi -f symsynd:dev64

manylinux-wheels:
	SYMSYND_MANYLINUX=1 ./docker-build.sh

mac-wheels:
	SYMSYND_MACWHEELS=1 ./build-wheels.sh

all-wheels: mac-wheels manylinux-wheels

release: sdist all-wheels
	pip install twine
	twine upload dist/symsynd-`python setup.py --version`[-.]*

.PHONY: build sdist wheel develop fast-test test clean clean-docker \
	build-docker-wheel all-wheels release
