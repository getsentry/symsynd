import sys


PY2 = sys.version_info[0] == 2


if PY2:
    text_type = unicode
    string_types = (unicode, str)
    int_types = (int, long)
else:
    text_type = str
    string_types = (str,)
    int_types = (int,)


def to_bytes(x):
    if isinstance(x, text_type):
        x = x.encode('utf-8')
    return x
