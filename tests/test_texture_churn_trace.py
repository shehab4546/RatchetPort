"""Verify measurement semantics from a known event trace, including the disabled path."""
from pathlib import Path
import argparse
import importlib.util
import os
import re
import subprocess
import tempfile


def rows(output, kind):
    return [dict((key, int(value, 0)) for key, value in re.findall(
        r'(\w+)=(0x[\da-f]+|\d+)(?=\s|$)', line))
        for line in output.splitlines() if line.startswith('RATCHET CHURN ' + kind + ' ')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    env = dict(os.environ)
    env.pop('RATCHET_IMAGE_CHURN_LOG', None)
    off = subprocess.run([str(args.executable), 'off'], env=env, capture_output=True, text=True, check=True)
    assert not off.stdout and not off.stderr, 'Disabled instrumentation emitted output'
    on = subprocess.run([str(args.executable), 'on'], env=env, capture_output=True, text=True, check=True)
    data = rows(on.stderr, 'image')
    a = next(row for row in data if row['uid'] == 101 and row['window'] == 1)
    b = next(row for row in data if row['uid'] == 202 and row['window'] == 1)
    later = next(row for row in data if row['uid'] == 101 and row['window'] == 2)
    MiB = 1024 * 1024
    assert a['uploads'] == 3 and a['refreshes'] == 2
    assert a['legacy_bytes'] == 32 * MiB and a['copy_payload_bytes'] == 12 * MiB
    assert a['copy_span_bytes'] == 15 * MiB and a['copied_mips'] == 6
    assert a['ram_source_bytes'] == 16 * MiB + 64 and a['gpu_source_bytes'] == 0
    assert a['same_epoch'] == 1 and a['adjacent_epoch'] == 1
    assert a['cpu'] == 1 and a['backing'] == 1 and a['upload_cause_mask'] == 19
    assert b['gpu_source_bytes'] == 2 * MiB and b['ram_source_bytes'] == 0
    assert b['uploads'] == 0 and b['empty'] == 1
    assert later['uploads'] == 1 and later['adjacent_epoch'] == 1
    assert later['same_epoch'] == 0 and later['legacy_bytes'] == 0
    gap = rows(on.stderr, 'gap')
    assert len(gap) == 1 and gap[0]['calls'] == 2
    summaries = rows(on.stderr, 'summary')
    assert summaries[0]['generation_misses'] == 1 and summaries[1]['generation_misses'] == 0
    producers = rows(on.stderr, 'producer')
    def producer(window, uid, kind, shader=0):
        return next(row for row in producers if (row['window'], row['uid'], row['kind'], row['shader'])
                    == (window, uid, kind, shader))
    shader = producer(3, 101, 1, 0x123456789abcdef0)
    assert shader['stage'] == 5 and shader['slot'] == 3 and shader['binding'] == 9
    assert shader['invalidations'] == 2 and shader['last_writer_uploads'] == 1
    assert shader['last_writer_payload_bytes'] == 32 and shader['multi_event_uploads'] == 1
    assert shader['multi_producer_uploads'] == 0
    copy = producer(3, 202, 2)
    assert copy['copy_src'] == 0x2000 and copy['producer_flags'] == 2
    assert copy['invalidations'] == 1 and copy['last_writer_uploads'] == 0
    unknown = producer(4, 101, 0)
    assert unknown['invalidations'] == 0 and unknown['last_writer_payload_bytes'] == 16
    multiple = producer(4, 202, 1, 0x123456789abcdef0)
    assert multiple['invalidations'] == 2 and multiple['last_writer_payload_bytes'] == 48
    assert multiple['multi_event_uploads'] == 1 and multiple['multi_producer_uploads'] == 1
    assert producer(4, 202, 2)['last_writer_uploads'] == 0
    assert producer(5, 202, 0)['invalidations'] == 1
    assert producer(5, 202, 2)['multi_producer_uploads'] == 1
    assert producer(5, 101, 1, 0x123456789abcdef0)['last_writer_uploads'] == 1
    assert producer(6, 101, 1, 0x123456789abcdef0)['last_writer_uploads'] == 0
    mirrored = next(r for r in data if r['uid'] == 101 and r['window'] == 6)
    assert mirrored['zero_mirrors'] == 1 and mirrored['zero_mirror_texel_bytes'] == 4096
    for summary in summaries:
        window = summary['window']
        image_rows = [r for r in data if r['window'] == window]
        producer_rows = [r for r in producers if r['window'] == window]
        assert len(producer_rows) == summary['producer_rows']
        assert sum(r['gpu'] for r in image_rows) == sum(r['invalidations'] for r in producer_rows)
        assert summary['dropped_producer_events'] == 0
    with tempfile.TemporaryDirectory() as directory:
        log = Path(directory) / 'churn.txt'
        env['RATCHET_IMAGE_CHURN_LOG'] = str(log)
        quiet = subprocess.run([str(args.executable), 'off'], env=env, capture_output=True, check=True)
        assert not log.exists() and not quiet.stdout and not quiet.stderr
        dedicated = subprocess.run([str(args.executable), 'on'], env=env, capture_output=True, check=True)
        assert not dedicated.stdout and not dedicated.stderr
        assert rows(log.read_text(), 'producer') == producers
        analyzer_path = Path(__file__).resolve().parents[1] / 'scripts/analyze_churn.py'
        spec = importlib.util.spec_from_file_location('analyze_churn', analyzer_path)
        analyzer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analyzer)
        report = analyzer.analyze(log, 6)
        assert report['window_totals_verified'] and report['producer_trace_present']
        assert report['last_writer_associated_payload_bytes'] == 112
        assert report['multi_producer_uploads'] == 2
        assert report['zero_mirrors'] == 1
        assert not report['incomplete_or_inconsistent_windows_excluded']
        lines = log.read_text().splitlines()
        removed = next(line for line in lines if line.startswith('RATCHET CHURN producer window=3 '))
        log.write_text('\n'.join(line for line in lines if line != removed) + '\n')
        assert analyzer.analyze(log, 6)['incomplete_or_inconsistent_windows_excluded'] == [3]
        # Corrupt real trace output: aggregate counters must not conceal missing or duplicate rows.
        image = next(line for line in lines if line.startswith('RATCHET CHURN image window=3 '))
        summary = next(line for line in lines if line.startswith('RATCHET CHURN summary window=3 '))
        corruptions = [
            lines + [image], lines + [summary],
            [line for line in lines if line != summary],
            [line.replace('dropped_producer_events=0', 'dropped_producer_events=1')
             if line == summary else line for line in lines],
            [re.sub(r'copy_payload_bytes=\d+', 'copy_payload_bytes=999999', line)
             if line == summary else line for line in lines],
        ]
        for corrupted in corruptions:
            log.write_text('\n'.join(corrupted) + '\n')
            result = analyzer.analyze(log, 6)
            assert result['incomplete_or_inconsistent_windows_excluded'] == [3]
            assert not result['window_totals_verified']
        log.write_text('')
        assert not analyzer.analyze(log, 6)['window_totals_verified']
    print('PASS: accounting, producer/source attribution, nesting, threads, report boundaries, dedicated log, opt-out')


if __name__ == '__main__':
    main()
