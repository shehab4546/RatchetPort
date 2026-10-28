# SPDX-License-Identifier: GPL-2.0-or-later
"""Mapping rules shared by the launcher and direct launches."""
from glyph_mapping import KEY_DEFAULTS as RUNTIME_KEYS, STICK_DEFAULTS, canonical_key, apply

KEY_DEFAULTS = dict(cross='Space', circle='F', square='E', triangle='Q',
                    l1='Left Ctrl', r1='Left Shift', l2='Mouse Right', r2='Mouse Left',
                    l3='Z', r3='C', options='Escape', touchpad_left='Tab',
                    touchpad_right='Backspace', up='1', right='2', down='3', left='4')
LEGACY_KEYS = dict(cross='Space', circle='Left Shift', square='Mouse Left', triangle='Mouse Right',
                   l1='Q', r1='E', l2='R', r2='Mouse Forward', l3='Z', r3='X',
                   options='Tab', touchpad_left='P', touchpad_right='Escape',
                   up='1', right='2', down='3', left='4')
STICK_PRESETS = {'WASD': ('A', 'D', 'W', 'S'),
                 'Arrow keys': ('Left', 'Right', 'Up', 'Down'),
                 'Mouse movement': ('Mouse Move Left', 'Mouse Move Right', 'Mouse Move Up', 'Mouse Move Down'),
                 'None': ('None',) * 4}
SUFFIXES = ('x_neg', 'x_pos', 'y_neg', 'y_pos')


def stick_preset(values, side):
    current = tuple(values.get(side+s, STICK_DEFAULTS[side+s]).casefold() for s in SUFFIXES)
    return next((name for name, sources in STICK_PRESETS.items()
                 if current == tuple(v.casefold() for v in sources)), 'Custom (saved)')


def validate_sources(primary, secondary, sticks):
    """Assignments remain unchanged until save/launch checks all conflicts."""
    used, errors = {}, []
    for title, mapping in (('Primary', primary), ('Secondary', secondary), ('Stick', sticks)):
        for button, source in mapping.items():
            key = canonical_key(source) if isinstance(source, str) else None
            label = f'{button} ({title})'
            if key is None:
                errors.append(f'{label}: unsupported input {source!r}')
                continue
            key = key.casefold()
            if key == 'none':
                continue
            if title != 'Stick' and key.startswith('mouse move '):
                errors.append(f'{label}: mouse movement belongs to a stick')
            if key in used:
                errors.append(f'{source}: {used[key]} / {label}')
            else:
                used[key] = label
    if errors:
        raise ValueError('Resolve these control assignments before saving or starting:\n' + '\n'.join(errors))


def validate_environment(env):
    for name, allowed in (('RATCHET_KEY_MAP', RUNTIME_KEYS), ('RATCHET_KEY_MAP_ALT', RUNTIME_KEYS),
                          ('RATCHET_STICK_KEYS', STICK_DEFAULTS)):
        value = env.get(name, '')
        if len(value.encode('utf-8')) > 1023:
            raise ValueError(f'{name} exceeds the input mapping limit')
        seen = set()
        for entry in value.split(','):
            if not entry.strip():
                continue
            button, sep, source = entry.partition('=')
            button = button.strip().lower()
            if button == 'touchpad':
                button = 'touchpad_left'
            if not sep or button not in allowed or button in seen or canonical_key(source) is None:
                raise ValueError(f'Invalid {name} entry: {entry}')
            seen.add(button)
    validate_sources(apply(RUNTIME_KEYS, env.get('RATCHET_KEY_MAP', '')),
                     apply(dict.fromkeys(RUNTIME_KEYS, 'None'), env.get('RATCHET_KEY_MAP_ALT', '')),
                     apply(STICK_DEFAULTS, env.get('RATCHET_STICK_KEYS', '')))
