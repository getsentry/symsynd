from symsynd.demangle import demangle_swift_symbol, demangle_cpp_symbol


def test_swift_demangle():
    mangled = '_TFC12Swift_Tester14ViewController11doSomethingfS0_FT_T_'
    expected = (
        'Swift_Tester.ViewController.doSomething '
        '(Swift_Tester.ViewController) -> () -> ()'
    )
    assert demangle_swift_symbol(mangled) == expected


def test_swift_demangle_options():
    mangled = (
        '_TTWVSC29UIApplicationLaunchOptionsKeys21_ObjectiveCBridgeable'
        '5UIKitZFS0_36_unconditionallyBridgeFromObjectiveCfGSqwx15_'
        'ObjectiveCType_x'
    )
    default_expected = (
        u'protocol witness for static Swift._ObjectiveCBridgeable._'
        u'unconditionallyBridgeFromObjectiveC (Swift.Optional<A._'
        u'ObjectiveCType>) -> A in conformance __C.'
        u'UIApplicationLaunchOptionsKey : Swift._ObjectiveCBridgeable '
        u'in UIKit'
    )
    simplified_expected = (
        u'protocol witness for static _ObjectiveCBridgeable._'
        u'unconditionallyBridgeFromObjectiveC(A._ObjectiveCType?) -> '
        u'A in conformance UIApplicationLaunchOptionsKey'
    )

    assert demangle_swift_symbol(mangled) == default_expected
    assert demangle_swift_symbol(mangled, simplified=True) == simplified_expected


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
