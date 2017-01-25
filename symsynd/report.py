import os

from symsynd.macho.arch import get_cpu_name, get_macho_uuids
from symsynd.utils import timedsection
from symsynd._compat import string_types


def find_debug_images(dsym_paths, binary_images):
    images_to_load = set()

    with timedsection('iterimages0'):
        for image in binary_images:
            cpu_name = get_cpu_name(image['cpu_type'],
                                    image['cpu_subtype'])
            if cpu_name is not None:
                images_to_load.add(image['uuid'].lower())

    images = {}

    # Step one: load images that are named by their UUID
    with timedsection('loadimages-fast'):
        for uuid in list(images_to_load):
            for dsym_path in dsym_paths:
                fn = os.path.join(dsym_path, uuid)
                if os.path.isfile(fn):
                    images[uuid] = fn
                    images_to_load.discard(uuid)
                    break

    # Otherwise fall back to loading images from the dsym bundle.  Because
    # this loading strategy is pretty slow we do't actually want to use it
    # unless we have a path that looks like a bundle.  As a result we
    # find all the paths which are bundles and then only process those.
    if images_to_load:
        slow_paths = []
        for dsym_path in dsym_paths:
            if os.path.isdir(os.path.join(dsym_path, 'Contents')):
                slow_paths.append(dsym_path)

        with timedsection('loadimages-slow'):
            for dsym_path in slow_paths:
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
    with timedsection('resolveimages'):
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
        with timedsection('findimages'):
            self.images = find_debug_images(dsym_paths, binary_images)

    def symbolize_frame(self, frame, silent=True, demangle=True,
                        symbolize_inlined=False, meta=None):
        img_addr = frame.get('object_addr') or frame.get('image_addr')
        img = self.images.get(img_addr)
        if img is None:
            if symbolize_inlined:
                return []
            return

        rv = self.driver.symbolize(
            img['dsym_path'], img['image_vmaddr'],
            img['image_addr'], frame['instruction_addr'],
            img['cpu_name'], silent=silent,
            demangle=demangle, symbolize_inlined=symbolize_inlined,
            meta=meta)

        if not symbolize_inlined:
            if rv['symbol_name'] is None:
                return
            return dict(frame, **rv)

        sym_rv = []
        for frame_rv in rv:
            if frame_rv['symbol_name'] is not None:
                sym_rv.append(dict(frame, **frame_rv))
            else:
                sym_rv.append(dict(frame))

        return sym_rv

    def symbolize_backtrace(self, backtrace, demangle=True, meta=None,
                            symbolize_inlined=False):
        rv = []
        meta = dict(meta or {}, frame_number=None)
        for idx, frame in enumerate(backtrace):
            meta['frame_number'] = idx
            symrv = self.symbolize_frame(frame, demangle=demangle,
                                         symbolize_inlined=symbolize_inlined,
                                         meta=meta)
            if symbolize_inlined:
                if symrv:
                    rv.extend(symrv)
                    continue
            else:
                if symrv is not None:
                    rv.append(symrv)
                    continue
            rv.append(frame)
        return rv
