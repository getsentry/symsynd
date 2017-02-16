from symsynd.heuristics import get_ip_register


def test_ip_reg():
    assert get_ip_register({'pc': '0x42'}, 'arm7') == int('42', 16)
    assert get_ip_register({}, 'arm7') == None
    assert get_ip_register({}, 'x86') == None
