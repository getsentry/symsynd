import os
import sys
import errno
import subprocess
from threading import Lock

from symsynd.utils import which
from symsynd.mach import is_valid_cpu_name
from symsynd.swift import demangle_symbol as demangle_swift_symbol


devnull = open(os.path.devnull, 'a')


SYMBOLIZER_SEARCHPATHS = []
if sys.platform == 'darwin':
    SYMBOLIZER_SEARCHPATHS.append('/usr/local/opt/llvm/bin')


def qm_to_none(value):
    if value == '??':
        return None
    return value


def normalize_dsym_path(p):
    if '\x00' in p or '"' in p or '\n' in p or '\r' in p:
        raise ValueError('Invalid character in dsym path')
    p = os.path.abspath(p)
    if not os.path.isfile(p):
        raise IOError(errno.ENOENT, 'dsym file not found (%s)' % p)
    return p


def find_llvm_symbolizer():
    p = os.environ.get('LLVM_SYMBOLIZER_PATH')
    if p:
        return p

    p = which('llvm-symbolizer', extra_paths=SYMBOLIZER_SEARCHPATHS)
    if p is not None:
        return p

    for ver in xrange(12, 3, -1):
        p = which('llvm-symbolizer-3.%d' % ver)
        if p is not None:
            return p


class Driver(object):

    def __init__(self, symbolizer_path=None):
        if symbolizer_path is None:
            symbolizer_path = find_llvm_symbolizer()
        self._proc = subprocess.Popen([symbolizer_path],
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=devnull)
        self._lock = Lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def close(self):
        if self._proc is not None:
            self._proc.kill()
            self._proc = None

    def symbolize(self, dsym_path, image_vmaddr, image_addr,
                  instruction_addr, cpu_name):
        if self._proc is None:
            raise RuntimeError('Symbolizer is closed')
        if not is_valid_cpu_name(cpu_name):
            raise ValueError('"%s" is not a valid cpu name' % cpu_name)
        dsym_path = normalize_dsym_path(dsym_path)

        addr = image_vmaddr + instruction_addr - image_addr
        stdout = self._proc.stdout
        with self._lock:
            self._proc.stdin.write('"%s:%s" 0x%x\n' % (
                dsym_path,
                cpu_name,
                addr,
            ))
            sym = stdout.readline().rstrip()
            location = stdout.readline().rstrip()
            stdout.readline()

        pieces = location.rsplit(':', 3)
        sym = qm_to_none(sym)

        if sym is not None:
            sym = (demangle_swift_symbol(sym) or sym).decode('utf-8', 'replace')

        return {
            'symbol_name': sym,
            'filename': qm_to_none(pieces[0].decode('utf-8')),
            'line': int(pieces[1]),
            'column': int(pieces[2]),
        }
