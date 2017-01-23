import os
import json
import pytest
from symsynd.report import ReportSymbolizer


TEST_PARAMETER = [
('1.4.1 (201701191305)', 'arm64'),
('1.4.1 (201701200943)', 'armv7')
]


def _load_dsyms_and_symbolize_stacktrace(filename, version, cpu, res_path, driver):
    filename_version = version.replace(' ', '')
    path = os.path.join(res_path, 'ext', version, cpu, filename)
    if not os.path.isfile(path):
        pytest.skip("not test file found")
    with open(path) as f:
        report = json.load(f)

    bt = None
    dsym_paths = []
    dsyms_folder = os.path.join(res_path, 'ext', version, 'dSYMs')
    for file in os.listdir(dsyms_folder):
        if file.endswith('.dSYM'):
            dsym_paths.append(os.path.join(dsyms_folder, file))

    rep = ReportSymbolizer(driver, dsym_paths, report['debug_meta']['images'])
    for thread in report['threads']['values']:
        if thread['crashed']:
            assert bt is None
            bt = rep.symbolize_backtrace(thread['stacktrace']['frames'])
    return bt, report


def _filter_system_frames(bt):
    new_bt = []
    for frame in bt:
        for package in ['CrashProbeiOS', 'CrashLibiOS']:
            if package in frame['package']:
                if frame.get('filename') and 'main.m' in frame.get('filename'):
                    continue;
                new_bt.append(frame)
    return new_bt

