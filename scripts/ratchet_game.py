"""Validation shared by the launcher and command-line runner."""
from pathlib import Path
import os
import struct
import hashlib
from prepare import load_sfo

TITLE_ID = 'CUSA01047'
APP_VERSION = '01.00'
PLAYGO_PATH = 'sce_sys/playgo-chunk.dat'
BUILD_FINGERPRINTS = {
    ('CUSA01047', '01.00'): (
        'fdf72d683f305ab1a70adfe246e9ac1dbbd4ceb988b1327157b6bda55476697d',
        'dc1a8862016cb80060928e911ab933d6e380014c1128e537642f9f569f3a05cf'),
    ('CUSA01047', '01.09'): (
        'd0bbf7a28ff633bf8f80379c00bd12209611cfcafcaaa39598263f34c366113b',
        '4deebb465b6635b351a301b64841062d3986122a99cc4ffc4f92c1b9aea53bb5'),
}
UPDATE_ARCHIVES = tuple(f'asset_archive/p{i:06d}' for i in range(35, 49))
UPDATE_TOC_SHA256 = '5fdfb07df834d6be96435a39dcb92b03fdcff128bc518de9cce31f8bb1aad654'


def playgo_header_chunks(header, file_size):
    """Validate the 256-byte PlaygoHeader and all section bounds before using its count.

    Layout/count limits: shadPS4 src/core/file_format/playgo_chunk.h. This validates
    the metadata needed by our installed-dump model, not the game payload itself.
    Keep these checks in sync with src/playgo_metadata.h.
    """
    if len(header) != 256 or file_size < 256:
        raise ValueError('truncated header')
    u16 = lambda offset: struct.unpack_from('<H', header, offset)[0]
    u32 = lambda offset: struct.unpack_from('<I', header, offset)[0]
    if u32(0) != 0x6F676C70 or u32(16) != file_size:
        raise ValueError('bad magic or file size')
    chunks, mchunks, scenarios = u16(10), u16(12), u16(14)
    if not 1 <= chunks <= 1000 or mchunks > 8000 or scenarios > 32 or (
            scenarios and u16(20) >= scenarios):
        raise ValueError('invalid counts or default scenario')
    sections = [struct.unpack_from('<II', header, 192 + 8 * i) for i in range(8)]
    for i, (offset, length) in enumerate(sections):
        if offset > file_size or length > file_size - offset or (length and offset < 256):
            raise ValueError('section outside file')
        for previous, size in sections[:i]:
            if length and size and offset < previous + size and previous < offset + length:
                raise ValueError('overlapping sections')
    lengths = [length for _, length in sections]
    if (lengths[0] < chunks * 32 or lengths[0] % 32 or lengths[1] % 2 or
            lengths[3] < mchunks * 16 or lengths[3] % 16 or
            lengths[4] < scenarios * 32 or lengths[4] % 32 or
            lengths[5] % 2 or lengths[7] % 16):
        raise ValueError('truncated or misaligned tables')
    return chunks


def validate_playgo(path):
    path = Path(path)
    try:
        with path.open('rb') as stream:
            return playgo_header_chunks(stream.read(256), os.fstat(stream.fileno()).st_size)
    except ValueError as error:
        raise ValueError(f'Invalid required PlayGo metadata: {path.resolve()} ({error}). '
                         'Restore it from the matching game version.') from error


def validate_identity(values):
    identity = values.get('TITLE_ID'), values.get('APP_VER')
    if identity not in BUILD_FINGERPRINTS:
        raise ValueError(f'Unreviewed game version: {identity[0]} / {identity[1]}. '
                         'Supported profiles: CUSA01047 USA 1.00 and experimental 1.09.')
    return values


def require_files(game, names):
    for name in names:
        path = game / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing or empty game file: {path.resolve()}. '
                             'Restore it from the matching game version.')


def verify_update(game, values):
    """Metadata alone must never authorize an update executable or its patch profile."""
    if values['APP_VER'] == '01.00':
        return  # Preserve the original unpatched 1.00 launch policy.
    path = game / 'eboot.bin'
    if path.stat().st_size > 512 * 1024 * 1024:
        raise ValueError('Update executable exceeds the 512 MiB limit')
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    expected = BUILD_FINGERPRINTS[(values['TITLE_ID'], values['APP_VER'])][0]
    if actual != expected:
        raise ValueError('Update executable fingerprint does not match CUSA01047 USA 1.09. '
                         'Restore the original update; changing APP_VER does not convert a build.')
    require_files(game, ('asset_archive/toc', *UPDATE_ARCHIVES))
    toc = game / 'asset_archive/toc'
    if toc.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Update TOC exceeds the 32 MiB limit')
    with toc.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != UPDATE_TOC_SHA256:
            raise ValueError('Update TOC fingerprint does not match CUSA01047 USA 1.09. '
                             'Keep the update executable and asset_archive/toc from the same update.')


def validate_game(folder):
    game = Path(folder)
    require_files(game, ('eboot.bin', 'sce_sys/param.sfo', 'sce_module/libc.prx',
                        'sce_module/libSceFios2.prx', PLAYGO_PATH))
    values = validate_identity(load_sfo(game / 'sce_sys/param.sfo'))
    validate_playgo(game / PLAYGO_PATH)
    verify_update(game, values)
    if values['APP_VER'] != '01.00':
        require_files(game, ('asset_archive/g00s000',))
    return values


def validate_selection(base, update=''):
    """Accept a complete installation, or base 1.00 plus its separate reviewed update."""
    values = validate_game(base)
    if not update:
        return values
    base, update = Path(base).resolve(), Path(update).resolve()
    if base == update or base in update.parents or update in base.parents:
        raise ValueError('Choose two separate folders for the game and its update')
    require_files(update, ('eboot.bin', 'sce_sys/param.sfo', PLAYGO_PATH,
                           'sce_module/libc.prx', 'sce_module/libSceFios2.prx'))
    updated = validate_identity(load_sfo(update / 'sce_sys/param.sfo'))
    if (values['APP_VER'] != '01.00' or updated['APP_VER'] != '01.09' or
            values['TITLE_ID'] != updated['TITLE_ID'] or updated.get('CATEGORY') != 'gp'):
        raise ValueError('Select CUSA01047 USA base 1.00 and its matching 1.09 update')
    require_files(base, ('asset_archive/g00s000',))
    validate_playgo(update / PLAYGO_PATH)
    verify_update(update, updated)
    return updated
