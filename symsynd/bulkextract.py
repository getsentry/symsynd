import os
import re
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess

from symsynd.utils import which, progressbar
from symsynd.macho.arch import get_macho_image_info
from symsynd.macho.util import is_macho_file
from symsynd.driver import devnull


_base_path_segment = re.compile(r'^(\d+)\.(\d+)(?:\.(\d+))? \(([a-zA-Z0-9]+)\)$')


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
    return '/' + '/'.join(items).strip('/')


def get_sdk_info_from_path(path):
    pieces = path.split('/')[::-1]
    for piece in pieces:
        if piece.endswith('.zip'):
            piece = piece[:-4]
        match = _base_path_segment.match(piece)
        if match is not None:
            tup = match.groups()
            return {
                'version_major': int(tup[0]),
                'version_minor': int(tup[1]),
                'version_patchlevel': int(tup[2] or 0),
                'version_build': tup[3],
            }


def parse_nm_line(line):
    line = line.rstrip()
    # This is a line without location, just skip it
    if not line or line[:1] == ' ':
        return
    return line.split(' ', 2)


class BulkExtractor(object):

    def __init__(self, nm_path=None):
        if nm_path is None:
            nm_path = find_llvm_nm()
        self.nm_path = nm_path

    def process_file(self, filename):
        if not is_macho_file(filename):
            return

        images = dict((x['cpu_name'], x) for x in get_macho_image_info(filename))

        def generate():
            for arch, info in images.iteritems():
                args = [self.nm_path, '-numeric-sort', filename,
                        '-arch', arch]
                c = subprocess.Popen(args, stdout=subprocess.PIPE,
                                     stderr=devnull)
                try:
                    while 1:
                        line = c.stdout.readline()
                        if not line:
                            break
                        items = parse_nm_line(line)
                        if items is None:
                            continue
                        if items[1] in 'tT':
                            symbol = items[2]
                            # Chop off leading underscore from symbols if
                            # it's there.
                            if symbol[:1] == '_':
                                symbol = symbol[1:]
                            yield arch, info, int(items[0], 16), symbol
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
        _archive = []

        sdk_info = get_sdk_info_from_path(
            os.path.normpath(os.path.abspath(base)))
        if sdk_info is None:
            raise RuntimeError('Could not parse SDK info from path')

        def _get_archive():
            if _archive:
                return _archive[0]
            f = zipfile.ZipFile(archive_file, 'w',
                                compression=zipfile.ZIP_DEFLATED)
            _archive.append(f)
            return f

        uuids_seen = set()
        path_index = {}

        last_object = None
        buf = []

        try:
            def _dump_buf():
                image, arch, info = last_object
                if info['uuid'] not in uuids_seen:
                    uuids_seen.add(info['uuid'])
                    data = json.dumps({
                        'arch': arch,
                        'image': image,
                        'uuid': info['uuid'],
                        'vmaddr': info.get('vmaddr'),
                        'vmsize': info.get('vmsize'),
                        'symbols': buf,
                    }, separators=(',', ':'))
                    _get_archive().writestr(info['uuid'], data)
                    path_info = path_index.setdefault(image, {})
                    path_info[arch] = info['uuid']
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
                _get_archive().writestr('path_index', json.dumps(
                    path_index, separators=(',', ':')))
                _get_archive().writestr('sdk_info', json.dumps(
                    sdk_info, separators=(',', ':')))
        finally:
            if _archive:
                _archive[0].close()
