"""Validation shared by the launcher and command-line runner."""
from pathlib import Path
from prepare import load_sfo

TITLE_ID = 'CUSA01047'
APP_VERSION = '01.00'

def validate_game(folder):
    game = Path(folder)
    for name in ('eboot.bin', 'sce_sys/param.sfo', 'sce_module/libc.prx', 'sce_module/libSceFios2.prx'):
        path = game / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing or empty game file: {name}')
    values = load_sfo(game / 'sce_sys/param.sfo')
    if values.get('TITLE_ID') != TITLE_ID or values.get('APP_VER') != APP_VERSION:
        raise ValueError('RatchetPort requires Ratchet & Clank PS4 CUSA01047 USA version 1.00.')
    return values
