# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded CUSA01047 prompt archives. Installed files are never written."""
import hashlib
import struct
import zlib
from pathlib import Path

LIMIT = 32 << 20
ARCHIVE_NAME = 'rpglyph'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Toc:
    def __init__(self, raw):
        if len(raw) < 8 or raw[:4] != bytes.fromhex('af12af77'):
            raise ValueError('Unsupported prompt TOC signature')
        expected, = struct.unpack_from('<I', raw, 4)
        if not 88 <= expected <= LIMIT:
            raise ValueError('Invalid TOC length')
        dec = zlib.decompressobj()
        self.data = bytearray(dec.decompress(raw[8:], expected + 1))
        # Retail TOC omits the zlib end marker; all bytes and lengths must agree.
        if len(self.data) != expected or dec.unconsumed_tail or dec.unused_data:
            raise ValueError('TOC decompression length mismatch')
        magic, kind, size, count = struct.unpack_from('<4I', self.data)
        if magic != 0x44415431 or size != expected or count != 6:
            raise ValueError('Unsupported TOC DAT1 header')
        self.sections = {}
        ranges = []
        for i in range(count):
            tag, offset, length = struct.unpack_from('<III', self.data, 16 + i * 12)
            if tag in self.sections or offset < 88 or offset + length > size:
                raise ValueError('Invalid TOC section')
            self.sections[tag] = (offset, length, 16 + i * 12)
            ranges.append((offset, offset + length))
        ordered = sorted(ranges)
        if any(b > c for (_, b), (c, _) in zip(ordered, ordered[1:])):
            raise ValueError('Overlapping TOC sections')
        for tag, stride in ((0x398abff0, 24), (0x506d7b8a, 8),
                            (0x65bcf461, 12), (0xdcd720b5, 8), (0xede8ada9, 8)):
            if tag not in self.sections or self.sections[tag][1] % stride:
                raise ValueError('Unsupported TOC stride')
        ho, hs, _ = self.sections[0x506d7b8a]
        so, ss, _ = self.sections[0x65bcf461]
        if hs // 8 != ss // 12:
            raise ValueError('TOC asset counts disagree')
        self.ids = {}
        for i, (value,) in enumerate(struct.iter_unpack('<Q', self.data[ho:ho + hs])):
            self.ids.setdefault(value, []).append(i)
        ao, az, _ = self.sections[0x398abff0]
        self.archives = []
        for pos in range(ao, ao + az, 24):
            name = bytes(self.data[pos + 8:pos + 24]).split(b'\0')[0].decode('ascii')
            if not name or any(c in name for c in '/\\:') or '..' in name:
                raise ValueError('Unsafe TOC archive name')
            self.archives.append(name)

    def locate(self, asset_id):
        indices = self.ids.get(asset_id, [])
        if len(indices) != 1:
            raise ValueError(f'Missing or ambiguous prompt {asset_id:016x}')
        so, _, _ = self.sections[0x65bcf461]
        size_at = so + indices[0] * 12
        count, size, chunk = struct.unpack_from('<III', self.data, size_at)
        co, cs, _ = self.sections[0xdcd720b5]
        if count != 1 or chunk >= cs // 8 or not 0 < size <= LIMIT:
            raise ValueError('Unsupported prompt chunk layout')
        chunk_at = co + chunk * 8
        archive, offset = struct.unpack_from('<II', self.data, chunk_at)
        if archive >= len(self.archives):
            raise ValueError('Prompt archive index out of bounds')
        return self.archives[archive], offset, size, size_at, chunk_at

    def read(self, folder, asset_id, expected_hash):
        name, offset, size, _, _ = self.locate(asset_id)
        path = (Path(folder) / name).resolve()  # Existing mod links are read-only.
        before = path.stat()
        if offset + size > before.st_size:
            raise ValueError(f'Prompt segment exceeds {name}')
        with path.open('rb') as stream:
            stream.seek(offset)
            data = stream.read(size)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f'{name} changed during prompt preparation')
        if len(data) != size or digest(data) != expected_hash:
            raise ValueError(f'Prompt identity mismatch in {name} at {offset} '
                             f'(asset={asset_id:016x}, size={size}, '
                             f'expected_sha256={expected_hash}, actual_sha256={digest(data)})')
        return data

    def overlay(self, replacements):
        data = bytearray(self.data)
        ao, az, table = self.sections[0x398abff0]
        if ao + az != len(data) or ARCHIVE_NAME in self.archives:
            raise ValueError('Unsupported archive table placement')
        archive = bytearray()
        for asset_id, payload in sorted(replacements.items()):
            if not payload or len(archive) + len(payload) > LIMIT:
                raise ValueError('Prompt overlay exceeds size limit')
            _, _, _, size_at, chunk_at = self.locate(asset_id)
            struct.pack_into('<I', data, size_at + 4, len(payload))
            struct.pack_into('<II', data, chunk_at, len(self.archives), len(archive))
            archive.extend(payload)
        # Share the already-installed base archive's installation metadata.
        # A new invented chunkmap ID could refer to a nonexistent PlayGo chunk.
        if 'g00s000' not in self.archives:
            raise ValueError('Missing base archive installation metadata')
        base = ao + self.archives.index('g00s000') * 24
        data.extend(bytes(self.data[base:base + 8]) + struct.pack('<16s', ARCHIVE_NAME.encode()))
        struct.pack_into('<I', data, table + 8, az + 24)
        struct.pack_into('<I', data, 8, len(data))
        encoded = bytes.fromhex('af12af77') + struct.pack('<I', len(data)) + zlib.compress(data, 6)
        check = Toc(encoded)
        for asset_id, payload in replacements.items():
            name, offset, size, _, _ = check.locate(asset_id)
            if name != ARCHIVE_NAME or bytes(archive[offset:offset + size]) != payload:
                raise ValueError('Prompt overlay round trip failed')
        return encoded, bytes(archive)


