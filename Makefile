test:
	pip install --editable .
	pip install pytest
	py.test --tb=short tests -vv
