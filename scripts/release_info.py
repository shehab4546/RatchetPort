# SPDX-License-Identifier: GPL-2.0-or-later
"""Port release identity shared by the launcher and distribution tools.

This is the port version, not the supported PS4 APP_VER (01.00).
"""
VERSION = '1.3.1'
CODENAME = 'Verified Preview'
RELEASE_LABEL = f'V{VERSION} — {CODENAME}'
APP_TITLE = f'RatchetPort {RELEASE_LABEL}'
ARCHIVE_STEM = f'RatchetPort-V{VERSION}-Verified-Preview'
WINDOWS_ARCHIVE = f'{ARCHIVE_STEM}-Windows.zip'
SOURCE_ARCHIVE = f'{ARCHIVE_STEM}-Source.zip'
FILE_VERSION = tuple(map(int, VERSION.split('.'))) + (0,)
