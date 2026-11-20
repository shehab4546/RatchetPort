# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded, advisory checks for gameplay voice archives (CUSA01047 USA, CUSA01073 Europe).

A sample is not a full WEM/layout verification. Never repairs files or blocks play.
"""
from pathlib import Path
import hashlib

import editions

# PS4 system language -> display name, text suffix, gameplay voice archive (USA edition).
LANGUAGES = editions.USA_LANGUAGES
BLOCK = 1024 * 1024
SAMPLES = 8


def inspect(game, language, title_id=None):
    """Sample the voice archive of `language` in the game folder's edition (from its param.sfo
    unless `title_id` is given; the USA table for unknown dumps)."""
    title_id = title_id or editions.title_of(game)
    language = editions.normalize_language(language, title_id)
    name, text, filename = editions.languages(title_id)[language]
    relative = 'asset_archive/' + filename
    result = dict(language=name, locale=filename.rsplit('.', 1)[1], archive=relative,
                  exists=False, size=0, integrity='UNKNOWN', reason='', sampled_blocks=0)
    path = Path(game) / relative
    try:
        result['exists'] = path.is_file()
        if not result['exists']:
            result.update(integrity='WARNING', reason='Archive is missing')
            return result
        size = result['size'] = path.stat().st_size
        if size < 12:
            result.update(integrity='WARNING', reason='Archive is empty or too small')
            return result
        count = size // BLOCK
        offsets = sorted({round(i * (count - 1) / (SAMPLES - 1)) * BLOCK
                          for i in range(SAMPLES)}) if count else [0]
        hashes, wave = [], False
        with path.open('rb') as stream:
            for offset in offsets:
                stream.seek(offset)
                data = stream.read(min(BLOCK, size - offset))
                if len(data) != min(BLOCK, size - offset):
                    raise OSError('Archive changed during sampling')
                hashes.append(hashlib.sha256(data).digest())
                start = 0
                while (start := data.find(b'RIFF', start)) >= 0:
                    if data[start + 8:start + 12] == b'WAVE':
                        wave = True
                        break
                    start += 4
        result['sampled_blocks'] = len(hashes)
        if count >= 8 and len(set(hashes)) == 1:
            result.update(integrity='FAILED', reason='Repeated 1 MiB blocks across archive samples')
        elif size < 1024:
            result.update(integrity='WARNING', reason='Archive is unexpectedly small')
        elif not wave:
            result.update(integrity='UNKNOWN', reason='No RIFF/WAVE header in samples; full validation required')
        else:
            result.update(integrity='OK', reason='Sample checks passed; full archive not verified')
    except OSError as error:
        result.update(integrity='WARNING', reason=f'Cannot inspect archive: {error}')
    return result


def describe(result):
    return (f"[Voice Archive]\nLanguage: {result['language']}\nSelected locale: {result['locale']}\n"
            f"Archive: {result['archive']}\nExists: {'yes' if result['exists'] else 'no'}\n"
            f"Size: {result['size']}\nIntegrity: {result['integrity']}\nReason: {result['reason']}")


def warning(result):
    if result['integrity'] in ('FAILED', 'WARNING'):
        return (f"{result['language']} voice archive: {result['archive']}\n{result['reason']}. "
                'Gameplay dialogue may be missing. Re-dump the language data from your own game. '
                'You can still start the game.')
    return result['reason']