@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_pthread_list_lock_report(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Crash with _pthread_list_lock held.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/01/
    # -[CRLCrashAsyncSafeThread crash] (CRLCrashAsyncSafeThread.m:41)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashAsyncSafeThread crash]'
    assert bt[1]['line'] == 41
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashAsyncSafeThread.m'


@pytest.mark.xfail(reason='C++ Exception handling doesn\'t work')
@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_throw_c_pp_exception(res_path, driver, version, cpu):
    # http://www.crashprobe.com/ios/02/
    # Fails on every crash reporter
    raise Exception('Fails on every crash reporter')


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_throw_objective_c_exception(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Throw Objective-C exception.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/03/
    # NSGenericException: An uncaught exception! SCREAM.
    # -[CRLCrashObjCException crash] (CRLCrashObjCException.m:41)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    if 'NSGenericException: An uncaught exception! SCREAM.' not in report['exception']['values'][0]['value']:
        pytest.xfail('Crash reason not found')
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashObjCException crash]'
    assert bt[1]['line'] == 41
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashObjCException.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_access_a_non_object_as_an_object(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Access a non-object as an object.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/04/
    # -[CRLCrashNSLog crash] (CRLCrashNSLog.m:41)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashNSLog crash]'
    assert bt[1]['line'] == 41
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashNSLog.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_crash_inside_objc_msg_send(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Crash inside objc_msgSend().json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/05/
    # -[CRLCrashObjCMsgSend crash] (CRLCrashObjCMsgSend.m:47)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashObjCMsgSend crash]'
    assert bt[1]['line'] == 47
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashObjCMsgSend.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_message_a_released_object(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Message a released object.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/06/
    # -[CRLCrashReleasedObject crash]_block_invoke (CRLCrashReleasedObject.m:51-53)
    # -[CRLCrashReleasedObject crash] (CRLCrashReleasedObject.m:49)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[2]['symbol_name'] == '__31-[CRLCrashReleasedObject crash]_block_invoke'
    assert bt[2]['line'] == 51
    assert bt[2]['filename'].rsplit('/', 1)[-1] == 'CRLCrashReleasedObject.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashReleasedObject crash]'
    assert bt[1]['line'] == 49
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashReleasedObject.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_write_to_a_read_only_page(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Write to a read-only page.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/07/
    # -[CRLCrashROPage crash] (CRLCrashROPage.m:42)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashROPage crash]'
    assert bt[1]['line'] == 42
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashROPage.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_execute_a_privileged_instruction(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Execute a privileged instruction.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/08/
    # ARMv7: -[CRLCrashPrivInst crash] (CRLCrashPrivInst.m:42)
    # ARM64: -[CRLCrashPrivInst crash] (CRLCrashPrivInst.m:52)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashPrivInst crash]'
    assert bt[1]['line'] == cpu == 'arm64' and 52 or 42
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashPrivInst.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_execute_an_undefined_instruction(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Execute an undefined instruction.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/09/
    # ARMv7: -[CRLCrashUndefInst crash] (CRLCrashUndefInst.m:42)
    # ARM64: -[CRLCrashUndefInst crash] (CRLCrashUndefInst.m:50)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashUndefInst crash]'
    assert bt[1]['line'] == cpu == 'arm64' and 50 or 42
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashUndefInst.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_dereference_a_null_pointer(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
    'Dereference a NULL pointer.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/10/
    # -[CRLCrashNULL crash] (CRLCrashNULL.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashNULL crash]'
    assert bt[1]['line'] == 37
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashNULL.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_dereference_a_bad_pointer(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Dereference a bad pointer.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/11/
    # ARMv7: -[CRLCrashGarbage crash] (CRLCrashGarbage.m:48)
    # ARM64: -[CRLCrashGarbage crash] (CRLCrashGarbage.m:52)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashGarbage crash]'
    assert bt[1]['line'] == cpu == 'arm64' and 52 or 48
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashGarbage.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_jump_into_an_nx_page(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
    'Jump into an NX page.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/12/
    # -[CRLCrashNXPage crash] (CRLCrashNXPage.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashNXPage crash]'
    assert bt[1]['line'] == 37
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashNXPage.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_stack_overflow(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Stack overflow.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/13/
    # -[CRLCrashStackGuard crash] (CRLCrashStackGuard.m:38) or line 39
    # -[CRLCrashStackGuard crash] (CRLCrashStackGuard.m:39)
    # ...
    # -[CRLCrashStackGuard crash] (CRLCrashStackGuard.m:39)
    assert bt is not None
    bt = _filter_system_frames(bt)
    #import pprint; pprint.pprint(bt)
    assert bt[29]['symbol_name'] == '-[CRLCrashStackGuard crash]'
    assert bt[29]['line'] == 38
    assert bt[29]['filename'].rsplit('/', 1)[-1] == 'CRLCrashStackGuard.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_call_builtin_trap(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Call __builtin_trap().json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/14/
    # -[CRLCrashTrap crash] (CRLCrashTrap.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashTrap crash]'
    assert bt[1]['line'] == 37
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashTrap.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_call_abort(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Call abort().json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/15/
    # -[CRLCrashAbort crash] (CRLCrashAbort.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashAbort crash]'
    assert bt[1]['line'] == 37
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashAbort.m'


@pytest.mark.xfail(reason='App crash does not generate any report')
@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_corrupt_malloc_s_internal_tracking_information(res_path, driver, version, cpu):
    # http://www.crashprobe.com/ios/16/
    # App crashes and generates no report
    raise Exception('App crashes and generates no report')


@pytest.mark.xfail(reason='App crash does not generate any report')
@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_corrupt_the_objective_c_runtime_s_structures(res_path, driver, version, cpu):
    # http://www.crashprobe.com/ios/17/
    # App crashes and generates no report
    raise Exception('App crashes and generates no report')


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_dwarf_unwinding(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'DWARF Unwinding.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/18/
    # CRLFramelessDWARF_test_crash (CRLFramelessDWARF.m:35)
    # -[CRLFramelessDWARF crash] (CRLFramelessDWARF.m:49)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert len(bt) > 3
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[2]['symbol_name'] == 'CRLFramelessDWARF_test_crash'
    assert bt[2]['line'] == 35
    assert bt[2]['filename'].rsplit('/', 1)[-1] == 'CRLFramelessDWARF.m'
    assert bt[1]['symbol_name'] == '-[CRLFramelessDWARF crash]'
    assert bt[1]['line'] == 49
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLFramelessDWARF.m'

@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_overwrite_link_register_then_crash(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Overwrite link register, then crash.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/19/
    # -[CRLCrashOverwriteLinkRegister crash] (CRLCrashOverwriteLinkRegister.m:53)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '-[CRLCrashOverwriteLinkRegister crash]'
    assert bt[1]['line'] == 53
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashOverwriteLinkRegister.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_smash_the_bottom_of_the_stack(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Smash the bottom of the stack.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/20/
    # -[CRLCrashSmashStackBottom crash] (CRLCrashSmashStackBottom.m:54)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert len(bt) > 0
    assert bt[0]['symbol_name'] == '-[CRLCrashSmashStackBottom crash]'
    assert bt[0]['line'] == 54
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLCrashSmashStackBottom.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_smash_the_top_of_the_stack(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Smash the top of the stack.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/21/
    # -[CRLCrashSmashStackTop crash] (CRLCrashSmashStackTop.m:54)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert len(bt) > 0
    assert bt[0]['symbol_name'] == '-[CRLCrashSmashStackTop crash]'
    assert bt[0]['line'] == 54
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLCrashSmashStackTop.m'


@pytest.mark.parametrize("version, cpu", TEST_PARAMETER)
def test_swift(res_path, driver, version, cpu):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        'Swift.json',
        version,
        cpu,
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/22/
    # @objc CrashLibiOS.CRLCrashSwift.crash (CrashLibiOS.CRLCrashSwift)() -> () (CRLCrashSwift.swift:36)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    bt = _filter_system_frames(bt)
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['line'] == 53
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
    assert bt[1]['symbol_name'] == '@objc CrashLibiOS.CRLCrashSwift.crash () -> ()'
    assert bt[1]['line'] == 36
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLCrashSwift.swift'

