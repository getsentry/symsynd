import os
import sys
from symsynd.bulkextract import BulkExtractor


ex = BulkExtractor()
for filename in sys.argv[1:]:
    dst = os.path.basename(filename)
    if not os.path.isfile(dst):
        ex.build_symbol_archive(filename, dst, sdk='iOS', log=True)
