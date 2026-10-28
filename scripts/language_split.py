# SPDX-License-Identifier: GPL-2.0-or-later
"""CUSA01047 v1.00: route only localization_all to a separate text language.

The rest of the game's resources use the selected voice/system language. The compact
lookup preserves the original sorted-index search and ABI, without a code cave.
"""
# Assembly source for TEMPLATE is docs/evidence/language-lookup.S.
# The injected mov edx immediate is at byte 16; only localization_all is redirected.
TEXT_IDS = {'1': 1, '2': 6, '7': 13, '17': 18, '20': 21, '22': 6}
GROUPS = {key: f'Ratchet Text Language {key} (experimental)' for key in TEXT_IDS if key != '22'}
ORIGINAL = '55 48 89 e5 41 56 53 48 89 f0 48 89 fb 89 c9 48 63 d2 48 8d 34 52 48 c1 e6 04 48 03 33 8b 54 ce 04 44 8b 34 ce 4a 8d 3c f5 00 00 00 00 48 03 7b 08 be 08 00 00 00 48 89 c1 e8 92 12 62 ff 48 89 c1 31 c0 48 83 f9 ff 74 0f 4c 01 f1 48 8d 04 49 48 c1 e0 02 48 03 43 18 5b 41 5e 5d c3'
TEMPLATE = bytes.fromhex('48 b8 de f8 1b 17 4f d9 55 be 48 39 c6 75 05 ba 15 00 00 00 6b d2 30 89 c9 48 8d 14 ca 48 03 17 44 8b 02 44 8b 52 04 45 01 c2 4c 8b 4f 08 45 39 d0 73 26 43 8d 04 10 d1 e8 49 39 34 c1 74 0d 72 05 41 89 c2 eb e8 44 8d 40 01 eb e2 48 8d 04 40 48 8b 57 18 48 8d 04 82 c3 31 c0 c3 90')


def normalize(value):
    value = str(value)
    return '2' if value == '22' else value if value in GROUPS else '1'


def writes(value):
    replacement = bytearray(TEMPLATE)
    replacement[16:20] = TEXT_IDS[normalize(value)].to_bytes(4, 'little')
    return [{'signature': ORIGINAL, 'offset': 0, 'elf_vaddr': 0x1889d70,
             'original_hex': ORIGINAL, 'replacement_hex': replacement.hex(' ')}]


PATCH_GROUPS = {name: {'writes': writes(value)} for value, name in GROUPS.items()}


def requested_groups(text, voice, other=()):
    names = [name for name in other if name not in GROUPS.values()]
    text, voice = normalize(text), normalize(voice)
    return names + ([GROUPS[text]] if text != voice else [])


def launch_environment(text, voice, report):
    text, voice = normalize(text), normalize(voice)
    prepared = text != voice and GROUPS[text] in report.get('prepared', [])
    # A rejected override falls back to matching text/voice, keeping the chosen text readable.
    return {'RATCHET_LANGUAGE': voice if prepared else text,
            'RATCHET_LANGUAGE_SPLIT': '1' if prepared else '0'}
