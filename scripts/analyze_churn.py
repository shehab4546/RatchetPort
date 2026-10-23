# SPDX-License-Identifier: GPL-2.0-or-later
"""Summarize complete ChurnTrace windows; never count partial diagnostic output.

Producer associations describe declared writers, not proof of GPU data changes.
The schema comes from video_core/texture_cache/churn_trace.cpp.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

TOTALS = ('uploads', 'legacy_bytes', 'copy_payload_bytes', 'same_epoch', 'adjacent_epoch')
PRODUCER_ID = ('uid', 'kind', 'stage', 'slot', 'binding', 'producer_flags',
               'shader', 'write_addr', 'write_bytes', 'copy_src')


def _complete(group):
    summaries, images, producers = (group[k] for k in ('summary', 'image', 'producer'))
    if len(summaries) != 1:
        return False
    summary = summaries[0]
    try:
        if summary['images'] != len(images) or summary['producer_rows'] != len(producers):
            return False
        if any(summary[k] for k in ('dropped_image_events', 'dropped_gap_events',
                                    'dropped_producer_events')):
            return False
        by_uid = {r['uid']: r for r in images}
        if len(by_uid) != len(images):
            return False
        if len({tuple(r[k] for k in PRODUCER_ID) for r in producers}) != len(producers):
            return False
        if any(r['uid'] not in by_uid for r in producers):
            return False
        if any(summary[k] != sum(r[k] for r in images) for k in TOTALS):
            return False
        for uid, image in by_uid.items():
            writers = [r for r in producers if r['uid'] == uid]
            if image['gpu'] != sum(r['invalidations'] for r in writers):
                return False
            if sum(r['last_writer_uploads'] for r in writers) > image['uploads']:
                return False
            if sum(r['last_writer_payload_bytes'] for r in writers) > image['copy_payload_bytes']:
                return False
            # Required even in windows without producer events.
            if image['zero_mirrors'] < 0:
                return False
        for row in producers:
            if not 0 <= row['multi_producer_uploads'] <= row['multi_event_uploads'] <= row['last_writer_uploads']:
                return False
    except KeyError:
        return False
    return True


def analyze(path, max_window=None):
    windows = defaultdict(lambda: defaultdict(list))
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.startswith('RATCHET CHURN '):
            continue
        kind = line.split()[2]
        if kind not in ('summary', 'image', 'producer', 'gap'):
            raise ValueError(f'Unknown churn row type: {kind}')
        row = {k: int(v, 0) for k, v in re.findall(r'(\w+)=(0x[\da-fA-F]+|\d+)(?=\s|$)', line)}
        if 'window' not in row:
            raise ValueError('Churn row has no valid window number')
        if max_window is None or row['window'] <= max_window:
            windows[row['window']][kind].append(row)
    valid, excluded = [], []
    for number, group in sorted(windows.items()):
        (valid if _complete(group) else excluded).append(number)
    images = [r for n in valid for r in windows[n]['image']]
    producers = [r for n in valid for r in windows[n]['producer']]
    return {
        'window_totals_verified': bool(valid) and not excluded,
        'producer_trace_present': any(g['producer'] for g in windows.values()),
        'included_windows': valid,
        'incomplete_or_inconsistent_windows_excluded': excluded,
        'last_writer_associated_payload_bytes': sum(r['last_writer_payload_bytes'] for r in producers),
        'multi_producer_uploads': sum(r['multi_producer_uploads'] for r in producers),
        'zero_mirrors': sum(r['zero_mirrors'] for r in images),
        **{k: sum(r[k] for r in images) for k in TOTALS},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--max-window', type=int)
    args = parser.parse_args()
    print(json.dumps(analyze(args.log, args.max_window), indent=2))
