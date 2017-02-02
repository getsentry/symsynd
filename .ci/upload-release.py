#!/usr/bin/env python
import os
import sys
import urlparse
import requests

try:
    from requests.packages import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass


AUTH_USERNAME = 'getsentry-bot'
AUTH_TOKEN = os.environ['GITHUB_AUTH_TOKEN']
AUTH = (AUTH_USERNAME, AUTH_TOKEN)
TAG = os.environ.get('TRAVIS_TAG') or \
    os.environ.get('APPVEYOR_REPO_TAG_NAME') or os.environ.get('BUILD_TAG')
NAME = 'symsynd'
REPO = 'getsentry/symsynd'

if sys.platform.startswith('win'):
    EXT = '.exe'
else:
    EXT = ''


def log(message, *args):
    if args:
        message = message % args
    print >> sys.stderr, message


def api_request(method, path, **kwargs):
    url = urlparse.urljoin('https://api.github.com/', path.lstrip('/'))
    # default travis python does not have SNI
    return requests.request(method, url, auth=AUTH, verify=False, **kwargs)


def find_wheels():
    dist = os.path.join('dist')
    for filename in os.listdir(dist):
        if filename.endswith('.whl'):
            yield os.path.join(dist, fileanme)


def get_target_executable_name():
    bits = TARGET.split('-')
    platform = bits[2].title()
    arch = bits[0]
    return 'sentry-cli-%s-%s%s' % (platform, arch, EXT)


def ensure_release():
    resp = api_request('GET', 'repos/%s/releases' % REPO)
    resp.raise_for_status()
    for release in resp.json():
        if release['tag_name'] == TAG:
            log('Found already existing release %s' % release['id'])
            return release
    resp = api_request('POST', 'repos/%s/releases' % REPO, json={
        'tag_name': TAG,
        'name': '%s %s' % (NAME, TAG),
        'draft': True,
    })
    resp.raise_for_status()
    release = resp.json()
    log('Created new release %s' % release['id'])
    return release


def upload_asset(release, path, asset_info):
    asset_name = os.path.basename(path)
    for asset in asset_info:
        if asset['name'] == asset_name:
            log('Already have release asset %s. Skipping' % asset_name)
            return

    upload_url = release['upload_url'].split('{')[0]
    with open(path, 'rb') as f:
        log('Creating new release asset %s.' % asset_name)
        resp = api_request('POST', upload_url,
                           params={'name': asset_name},
                           headers={'Content-Type': 'application/octet-stream'},
                           data=f)
        resp.raise_for_status()


def upload_assets(release, wheels):
    resp = api_request('GET', release['assets_url'])
    resp.raise_for_status()
    asset_info = resp.json()
    for wheel in wheels:
        upload_asset(release, wheel, asset_info)


def main():
    if not TAG:
        return log('No tag specified.  Doing nothing.')
    wheels = list(find_wheels())
    if not wheels:
        return log('Could not locate wheels.  Doing nothing.')

    release = ensure_release()
    upload_assets(release, wheels)


if __name__ == '__main__':
    main()
