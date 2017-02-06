#!/usr/bin/env python
import os
import sys
import json
import requests


resp = requests.get('https://api.github.com/repos/getsentry/symsynd/releases/tags/%s' % sys.argv[1]).json()
for asset in resp['assets']:
    print 'Downloading', asset['name']
    src = requests.get(asset['browser_download_url'], stream=True)
    with open(os.path.join('dist', asset['name']), 'wb') as dst:
        for chunk in src.iter_content(chunk_size=1 << 16):
            dst.write(chunk)
