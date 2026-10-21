"""Validation shared by the launcher and command-line runner."""
from pathlib import Path
import os
import struct
from prepare import load_sfo

TITLE_ID = 'CUSA01047'
APP_VERSION = '01.00'
PLAYGO_PATH = 'sce_sys/playgo-chunk.dat'


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
                         'Restore it from your original CUSA01047 USA v1.00 dump.') from error


def validate_identity(values):
    if values.get('TITLE_ID') != TITLE_ID or values.get('APP_VER') != APP_VERSION:
        raise ValueError('RatchetPort requires Ratchet & Clank PS4 CUSA01047 USA version 1.00.')
    return values


def validate_game(folder):
    game = Path(folder)
    for name in ('eboot.bin', 'sce_sys/param.sfo', 'sce_module/libc.prx',
                 'sce_module/libSceFios2.prx', PLAYGO_PATH):
        path = game / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing or empty game file: {path.resolve()}. '
                             'Restore it from your original CUSA01047 USA v1.00 dump.')
    values = validate_identity(load_sfo(game / 'sce_sys/param.sfo'))
    validate_playgo(game / PLAYGO_PATH)
    return values
