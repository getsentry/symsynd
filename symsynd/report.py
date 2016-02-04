import os

from symsynd.mach import get_cpu_name, get_macho_uuids


def find_debug_images(dsym_path, binary_images):
    base = os.path.join(dsym_path, 'Contents', 'Resources', 'DWARF')

    images_to_load = set()

    for image in binary_images:
        cpu_name = get_cpu_name(image['cpu_type'],
                                image['cpu_subtype'])
        if cpu_name is not None:
            images_to_load.add(image['uuid'].lower())

    images = {}

    # Step one: load images that are named by their UUID
    for uuid in list(images_to_load):
        fn = os.path.join(base, uuid)
        if os.path.isfile(fn):
            images[uuid] = fn
            images_to_load.discard(uuid)

    # Otherwise fall back to loading images from the dsym bundle.
    if images_to_load:
        for fn in os.listdir(base):
            # Looks like a UUID we loaded, skip it
            if fn in images:
                continue
            full_fn = os.path.join(base, fn)
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

    def __init__(self, driver, dsym_path, binary_images):
        self.driver = driver
        self.images = find_debug_images(dsym_path, binary_images)

    def symbolize_backtrace(self, backtrace):
        rv = []
        for frame in backtrace:
            frame = dict(frame)
            img = self.images.get(frame['object_addr'])
            if img is not None:
                frame.update(self.driver.symbolize(
                    img['dsym_path'], img['image_vmaddr'],
                    img['image_addr'], frame['instruction_addr'],
                    img['cpu_name']))
            rv.append(frame)
        return rv
