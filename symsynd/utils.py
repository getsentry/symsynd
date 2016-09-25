import os
from contextlib import contextmanager
from itertools import chain
from symsynd._compat import int_types


def which(prog, extra_paths=None):
    path = os.environ['PATH'].split(os.path.pathsep)
    if extra_paths:
        path = chain(path, extra_paths)
    for p in path:
        p = os.path.join(p, prog)
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p


@contextmanager
def _dummy_bar(items):
    yield items


def progressbar(items, prefix, enabled=True):
    if enabled:
        label = '%-20s' % prefix
        import click
        return click.progressbar(items, label=label)
    return _dummy_bar(items)


def parse_addr(x):
    if x is None:
        return 0
    if isinstance(x, int_types):
        return x
    if isinstance(x, basestring):
        if x[:2] == '0x':
            return int(x[2:], 16)
        return int(x)
    raise ValueError('Unsupported address format %r' % (x,))
