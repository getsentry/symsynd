import os
import gc
import json
from symsynd.driver import Driver
from symsynd.report import ReportSymbolizer


here = os.path.abspath(os.path.dirname(__file__))
res_path = os.path.join(here, 'tests', 'res')


with open(os.path.join(res_path, 'crash-report.json')) as f:
    report = json.load(f)
driver = Driver()


def iterate():
    bt = None
    dsym_path = os.path.join(res_path, 'Crash-Tester.app.dSYM')
    rep = ReportSymbolizer(driver, [dsym_path],
                           report['binary_images'])
    for thread in report['crash']['threads']:
        if thread['crashed']:
            assert bt is None
            bt = rep.symbolize_backtrace(thread['backtrace']['contents'])

    assert bt is not None


def main():
    while 1:
        iterate()
        gc.collect()


if __name__ == '__main__':
    main()
