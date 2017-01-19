import os
import json
import pytest
from symsynd.report import ReportSymbolizer

VERSION = '1.4.1 (201701191305)'
CPU = 'arm64'


def _load_dsyms_and_symbolize_stacktrace(filename, res_path, driver):
    filename_version = VERSION.replace(' ', '')
    with open(os.path.join(res_path, 'ext', VERSION, CPU,
        filename_version + filename.replace(filename_version, ''))) as f:
        report = json.load(f)

    bt = None
    dsym_paths = []
    dsyms_folder = os.path.join(res_path, 'ext', VERSION, 'dSYMs')
    for file in os.listdir(dsyms_folder):
        if file.endswith('.dSYM'):
            dsym_paths.append(os.path.join(dsyms_folder, file))

    rep = ReportSymbolizer(driver, dsym_paths, report['debug_meta']['images'])
    for thread in report['threads']['values']:
        if thread['crashed']:
            assert bt is None
            bt = rep.symbolize_backtrace(thread['stacktrace']['frames'])
    return bt, report


def test_pthread_list_lock_report(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Crash with _pthread_list_lock held-B25F873123CC4FA0A38CC487ABEF291D.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/01/
    # -[CRLCrashAsyncSafeThread crash] (CRLCrashAsyncSafeThread.m:41)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 41
    assert bt[22]['symbol_name'] == '-[CRLCrashAsyncSafeThread crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashAsyncSafeThread.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


@pytest.mark.xfail
def test_throw_c_pp_exception(res_path, driver):
    # http://www.crashprobe.com/ios/02/
    # Fails on every crash reporter
    raise Exception('Fails on every crash reporter')


def test_throw_objective_c_exception(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Throw Objective-C exception-F5C38540F071472192CFCA5F5CB602FC.json',
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
    assert bt[22]['line'] == 41
    assert bt[22]['symbol_name'] == '-[CRLCrashObjCException crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashObjCException.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_access_a_non_object_as_an_object(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Access a non-object as an object-4704C3CC7E5645A7834B4075094100E9.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/04/
    # -[CRLCrashNSLog crash] (CRLCrashNSLog.m:41)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 41
    assert bt[22]['symbol_name'] == '-[CRLCrashNSLog crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashNSLog.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_crash_inside_objc_msg_send(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Crash inside objc_msgSend()-A111F4B5D10D4104B3F4BC1FFF477A6D.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/05/
    # -[CRLCrashObjCMsgSend crash] (CRLCrashObjCMsgSend.m:47)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 47
    assert bt[22]['symbol_name'] == '-[CRLCrashObjCMsgSend crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashObjCMsgSend.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_message_a_released_object(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Message a released object-86624D03EE1B466DBF7749116939B221.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/06/
    # -[CRLCrashReleasedObject crash]_block_invoke (CRLCrashReleasedObject.m:51-53)
    # -[CRLCrashReleasedObject crash] (CRLCrashReleasedObject.m:49)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 51
    assert bt[22]['symbol_name'] == '__31-[CRLCrashReleasedObject crash]_block_invoke'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashReleasedObject.m'
    assert bt[21]['line'] == 49
    assert bt[21]['symbol_name'] == '-[CRLCrashReleasedObject crash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLCrashReleasedObject.m'
    assert bt[20]['line'] == 53
    assert bt[20]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[20]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_write_to_a_read_only_page(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Write to a read-only page-D3FA9EF36DCD4A90B5A0CAF8C12ED999.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/07/
    # -[CRLCrashROPage crash] (CRLCrashROPage.m:42)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 42
    assert bt[22]['symbol_name'] == '-[CRLCrashROPage crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashROPage.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_execute_a_privileged_instruction(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Execute a privileged instruction-940551E8FDCB4F7EBD3B7BB2DBD5C697.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/08/
    # ARMv7: -[CRLCrashPrivInst crash] (CRLCrashPrivInst.m:42)
    # ARM64: -[CRLCrashPrivInst crash] (CRLCrashPrivInst.m:52)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 52
    assert bt[22]['symbol_name'] == '-[CRLCrashPrivInst crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashPrivInst.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_execute_an_undefined_instruction(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Execute an undefined instruction-3E6925CDE19A49D99EC3D1751EBC8D08.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/09/
    # ARMv7: -[CRLCrashUndefInst crash] (CRLCrashUndefInst.m:42)
    # ARM64: -[CRLCrashUndefInst crash] (CRLCrashUndefInst.m:50)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 50
    assert bt[22]['symbol_name'] == '-[CRLCrashUndefInst crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashUndefInst.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_dereference_a_null_pointer(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Dereference a NULL pointer-A7E0CB80A49F48528A27FF20BA279397.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/10/
    # -[CRLCrashNULL crash] (CRLCrashNULL.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 37
    assert bt[22]['symbol_name'] == '-[CRLCrashNULL crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashNULL.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_dereference_a_bad_pointer(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Dereference a bad pointer-120F22EC7CE14D088B0DA04BC78A4BFB.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/11/
    # ARMv7: -[CRLCrashGarbage crash] (CRLCrashGarbage.m:48)
    # ARM64: -[CRLCrashGarbage crash] (CRLCrashGarbage.m:52)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 52
    assert bt[22]['symbol_name'] == '-[CRLCrashGarbage crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashGarbage.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_jump_into_an_nx_page(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Jump into an NX page-B511C6F2659F4FB5BA07E14D7D6A7B26.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/12/
    # -[CRLCrashNXPage crash] (CRLCrashNXPage.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 37
    assert bt[22]['symbol_name'] == '-[CRLCrashNXPage crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashNXPage.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_stack_overflow(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Stack overflow-D6D8C3E5738E48119007E9C48D8C26E9.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/13/
    # -[CRLCrashStackGuard crash] (CRLCrashStackGuard.m:38) or line 39
    # -[CRLCrashStackGuard crash] (CRLCrashStackGuard.m:39)
    # ...
    # -[CRLCrashStackGuard crash] (CRLCrashStackGuard.m:39)
    assert bt is not None
    #import pprint; pprint.pprint(bt)
    assert bt[29]['line'] == 38
    assert bt[29]['symbol_name'] == '-[CRLCrashStackGuard crash]'
    assert bt[29]['filename'].rsplit('/', 1)[-1] == 'CRLCrashStackGuard.m'


def test_call_builtin_trap(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Call __builtin_trap()-0A27E23FB60E446197F6B830921BB287.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/14/
    # -[CRLCrashTrap crash] (CRLCrashTrap.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 37
    assert bt[22]['symbol_name'] == '-[CRLCrashTrap crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashTrap.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_call_abort(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Call abort()-3784D09D3CEA446283B8938EAB71D37E.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/15/
    # -[CRLCrashAbort crash] (CRLCrashAbort.m:37)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 37
    assert bt[22]['symbol_name'] == '-[CRLCrashAbort crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashAbort.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


@pytest.mark.xfail
def test_corrupt_malloc_s_internal_tracking_information(res_path, driver):
    # http://www.crashprobe.com/ios/16/
    # App crashes and generates no report
    raise Exception('App crashes and generates no report')


@pytest.mark.xfail
def test_corrupt_the_objective_c_runtime_s_structures(res_path, driver):
    # http://www.crashprobe.com/ios/17/
    # App crashes and generates no report
    raise Exception('App crashes and generates no report')


def test_dwarf_unwinding(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-DWARF Unwinding-BBF334A7B61D48A7BF854373161C9AE1.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/18/
    # CRLFramelessDWARF_test_crash (CRLFramelessDWARF.m:35)
    # -[CRLFramelessDWARF crash] (CRLFramelessDWARF.m:49)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    #import pprint; pprint.pprint(bt)
    assert len(bt) > 3
    assert bt[2]['line'] == 35
    assert bt[2]['symbol_name'] == 'CRLFramelessDWARF_test_crash'
    assert bt[2]['filename'].rsplit('/', 1)[-1] == 'CRLFramelessDWARF.m'
    assert bt[1]['line'] == 49
    assert bt[1]['symbol_name'] == '-[CRLFramelessDWARF crash]'
    assert bt[1]['filename'].rsplit('/', 1)[-1] == 'CRLFramelessDWARF.m'
    assert bt[0]['line'] == 53
    assert bt[0]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_overwrite_link_register_then_crash(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Overwrite link register, then crash-06F17D84FA1A40C78F388F9A4CDE940D.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/19/
    # -[CRLCrashOverwriteLinkRegister crash] (CRLCrashOverwriteLinkRegister.m:53)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 53
    assert bt[22]['symbol_name'] == '-[CRLCrashOverwriteLinkRegister crash]'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashOverwriteLinkRegister.m'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'


def test_smash_the_bottom_of_the_stack(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Smash the bottom of the stack-7FFA9355A6014343AB16AF1140F0CA7B.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/20/
    # -[CRLCrashSmashStackBottom crash] (CRLCrashSmashStackBottom.m:54)
    assert bt is not None
    assert len(bt) > 0
    assert bt[0]['line'] == 54
    assert bt[0]['symbol_name'] == '-[CRLCrashSmashStackBottom crash]'
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLCrashSmashStackBottom.m'


def test_smash_the_top_of_the_stack(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Smash the top of the stack-04DADC5BB6B14C9E86DBDE9E2535485A.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/21/
    # -[CRLCrashSmashStackTop crash] (CRLCrashSmashStackTop.m:54)
    assert bt is not None
    assert len(bt) > 0
    assert bt[0]['line'] == 54
    assert bt[0]['symbol_name'] == '-[CRLCrashSmashStackTop crash]'
    assert bt[0]['filename'].rsplit('/', 1)[-1] == 'CRLCrashSmashStackTop.m'


def test_swift(res_path, driver):
    bt, report = _load_dsyms_and_symbolize_stacktrace(
        '1.4.1(201701191305)-Swift-FA3B2181D3FB40D99C83C8BFB574B532.json',
        res_path,
        driver
    )

    # http://www.crashprobe.com/ios/22/
    # @objc CrashLibiOS.CRLCrashSwift.crash (CrashLibiOS.CRLCrashSwift)() -> () (CRLCrashSwift.swift:36)
    # -[CRLDetailViewController doCrash] (CRLDetailViewController.m:53)
    assert bt is not None
    assert bt[22]['line'] == 36
    assert bt[22]['symbol_name'] == '@objc CrashLibiOS.CRLCrashSwift.crash (CrashLibiOS.CRLCrashSwift)() -> ()'
    assert bt[22]['filename'].rsplit('/', 1)[-1] == 'CRLCrashSwift.swift'
    assert bt[21]['line'] == 53
    assert bt[21]['symbol_name'] == '-[CRLDetailViewController doCrash]'
    assert bt[21]['filename'].rsplit('/', 1)[-1] == 'CRLDetailViewController.m'
