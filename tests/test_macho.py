from symsynd import mach


def test_cpu_names():
    assert mach.get_cpu_name(12, 9) == 'armv7'


def test_uuid(ct_dsym_path):
    uuids = mach.get_macho_uuids(ct_dsym_path)
    assert uuids == [
        '8094558b-3641-36f7-ba80-a1aaabcf72da',
        'f502dec3-e605-36fd-9b3d-7080a7c6f4fc'
    ]
