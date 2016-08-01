from __future__ import absolute_import, print_function, unicode_literals

import os
import sys
import errno
import subprocess
from threading import RLock

from symsynd.utils import which, parse_addr
from symsynd.macho.arch import is_valid_cpu_name
from symsynd.demangle import demangle_symbol


devnull = open(os.path.devnull, 'a')


SYMBOLIZER_SEARCHPATHS = []
if sys.platform == 'darwin':
    SYMBOLIZER_SEARCHPATHS.append('/usr/local/opt/llvm/bin')


class SymbolicationError(Exception):
    pass


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

    p = which('llvm-symbolizer')
    if p is not None:
        return p

    for ver in range(12, 3, -1):
        p = which('llvm-symbolizer-3.%d' % ver)
        if p is not None:
            return p

    p = which('llvm-symbolizer')
    if p is not None:
        return p

    raise EnvironmentError('Could not locate llvm-symbolizer')


class Driver(object):

    def __init__(self, symbolizer_path=None):
        if symbolizer_path is None:
            symbolizer_path = find_llvm_symbolizer()
        self.symbolizer_path = symbolizer_path
        self._lock = RLock()
        self._proc = None
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def close(self):
        self._closed = True
        if self._proc is not None:
            self.kill()

    def kill(self):
        self._proc.kill()
        self._proc = None

    def get_proc(self):
        if self._proc is not None:
            return self._proc
        with self._lock:
            if self._proc is None:
                self._proc = subprocess.Popen([self.symbolizer_path],
                                              stdin=subprocess.PIPE,
                                              stdout=subprocess.PIPE,
                                              stderr=devnull)
            return self._proc

    def symbolize(self, dsym_path, image_vmaddr, image_addr,
                  instruction_addr, cpu_name, uuid=None, silent=True):
        if self._closed:
            raise RuntimeError('Symbolizer is closed')
        if not is_valid_cpu_name(cpu_name):
            raise ValueError('"%s" is not a valid cpu name' % cpu_name)
        dsym_path = normalize_dsym_path(dsym_path)

        image_vmaddr = parse_addr(image_vmaddr)
        image_addr = parse_addr(image_addr)
        instruction_addr = parse_addr(instruction_addr)

        addr = image_vmaddr + instruction_addr - image_addr

        try:
            try:
                with self._lock:
                    input_command = '"%s:%s" 0x%x\n' % (
                        dsym_path,
                        cpu_name,
                        addr,
                    )
                    proc = self.get_proc()
                    proc.stdin.write(input_command)
                    proc.stdin.flush()

                    sym_resp = proc.stdout.readline()
                    if sym_resp == input_command:
                        raise SymbolicationError('Symbolizer echoed garbage.')

                    location_resp = proc.stdout.readline()
                    empty_line = proc.stdout.readline()

                    if not all([sym_resp, location_resp, empty_line]):
                        raise SymbolicationError('Symbolizer crashed.')
                    if empty_line.strip():
                        raise SymbolicationError('Symbolizer produced '
                                                 'extra garbage: %r' %
                                                 empty_line)
            except Exception:
                self.kill()
                raise
        except SymbolicationError:
            if not silent:
                raise
            sym = '??'
            location = '??:0:0'
        else:
            sym = sym_resp.rstrip()
            location = location_resp.rstrip()

        pieces = location.rsplit(':', 3)
        sym = qm_to_none(sym)

        if sym is not None:
            sym = (demangle_symbol(sym) or sym).decode('utf-8', 'replace')
        elif not silent:
            raise SymbolicationError('Symbolizer could not find symbol')

        return {
            'symbol_name': sym,
            'filename': qm_to_none(pieces[0].decode('utf-8')),
            'line': int(pieces[1] or '0'),
            'column': int(pieces[2] or '0'),
            'uuid': uuid,
        }
