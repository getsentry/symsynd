import os

from symsynd.macho.arch import get_cpu_name, get_macho_uuids
from symsynd._compat import string_types, int_types
from contextlib import contextmanager
from itertools import chain


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


def find_debug_images(dsym_paths, binary_images):
    images_to_load = set()

    for image in binary_images:
        cpu_name = get_cpu_name(image['cpu_type'],
                                image['cpu_subtype'])
        if cpu_name is not None:
            images_to_load.add(image['uuid'].lower())

    images = {}

    # Step one: load images that are named by their UUID
    for uuid in list(images_to_load):
        for dsym_path in dsym_paths:
            fn = os.path.join(dsym_path, uuid)
            if os.path.isfile(fn):
                images[uuid] = fn
                images_to_load.discard(uuid)
                break

    # Otherwise fall back to loading images from the dsym bundle.
    if images_to_load:
        for dsym_path in dsym_paths:
            dwarf_base = os.path.join(dsym_path, 'Contents',
                                      'Resources', 'DWARF')
            if os.path.isdir(dwarf_base):
                for fn in os.listdir(dwarf_base):
                    # Looks like a UUID we loaded, skip it
                    if fn in images:
                        continue
                    full_fn = os.path.join(dwarf_base, fn)
                    uuids = get_macho_uuids(full_fn)
                    for _, uuid in uuids:
                        if uuid in images_to_load:
                            images[uuid] = full_fn
                            images_to_load.discard(uuid)

    rv = {}

    # Now resolve all the images.
    for image in binary_images:
        cpu_name = get_cpu_name(image['cpu_type'],
                                image['cpu_subtype'])
        if cpu_name is None:
            continue
        uid = image['uuid'].lower()
        if uid not in images:
            continue
        rv[image['image_addr']] = {
            'uuid': uid,
            'image_addr': image['image_addr'],
            'dsym_path': images[uid],
            'image_vmaddr': image['image_vmaddr'],
            'cpu_name': cpu_name,
        }

    return rv


class ReportSymbolizer(object):

    def __init__(self, driver, dsym_paths, binary_images):
        if isinstance(dsym_paths, string_types):
            dsym_paths = [dsym_paths]
        self.driver = driver
        self.images = find_debug_images(dsym_paths, binary_images)

    def symbolize_frame(self, frame, silent=True):
        img = self.images.get(frame['object_addr'])
        if img is not None:
            rv = self.driver.symbolize(
                img['dsym_path'], img['image_vmaddr'],
                img['image_addr'], frame['instruction_addr'],
                img['cpu_name'], img['uuid'], silent=silent)

            # Only return this if we found the symbol
            if rv['symbol_name'] is not None:
                frame = dict(frame)
                frame.update(rv)
                return frame

    def symbolize_backtrace(self, backtrace):
        rv = []
        for frame in backtrace:
            new_frame = self.symbolize_frame(frame)
            rv.append(new_frame or frame)
        return rv
