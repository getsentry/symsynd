import os
import bisect

from symsynd.libdebug import get_cpu_name, DebugInfo
from symsynd.exceptions import DebugInfoError
from symsynd.utils import timedsection, parse_addr
from symsynd._compat import string_types


def get_image_cpu_name(image):
    cpu_name = image.get('cpu_name')
    if cpu_name is not None:
        return cpu_name
    return get_cpu_name(image['cpu_type'], image['cpu_subtype'])


def find_debug_images(dsym_paths, binary_images):
    """Given a list of paths and a list of binary images this returns a
    dictionary of image addresses to the locations on the file system for
    all found images.
    """
    images_to_load = set()

    with timedsection('iterimages0'):
        for image in binary_images:
            if get_image_cpu_name(image) is not None:
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
                        try:
                            di = DebugInfo.open_path(full_fn)
                        except DebugInfoError:
                            continue
                        uuids = get_macho_uuids(full_fn)
                        for variant in di.get_variants():
                            uuid = str(variant.uuid)
                            if uuid in images_to_load:
                                images[uuid] = full_fn
                                images_to_load.discard(uuid)

    rv = {}

    # Now resolve all the images.
    with timedsection('resolveimages'):
        for image in binary_images:
            cpu_name = get_image_cpu_name(image)
            if cpu_name is None:
                continue
            uid = image['uuid'].lower()
            if uid not in images:
                continue
            rv[parse_addr(image['image_addr'])] = images[uid]

    return rv


class ImageLookup(object):
    """Helper object to locate images."""

    def __init__(self, images):
        self._image_addresses = []
        self.images = {}
        for img in images:
            img_addr = parse_addr(img['image_addr'])
            self._image_addresses.append(img_addr)
            self.images[img_addr] = img
        self._image_addresses.sort()

    def iter_images(self):
        return six.itervalues(self.images)

    def get_uuids(self):
        return list(self.iter_uuids())

    def iter_uuids(self):
        for img in self.iter_images():
            yield img['uuid']

    def find_image(self, addr):
        """Given an instruction address this locates the image this address
        is contained in.
        """
        idx = bisect.bisect_left(self._image_addresses, parse_addr(addr))
        if idx > 0:
            return self.images[self._image_addresses[idx - 1]]
