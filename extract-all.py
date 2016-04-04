import os
from symsynd.bulkextract import BulkExtractor


path = '/Volumes/DeviceSupport'
output = 'symbols'

try:
    os.makedirs(output)
except OSError:
    pass


ex = BulkExtractor()
for filename in os.listdir(path):
    if not filename.endswith('.zip'):
        continue
    dst = os.path.join(output, filename)
    if os.path.isfile(dst):
        continue
    ex.build_symbol_archive(os.path.join(path, filename), dst,
                            log=True)
