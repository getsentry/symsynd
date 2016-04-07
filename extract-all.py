import os
import sys
from symsynd.bulkextract import BulkExtractor


path = '/Volumes/DeviceSupport'


ex = BulkExtractor()
for filename in sys.argv[1:]:
    dst = os.path.basename(filename)
    if not os.path.isfile(dst):
        ex.build_symbol_archive(os.path.join(path, filename), dst,
                                log=True)
