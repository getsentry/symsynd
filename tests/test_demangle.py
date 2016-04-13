from symsynd.demangle import demangle_swift_symbol, demangle_cpp_symbol


def test_swift_demangle():
    mangled = '_TFC12Swift_Tester14ViewController11doSomethingfS0_FT_T_'
    expected = (
        'Swift_Tester.ViewController.doSomething '
        '(Swift_Tester.ViewController) -> () -> ()'
    )
    assert demangle_swift_symbol(mangled) == expected


def test_cpp_demangle():
    mangled = '_ZN6google8protobuf2io25CopyingInputStreamAdaptor4SkipEi'
    expected = 'google::protobuf::io::CopyingInputStreamAdaptor::Skip(int)'
    assert demangle_cpp_symbol(mangled) == expected


def test_demangle_failure_underscore():
    mangled = '_some_name'
    assert demangle_swift_symbol(mangled) is None


def test_demangle_failure_no_underscore():
    mangled = 'some_other_name'
    assert demangle_swift_symbol(mangled) is None
