# SPDX-License-Identifier: GPL-2.0-or-later
"""Logical prompt resolver. No input events or runtime maps are modified."""
import re
from glyph_keys import SDL_KEYS

KEY_DEFAULTS = dict(cross='Space', circle='Left Shift', square='E', triangle='Q',
                    l1='1', r1='3', l2='R', r2='F', l3='Z', r3='C',
                    options='Return', touchpad_left='Tab', touchpad_right='Backspace',
                    up='I', down='K', left='J', right='L')
STICK_DEFAULTS = dict(lx_neg='A', lx_pos='D', ly_neg='W', ly_pos='S',
                      rx_neg='Mouse Move Left', rx_pos='Mouse Move Right',
                      ry_neg='Mouse Move Up', ry_pos='Mouse Move Down')
PAD_DEFAULTS = dict(cross='a', circle='b', square='x', triangle='y',
                    l1='leftshoulder', r1='rightshoulder', l3='leftstick', r3='rightstick',
                    options='start', touchpad_right='back',
                    up='dpup', down='dpdown', left='dpleft', right='dpright')
PAD_LABELS = dict(a='A', b='B', x='X', y='Y', leftshoulder='LB', rightshoulder='RB',
                  leftstick='LS', rightstick='RS', start='MENU', back='VIEW',
                  dpup='UP', dpdown='DOWN', dpleft='LEFT', dpright='RIGHT',
                  guide='GUIDE', touchpad='TOUCH', misc1='SHARE',
                  paddle1='P1', paddle2='P2', paddle3='P3', paddle4='P4',
                  misc2='M2', misc3='M3', misc4='M4', misc5='M5', misc6='M6')
MOUSE = ('Mouse Left', 'Mouse Right', 'Mouse Middle', 'Mouse Back', 'Mouse Forward',
         'Wheel Up', 'Wheel Down', 'Mouse Move Left', 'Mouse Move Right', 'Mouse Move Up', 'Mouse Move Down')
SPECIAL = {'space': 'SPACE', 'return': 'ENTER', 'escape': 'ESC', 'backspace': 'BKSP',
           'tab': 'TAB', 'left shift': 'SHIFT', 'right shift': 'R SHF',
           'left ctrl': 'CTRL', 'right ctrl': 'R CTL', 'left alt': 'ALT', 'right alt': 'R ALT',
           'left gui': 'WIN', 'right gui': 'R WIN', 'capslock': 'CAPS', 'numlock': 'NUM',
           'scrolllock': 'SCRL', 'printscreen': 'PRT', 'pause': 'PAUSE', 'insert': 'INS',
           'delete': 'DEL', 'home': 'HOME', 'end': 'END', 'pageup': 'PGUP', 'pagedown': 'PGDN',
           'application': 'MENU', 'comma': ',', 'equals': '=', 'none': '-'}


def canonical_key(value):
    value = value.strip(' \t\r\n')
    for name in MOUSE:
        if name.lower() == value.lower():
            return name
    if value.lower() in ('none', 'comma', 'equals'):
        return value.lower()
    return SDL_KEYS.get(value.lower())


def apply(defaults, spec, keyboard=True):
    result = defaults.copy()
    # The runtime copies at most 1023 bytes and keeps the last valid entry.
    for entry in spec.encode('utf-8')[:1023].decode('utf-8', 'ignore').split(','):
        if '=' not in entry:
            continue
        name, value = (v.strip(' \t\r\n') for v in entry.split('=', 1))
        name = name.lower()
        if name == 'touchpad':
            name = 'touchpad_left'
        allowed = defaults if defaults is STICK_DEFAULTS else KEY_DEFAULTS
        if name not in allowed:
            continue
        source = canonical_key(value) if keyboard else value.lower()
        if source is not None and (keyboard or source in PAD_LABELS or source == 'none'):
            result[name] = source
    return result


class Resolver:
    def __init__(self, style, env):
        if style not in ('keyboard', 'xbox'):
            raise ValueError('Unsupported generated prompt style')
        self.style = style
        self.keys = apply(KEY_DEFAULTS, env.get('RATCHET_KEY_MAP', ''))
        secondary = apply(dict.fromkeys(KEY_DEFAULTS, 'None'), env.get('RATCHET_KEY_MAP_ALT', ''))
        for button, value in self.keys.items():
            if value.lower() == 'none':
                self.keys[button] = secondary[button]
        self.sticks = apply(STICK_DEFAULTS, env.get('RATCHET_STICK_KEYS', ''))
        self.pad = apply(PAD_DEFAULTS, env.get('RATCHET_PAD_MAP', ''), False)

    def key(self, source):
        value = canonical_key(source)
        if value in MOUSE:
            return ('mouse', value)
        if value is None:
            return ('key', '?')
        lower = value.lower()
        if lower in ('up','down','left','right'):
            return ('arrow', lower)
        if lower.startswith('keypad '):
            label = value[7:].upper()
            label = {'ENTER':'ENT'}.get(label,label)
            return ('key', 'N'+label if len(label)<=3 else '?')
        return ('key', SPECIAL.get(lower, value.upper() if len(value)<=5 else '?'))

    def resolve(self, logical):
        if logical in ('stick_left', 'stick_right', 'dpad_all'):
            if self.style == 'xbox':
                return ('pad','DPAD') if logical=='dpad_all' else ('stick','LS' if logical=='stick_left' else 'RS')
            names = (('left','right','up','down') if logical == 'dpad_all' else
                     tuple(('l' if logical=='stick_left' else 'r')+n for n in ('x_neg','x_pos','y_neg','y_pos')))
            mapping = self.keys if logical=='dpad_all' else self.sticks
            sources = [mapping[n] for n in names]
            if sources == ['Mouse Move Left','Mouse Move Right','Mouse Move Up','Mouse Move Down']:
                return ('mouse','Mouse Move All')
            return ('cluster',tuple(self.key(v) for v in sources))
        if self.style=='keyboard':
            return self.key(self.keys.get(logical,'None'))
        if logical in ('l2','r2'):
            return ('pad','LT' if logical=='l2' else 'RT')  # Physical triggers stay active.
        if logical=='touchpad_left':
            return ('chord',(self.resolve('l1'),self.resolve('touchpad_right')))
        source=self.pad.get(logical,'none')
        if source in ('dpup','dpdown','dpleft','dpright'):
            return ('arrow',source[2:])
        return ('pad',PAD_LABELS.get(source,'-'))
