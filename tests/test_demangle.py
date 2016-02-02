from symsynd.swift import demangle_symbol


def test_swift_demangle():
    mangled = '_TFC12Swift_Tester14ViewController11doSomethingfS0_FT_T_'
    expected = (
        'Swift_Tester.ViewController.doSomething '
        '(Swift_Tester.ViewController) -> () -> ()'
    )
    assert demangle_symbol(mangled) == expected


def test_demangle_failure_underscore():
    mangled = '_some_name'
    assert demangle_symbol(mangled) is None


def test_demangle_failure_no_underscore():
    mangled = 'some_other_name'
    assert demangle_symbol(mangled) is None