def unpack_built(raw):
    if len(raw) < 36:
        raise ValueError('Short built chunk')
    expected = sum(struct.unpack_from('<II', raw, 4))
    if not 0 < expected <= LIMIT:
        raise ValueError('Invalid built length')
    src = memoryview(raw)[36:]
    out = bytearray()
    p = 0

    def length(n):
        nonlocal p
        if n == 15:
            while True:
                if p >= len(src):
                    raise ValueError('Truncated LZ4 length')
                v = src[p]; p += 1; n += v
                if n > expected:
                    raise ValueError('LZ4 length exceeds output')
                if v != 255:
                    break
        return n

    while p < len(src):
        token = src[p]; p += 1
        n = length(token >> 4)
        if p + n > len(src) or len(out) + n > expected:
            raise ValueError('Invalid LZ4 literals')
        out.extend(src[p:p + n]); p += n
        if p == len(src):
            break
        if p + 2 > len(src):
            raise ValueError('Truncated LZ4 offset')
        offset = src[p] | src[p + 1] << 8; p += 2
        n = length(token & 15) + 4
        if not 0 < offset <= len(out) or len(out) + n > expected:
            raise ValueError('Invalid LZ4 match')
        for _ in range(n):
            out.append(out[-offset])
    if len(out) != expected:
        raise ValueError('Built length mismatch')
    return bytes(out)


def pack_built(header, data):
    """Literal-only LZ4 avoids compression dependencies for these small assets."""
    if len(header) != 36 or sum(struct.unpack_from('<II', header, 4)) != len(data):
        raise ValueError('Built header length mismatch')
    extra = bytearray()
    n = len(data)
    if n >= 15:
        left = n - 15
        while left >= 255:
            extra.append(255); left -= 255
        extra.append(left)
    return header + bytes([min(n, 15) << 4]) + extra + data
