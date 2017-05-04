import os
import sys
import time
import json
import pytest

from symsynd.images import find_debug_images, ImageLookup
from symsynd.libdebug import get_cpu_name
from symsynd.heuristics import find_best_instruction
from symsynd.utils import parse_addr


diff_report = None


class ReportSymbolizer(object):

    def __init__(self, driver, dsym_paths, binary_images):
        self.driver = driver
        self.images = ImageLookup(binary_images)
        self.image_paths = find_debug_images(dsym_paths, binary_images)

    def symbolize_backtrace(self, backtrace, meta=None):
        def symbolize(frame):
            instr = frame['instruction_addr']
            img = self.images.find_image(instr)
            if img is None:
                return [frame]
            dsym_path = self.image_paths.get(parse_addr(img['image_addr']))
            if dsym_path is None:
                return [frame]

            cpu_name = get_cpu_name(img['cpu_type'], img['cpu_subtype'])
            if meta is not None:
                instr = find_best_instruction(instr, cpu_name, meta)

            rv = self.driver.symbolize(dsym_path, img['image_vmaddr'],
                                       img['image_addr'],
                                       instr, cpu_name,
                                       symbolize_inlined=True)
            if not rv:
                return [frame]

            result = []
            for rv in rv:
                frame = dict(frame)
                frame['symbol_name'] = rv['symbol']
                frame['filename'] = rv['abs_path']
                frame['line'] = rv['lineno']
                frame['column'] = rv['colno']
                result.append(frame)
            return result

        rv = []
        for idx, f in enumerate(backtrace):
            if meta is not None:
                meta['frame_number'] = idx
            rv.extend(symbolize(f))
        return rv


class DiffReport(object):

    def __init__(self, config):
        from _pytest.config import create_terminal_writer
        self.filename = '.last-run'
        self.results = {}
        self.ran_any = False
        self._tw = create_terminal_writer(config, sys.stdout)

    def record_result(self, name, outcome):
        self.results[name] = outcome
        self.ran_any = True

    def write_to_file(self):
        if self.results != self.get_last_run():
            with open(self.filename, 'w') as f:
                f.write(json.dumps(self.results).rstrip() + '\n')

    def get_last_run(self):
        try:
            with open(self.filename) as f:
                return json.load(f)
        except IOError:
            pass
        return {}

    def diff_with_run(self, old):
        a = old
        b = self.results

        diffs = {}
        unhandled = set(b)

        for key, value in a.iteritems():
            if value != b.get(key):
                diffs[key] = (value, b.get(key))
            unhandled.discard(key)

        for key in unhandled:
            diffs[key] = (None, b[key])

        def _write_status(status):
            if status == 'passed':
                self._tw.write('PASSED', green=True)
            elif status == 'failed':
                self._tw.write('FAILED', red=True)
            elif status == 'skipped':
                self._tw.write('SKIPPED', yellow=True)
            elif status is None:
                self._tw.write('MISSING', cyan=True)
            else:
                self._tw.write(status.upper())

        new_failed = 0
        new_passed = 0

        self._tw.line()
        if not diffs:
            self._tw.sep('~', 'NO CHANGES SINCE LAST RUN')
            return

        self._tw.sep('~', 'CHANGES SINCE LAST RUN FOUND')
        for key, (old, new) in sorted(diffs.items()):
            self._tw.write(key.split('::')[-1] + ' ')
            _write_status(old)
            self._tw.write(' -> ')
            _write_status(new)
            self._tw.line()
            if new == 'failed':
                new_failed += 1
            elif new == 'passed':
                new_passed += 1

        self._tw.sep('~', 'new passed: %d, new failed: %d' %
                     (new_passed, new_failed))


def pytest_addoption(parser):
    group = parser.getgroup('general')
    group.addoption('--fail-debugskip',
           action='store_true', dest='fail_debugskip', default=False,
           help='do not ignore debugskip tests but fail them')


def pytest_configure(config):
    global diff_report
    diff_report = DiffReport(config)


def pytest_unconfigure(config):
    old_run = diff_report.get_last_run()
    if diff_report.ran_any:
        diff_report.write_to_file()
        diff_report.diff_with_run(old_run)


def change_some_failed_to_skipped(item, rep):
    if item.config.option.fail_debugskip:
        return
    if item.parent and 'test_crashprobe.py' in item.parent.nodeid and \
       '-debug-' in item.nodeid:
        rep.outcome = 'skipped'
        rep._wasdebugskip = True


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call':
        if rep.outcome == 'failed':
            change_some_failed_to_skipped(item ,rep)
        diff_report.record_result(item.nodeid, rep.outcome)


def pytest_report_teststatus(report):
    if getattr(report, '_wasdebugskip', False):
        return 'debugfailed', 'x', 'DEBUGFAIL'


@pytest.fixture(scope='module')
def res_path():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, 'res')


@pytest.fixture(scope='function')
def driver(request):
    from symsynd.driver import Driver
    rv = Driver()
    request.addfinalizer(rv.close)
    return rv


@pytest.fixture(scope='function')
def make_report_sym(request, driver):
    return lambda *args: ReportSymbolizer(driver, *args)
