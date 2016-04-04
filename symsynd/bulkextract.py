import os
import re
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess

from symsynd.utils import which, progressbar
from symsynd.mach import get_macho_uuids
from symsynd.driver import devnull


_arch_intro_re = re.compile(r'^.*? \(for architecture (.*?)\):$')
_base_path_segment = re.compile(r'^\d+\.\d+ \([a-zA-Z0-9]+\)$')


NM_SEARCHPATHS = []
if sys.platform == 'darwin':
    NM_SEARCHPATHS.append('/usr/local/opt/llvm/bin')


def find_llvm_nm():
    p = os.environ.get('LLVM_NM_PATH')
    if p:
        return p

    p = which('llvm-nm', extra_paths=NM_SEARCHPATHS)
    if p is not None:
        return p

    for ver in xrange(12, 3, -1):
        p = which('llvm-nm-3.%d' % ver)
        if p is not None:
            return p

    sys_nm = which('nm')
    if sys_nm is not None:
        rv = subprocess.Popen([sys_nm, '--help'],
                              stdout=subprocess.PIPE).communicate()[0]
        if '-no-llvm-bc' in rv:
            return sys_nm

    raise EnvironmentError('Could not locate llvm-nm')


def chop_symbol_path(path):
    items = path.split('/')
    if items and _base_path_segment.match(items[0]):
        items = items[1:]
    if items and items[0] == 'Symbols':
        items = items[1:]
    return '/'.join(items)


class BulkExtractor(object):

    def __init__(self, nm_path=None):
        if nm_path is None:
            nm_path = find_llvm_nm()
        self.nm_path = nm_path

    def process_file(self, filename):
        arch_to_uuid = dict(get_macho_uuids(filename) or ())
        if not arch_to_uuid:
            return
        def generate():
            args = [self.nm_path, '-numeric-sort', filename]
            c = subprocess.Popen(args, stdout=subprocess.PIPE,
                                 stderr=devnull)
            try:
                arch = None
                while 1:
                    line = c.stdout.readline()
                    if not line:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    match = _arch_intro_re.match(line)
                    if match is not None:
                        arch = match.group(1)
                        continue
                    if arch is None:
                        continue
                    items = line.split(' ', 2)
                    if items[1] in 'tT':
                        yield (arch, arch_to_uuid[arch], int(items[0], 16),
                               items[2])
            finally:
                try:
                    c.kill()
                except Exception:
                    pass
        return generate()

    def process_directory(self, base, log):
        base = os.path.normpath(os.path.abspath(base))

        paths = []
        for dirpath, dirnames, filenames in os.walk(base):
            for filename in filenames:
                path = os.path.join(base, dirpath, filename)
                paths.append(path)

        with progressbar(paths, prefix=os.path.basename(base),
                         enabled=log) as bar:
            for path in bar:
                local_path = path[len(base) + 1:]
                iter = self.process_file(path)
                if iter is not None:
                    for tup in iter:
                        yield (chop_symbol_path(local_path),) + tup

    def process_archive(self, filename, log=False):
        f = zipfile.ZipFile(filename)

        prefix = os.path.basename(filename).rsplit('.', 1)[0]

        with progressbar(f.namelist(), prefix=prefix, enabled=log) as bar:
            for member in bar:
                if member.endswith('/'):
                    continue
                with tempfile.NamedTemporaryFile() as df:
                    with f.open(member) as sf:
                        shutil.copyfileobj(sf, df)
                        iter = self.process_file(df.name)
                        if iter is not None:
                            for tup in iter:
                                yield (chop_symbol_path(member),) + tup

    def build_symbol_archive(self, base, archive_file, log=False):
        f = zipfile.ZipFile(archive_file, 'w',
                            compression=zipfile.ZIP_DEFLATED)
        uuids_seen = set()
        path_index = {}

        with f:
            last_object = None
            buf = []

            def _dump_buf():
                image, arch, uuid = last_object
                if uuid not in uuids_seen:
                    uuids_seen.add(uuid)
                    data = json.dumps({
                        'arch': arch,
                        'image': image,
                        'uuid': uuid,
                        'symbols': buf,
                    }, separators=(',', ':'))
                    f.writestr(uuid, data)
                    path_info = path_index.setdefault(image, {})
                    path_info[arch] = uuid
                del buf[:]

            if os.path.isdir(base):
                iter = self.process_directory(base, log=log)
            else:
                iter = self.process_archive(base, log=log)
            for tup in iter:
                if last_object is None or last_object != tup[:3]:
                    if buf:
                        _dump_buf()
                    last_object = tup[:3]
                buf.append(tup[3:])
            if buf:
                _dump_buf()

            if path_index:
                f.writestr('path_index', json.dumps(
                    path_index, separators=(',', ':')))
