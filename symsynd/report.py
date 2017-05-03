import os
import bisect

from symsynd.macho.arch import get_cpu_name, get_macho_uuids
from symsynd.utils import timedsection, parse_addr
from symsynd.exceptions import SymbolicationError
from symsynd._compat import string_types


def get_image_cpu_name(image):
    cpu_name = image.get('cpu_name')
    if cpu_name is not None:
        return cpu_name
    return get_cpu_name(image['cpu_type'], image['cpu_subtype'])


def find_debug_images(dsym_paths, binary_images):
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
                        uuids = get_macho_uuids(full_fn)
                        for _, uuid in uuids:
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
            rv[parse_addr(image['image_addr'])] = {
                'uuid': uid,
                'image_addr': image['image_addr'],
                'dsym_path': images[uid],
                'image_vmaddr': image.get('image_vmaddr') or 0,
                'cpu_name': cpu_name,
            }

    return rv


class ReportSymbolizer(object):
    """A report symbolizer can symbolize apple style crash reports.  For
    information on some of the parameters also make sure to refer to the
    underlying `Driver` which needs to be passed in.

    `dsym_paths` is a list of paths where dsym files can be found on the
    file system.  `binary_images` is a list of binary images.  The
    images need to be given as dictionaries with the following keys:
    ``uuid``, ``image_addr``, ``dsym_path``, ``image_vmaddr`` (can be left
    out), ``cpu_type``, ``cpu_subtype`` (alternatively ``cpu_name`` is
    also accepted).
    """

    def __init__(self, driver, dsym_paths, binary_images):
        if isinstance(dsym_paths, string_types):
            dsym_paths = [dsym_paths]
        self.driver = driver
        with timedsection('findimages'):
            self.images = find_debug_images(dsym_paths, binary_images)

        # This mapping is the mapping that the report symbolizer actually
        # uses.  The `images` mapping is primarily for extenral consumers
        # that want to see what images exist in the symbolizer.
        self._image_addresses = list(self.images)
        self._image_addresses.sort()

        # This should always succeed but you never quite know.
        self.cpu_name = None
        for img in self.images.itervalues():
            cpu_name = img['cpu_name']
            if self.cpu_name is None:
                self.cpu_name = cpu_name
            elif self.cpu_name != cpu_name:
                self.cpu_name = None
                break

    def find_image(self, addr):
        """Given an instruction address this locates the image this address
        is contained in.
        """
        idx = bisect.bisect_left(self._image_addresses, parse_addr(addr))
        if idx > 0:
            return self.images[self._image_addresses[idx - 1]]

    def symbolize_frame(self, frame, symbolize_inlined=False):
        """Symbolizes a frame in the context of the report data.  For
        more information see the `Driver.symbolize` method.
        """
        cpu_name = frame.get('cpu_name') or (
            meta and meta.get('cpu_name')) or self.cpu_name

        if cpu_name is None:
            raise SymbolicationError('The CPU name was not provided')

        instruction_addr = parse_addr(frame['instruction_addr'])

        img = self.find_image(instruction_addr)
        if img is not None:
            return self.driver.symbolize(
                img['dsym_path'], img['image_vmaddr'],
                img['image_addr'], instruction_addr,
                cpu_name, symbolize_inlined=symbolize_inlined)

        # Default return value for missing matches
        if symbolize_inlined:
            return []
