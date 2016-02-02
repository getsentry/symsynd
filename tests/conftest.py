import os
import pytest


@pytest.fixture(scope='module')
def here():
    return os.path.abspath(os.path.dirname(__file__))


@pytest.fixture(scope='module')
def res_path(here):
    return os.path.join(here, 'res')


@pytest.fixture(scope='module')
def ct_dsym_base_path(res_path):
    return os.path.join(res_path, 'Crash-Tester.app.dSYM')


@pytest.fixture(scope='module')
def ct_dsym_path(ct_dsym_base_path):
    return os.path.join(ct_dsym_base_path, 'Contents',
                        'Resources', 'DWARF', 'Crash-Tester')


@pytest.fixture(scope='function')
def driver(request):
    from symsynd.driver import Driver
    rv = Driver()
    request.addfinalizer(rv.close)
    return rv
