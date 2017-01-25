import os
import errno
from threading import RLock

from symsynd.utils import parse_addr, timedsection
from symsynd.macho.arch import is_valid_cpu_name, get_macho_vmaddr
from symsynd.demangle import demangle_symbol
from symsynd.exceptions import SymbolicationError
from symsynd.libsymbolizer import Symbolizer


SIGILL = 4
SIGBUS = 10
SIGSEGV = 11


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


def get_previous_instruction(addr, cpu_name):
    if cpu_name.startswith('arm64'):
        return (addr & -4) - 4
    elif cpu_name.startswith('arm'):
        return (addr & -2) - 2
    else:
        return addr - 1


def get_next_instruction(addr, cpu_name):
    if cpu_name.startswith('arm64'):
        return (addr & -4) + 4
    elif cpu_name.startswith('arm'):
        return (addr & -2) + 2
    else:
        return addr + 1


def truncate_instruction(addr, cpu_name):
    if cpu_name.startswith('arm64'):
        return addr & -4
    elif cpu_name.startswith('arm'):
        return addr & -2
    return addr


def find_instruction(addr, cpu_name, meta=None):
    # In case we're not on the crashing frame we apply a simple heuristic:
    # since we're most likely dealing with return addresses we just assume
    # that the call is one instruction behind the current one.
    if not meta or meta.get('frame_number') != 0:
        return get_previous_instruction(addr, cpu_name)

    # In case registers are available we can check if the PC register
    # does not match the given address we have from the first frame.
    # If that is the case and we got one of a few signals taht are likely
    # it seems that going with one instruction back is actually the
    # correct thing to do.
    regs = meta.get('registers')
    if cpu_name[:3] == 'arm' and regs and 'pc' in regs \
       and parse_addr(regs['pc']) != addr and \
       meta.get('signal') in (SIGILL, SIGBUS, SIGSEGV):
        return get_previous_instruction(addr, cpu_name)

    return addr


def convert_symbol(sym, demangle=True):
    symbol_name = sym[0]
    if demangle:
        symbol_name = demangle_symbol(symbol_name)
    return {
        'symbol_name': symbol_name,
        'filename': sym[1],
        'line': sym[2],
        'column': sym[3],
    }


class Driver(object):
    """The main symbolication driver.  This abstracts around a low level
    LLVM based symbolizer that works with DWARF files.  It's recommended to
    explicitly close the driver to ensure memory cleans up timely.
    """

    def __init__(self):
        self._lock = RLock()
        self._proc = None
        self._closed = False
        self._symbolizer = Symbolizer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def close(self):
        if not self._closed:
            self._symbolizer.close()
        self._closed = True

    def symbolize(self, dsym_path, image_vmaddr, image_addr,
                  instruction_addr, cpu_name, silent=True,
                  demangle=True, symbolize_inlined=False,
                  meta=None):
        """Symbolizes a single frame based on the information provided.  If
        the symbolication fails `None` is returned in default more or a
        an exception is raised if `silent` is disabled.

        `dsym_path` is the path to the dsym file on the file system.
        `image_vmaddr` is the slide of the image.  For most situations this
        can just be set to `0`.  If it's zero or unset we will attempt to
        find the slide from the dsym file.  `image_addr` is the canonical
        image address as loaded.  `instruction_addr` is the address where the
        error most likely happend (some fuzziness is performed since the
        assumption is that these addresses are based on the return addresses
        on the stack.  See `meta` for more information).

        `cpu_name` is the CPU name.  It follows general apple conventions and
        is used to special case certain behavior and look up the right
        symbols.  Common names are `armv7` and `arm64`.

        The `demangle` parameter controls if demangling should be performed
        or not.  Currently C++ and (some version of) Swift demangling is
        supported.

        Additionally if `symbolize_inlined` is set to `True` then a list of
        frames is returned instead which might contain inlined frames.  In
        that case the return value might be an empty list instead.

        `meta` is a dictionary of meta information that can help with
        the symbolication process.  If it's empty then all heuristics are
        disabled.  The following keys are currently supported:

        -   ``frame_number``: the number of the source frame.  If this is set
            to ``0`` then the crashing frame is assumed and various heuristics
            are enabled.
        -   ``signal``: the posix signal number if the execution was aborted
            with a posix signal.  In particular this can help fix some issues
            with assuming wrong addresses in limited circumstances.
        -   ``registers``: a dictionary of register values.  The key is the
            name of the register and the value is the register value as
            hexadecimal string or integer.  The only register that currently
            matters is ``pc`` on arm CPUs however this might change in the
            future.
        """
        if self._closed:
            raise RuntimeError('Symbolizer is closed')
        dsym_path = normalize_dsym_path(dsym_path)

        image_vmaddr = parse_addr(image_vmaddr)
        if not image_vmaddr:
            image_vmaddr = get_macho_vmaddr(dsym_path, cpu_name) or 0

        image_addr = parse_addr(image_addr)
        instruction_addr = parse_addr(instruction_addr)

        try:
            if not is_valid_cpu_name(cpu_name):
                raise SymbolicationError('"%s" is not a valid cpu name' % cpu_name)

            instruction_addr = find_instruction(instruction_addr, cpu_name,
                                                meta)
            addr = image_vmaddr + instruction_addr - image_addr

            with self._lock:
                with timedsection('symbolize'):
                    if symbolize_inlined:
                        syms = self._symbolizer.symbolize_inlined(
                            dsym_path, addr, cpu_name)
                        return [convert_symbol(sym, demangle) for sym in syms]
                    else:
                        sym = self._symbolizer.symbolize(
                            dsym_path, addr, cpu_name)
                        return convert_symbol(sym, demangle)
        except SymbolicationError:
            if not silent:
                raise
            if symbolize_inlined:
                return []
            return None
