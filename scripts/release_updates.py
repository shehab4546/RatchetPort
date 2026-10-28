# SPDX-License-Identifier: GPL-2.0-or-later
"""Published RatchetPort releases; source archives are never executable updates."""
import json
import re
import urllib.request
from urllib.parse import urlparse

REPOSITORY = 'shehab4546/RatchetPort'
API = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
PAGE = f'https://github.com/{REPOSITORY}/releases'


def version(value):
    match = re.fullmatch(r'[vV]?(\d+(?:\.\d+){1,3})', value or '')
    if not match:
        raise ValueError('Release tag must be a version such as v1.7.1')
    parts = tuple(map(int, match[1].split('.')))
    return parts + (0,) * (4-len(parts))


def release_url(url, download=False):
    parsed = urlparse(url or '')
    prefix = f'/{REPOSITORY}/releases/' + ('download/' if download else 'tag/')
    return (parsed.scheme == 'https' and parsed.netloc == 'github.com'
            and parsed.path.startswith(prefix) and not parsed.query and not parsed.fragment)


def latest(current, opener=None):
    request = urllib.request.Request(API, headers={'User-Agent': 'RatchetPort-update-check',
        'Accept': 'application/vnd.github+json'})
    with (opener or urllib.request.urlopen)(request, timeout=12) as response:
        raw = response.read((1 << 20) + 1)
    if len(raw) > 1 << 20:
        raise ValueError('Release response exceeds the size limit')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('Invalid release response')
    if data.get('draft') or data.get('prerelease'):
        return None
    tag = data.get('tag_name', '')
    if version(tag) <= version(current):
        return None
    page = data.get('html_url', '')
    if not release_url(page):
        raise ValueError('Unexpected release page')
    candidates = [a for a in data.get('assets', []) if isinstance(a, dict)
                  and re.fullmatch(r'RatchetPort-[^/\\]+-Windows\.zip', a.get('name', ''), re.I)
                  and a.get('state') == 'uploaded' and release_url(a.get('browser_download_url'), True)]
    url, digest = '', ''
    if len(candidates) == 1:
        asset = candidates[0]
        if re.fullmatch(r'sha256:[0-9a-fA-F]{64}', asset.get('digest') or ''):
            url, digest = asset['browser_download_url'], asset['digest'][7:].lower()
    return tag, url, page, digest


def safe_members(package):
    total, names = 0, set()
    for entry in package.infolist():
        name = entry.filename.replace('\\', '/')
        parts = name.rstrip('/').split('/')
        if (not all(parts) or any(p in ('.', '..') or ':' in p or p.endswith((' ', '.')) for p in parts)
                or any(re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', p, re.I) for p in parts)
                or (entry.external_attr >> 16) & 0o170000 == 0o120000
                or name.casefold() in names):
            raise ValueError('Unsafe path in update archive')
        names.add(name.casefold())
        total += entry.file_size
        if total > 12 << 30 or len(names) > 50000:
            raise ValueError('Update archive exceeds extraction limits')
    return package.infolist()
