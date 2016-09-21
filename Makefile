llvm/CMakeLists.txt:
	git submodule update --init

build: llvm/CMakeLists.txt
	./libsymbolizer/build.sh

build-wheel: build
	pip install wheel
	python setup.py bdist_wheel

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
	./docker-build.sh build-wheel

.PHONY: build build-wheel develop test clean clean-docker build-docker-wheel
