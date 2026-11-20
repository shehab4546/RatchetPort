# SPDX-License-Identifier: GPL-2.0-or-later
"""Supported game editions: the single source of per-edition facts.

Both are Ratchet & Clank PS4 application version 01.00 dumps made from the player's own copy.
CUSA01047 (USA) is the reviewed baseline; every USA value below is unchanged from the original
port. CUSA01073 (Europe) is a later build of the same game (SDK 4.0, PS4 Pro aware) whose
differences are documented in docs/EUROPE_EDITION.md. Only facts live here: no game bytes.
"""
from pathlib import Path

USA = 'CUSA01047'
EUROPE = 'CUSA01073'
APP_VERSION = '01.00'

# PS4 system language ID -> (display name, text locale, gameplay voice archive).
USA_LANGUAGES = {
    '1': ('English US', 'us', 'a00s003.us'),
    '2': ('French', 'fr', 'a00s007.fr'),
    '7': ('Portuguese Portugal', 'pt', 'a00s013.pt'),
    '20': ('Spanish LATAM', 'la', 'a00s017.mx'),
    '17': ('Portuguese Brazil', 'br', 'a00s018.br'),
}
# The European dump's asset_archive/a00sNNN.<locale> voice archives. Voices follow the text.
EUROPE_LANGUAGES = {
    '3': ('Spanish Spain', 'es', 'a00s015.es'),
    '1': ('English US', 'us', 'a00s003.us'),
    '18': ('English UK', 'us', 'a00s003.us'),
    '2': ('French', 'fr', 'a00s007.fr'),
    '4': ('German', 'de', 'a00s008.de'),
    '5': ('Italian', 'it', 'a00s009.it'),
    '6': ('Dutch', 'nl', 'a00s005.nl'),
    '7': ('Portuguese Portugal', 'pt', 'a00s013.pt'),
    '8': ('Russian', 'ru', 'a00s014.ru'),
    '16': ('Polish', 'pl', 'a00s012.pl'),
    '12': ('Finnish', 'fi', 'a00s006.fi'),
    '13': ('Swedish', 'se', 'a00s016.se'),
    '14': ('Danish', 'dk', 'a00s004.dk'),
    '15': ('Norwegian', 'no', 'a00s011.no'),
    '19': ('Turkish', 'tr', 'a00s020.tr'),
    '21': ('Arabic', 'ar', 'a00s019.ar'),
}

EDITIONS = {
    USA: {
        'name': 'USA',
        'source_sha256': 'fdf72d683f305ab1a70adfe246e9ac1dbbd4ceb988b1327157b6bda55476697d',
        'elf_sha256': 'dc1a8862016cb80060928e911ab933d6e380014c1128e537642f9f569f3a05cf',
        'languages': USA_LANGUAGES,
        'language_aliases': {'22': '2'},   # French under NA: same content as 2
        'text_split': True,                # USA-only text/voice separation (language_split.py)
        'compat': None,                    # runs as reviewed, nothing added at link time
    },
    EUROPE: {
        'name': 'Europe',
        'source_sha256': '0aeafa5fb7f511b2e0dfb1feef37dff60ce66cb322c6db9a63ee4ba8942f7362',
        'elf_sha256': 'a12d10e22b3ddbb869ad6e0995661de283fc1db143c435c4d5c665cde55d3fad',
        'languages': EUROPE_LANGUAGES,
        'language_aliases': {},
        'text_split': False,
        'compat': 'europe',                # edition_compat.EUROPE: link-time compatibility fixes
    },
}


def default_game_dir(base):
    """The game folder used when none is configured: base/CUSA01047 or base/CUSA01073, whichever
    holds an eboot.bin (USA first), else base/CUSA01047. Keeps a portable copy working anywhere."""
    for title in EDITIONS:
        if (Path(base) / title / 'eboot.bin').is_file():
            return Path(base) / title
    return Path(base) / USA


def edition(title_id):
    """The edition record of a TITLE_ID, or None."""
    return EDITIONS.get(title_id)


def title_of(game):
    """TITLE_ID of a game folder from its param.sfo, or None when unreadable."""
    try:
        from prepare import load_sfo
        return load_sfo(Path(game) / 'sce_sys/param.sfo').get('TITLE_ID')
    except (OSError, ValueError, TypeError):
        return None


def languages(title_id=USA):
    """System language ID -> (name, text locale, voice archive) of an edition (USA when unknown)."""
    return (EDITIONS.get(title_id) or EDITIONS[USA])['languages']


def normalize_language(value, title_id=USA):
    """The edition's own system language ID for a saved value; unknown values become English (1)."""
    record = EDITIONS.get(title_id) or EDITIONS[USA]
    value = str(value)
    value = record['language_aliases'].get(value, value)
    return value if value in record['languages'] else '1'
