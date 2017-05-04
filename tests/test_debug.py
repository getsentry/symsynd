import os
from uuid import UUID
from symsynd.libdebug import DebugInfo, get_cpu_name, get_cpu_type_tuple


def test_cpu_names():
    assert get_cpu_name(12, 9) == 'armv7'
    tup = get_cpu_type_tuple('arm64')
    assert get_cpu_name(*tup) == 'arm64'


def test_uuid(res_path):
    ct_dsym_path = os.path.join(
        res_path, 'Crash-Tester.app.dSYM', 'Contents', 'Resources',
        'DWARF', 'Crash-Tester')
    di = DebugInfo.open_path(ct_dsym_path)
    uuids = [(s.cpu_name, str(s.uuid)) for s in di.get_variants()]
    assert uuids == [
        ('armv7', '8094558b-3641-36f7-ba80-a1aaabcf72da'),
        ('arm64', 'f502dec3-e605-36fd-9b3d-7080a7c6f4fc'),
    ]


def test_variants(res_path):
    ct_dsym_path = os.path.join(
        res_path, 'Crash-Tester.app.dSYM', 'Contents', 'Resources',
        'DWARF', 'Crash-Tester')
    di = DebugInfo.open_path(ct_dsym_path)
    res = sorted([x.__dict__ for x in di.get_variants()],
                  key=lambda x: x['cpu_name'])
    assert res == [
        {'vmaddr': 4294967296L,
         'vmsize': 294912L,
         'cpu_name': u'arm64',
         'uuid': UUID('f502dec3-e605-36fd-9b3d-7080a7c6f4fc'),
         'name': u'<unknown>'},
        {'vmaddr': 16384L,
         'vmsize': 262144L,
         'cpu_name': u'armv7',
         'uuid': UUID('8094558b-3641-36f7-ba80-a1aaabcf72da'),
         'name': u'<unknown>'}
    ]
