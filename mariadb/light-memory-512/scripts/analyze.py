#!/usr/bin/python3
import csv
import math
import statistics
import sys
from pathlib import Path

root = Path(sys.argv[1])
samples = list(csv.DictReader((root / 'memory.csv').open())) if (root / 'memory.csv').exists() else []
latencies = list(csv.DictReader((root / 'latencies.csv').open())) if (root / 'latencies.csv').exists() else []
oom_kill_increased = False
# One-second sampling. A gap above 2s, or fewer than one measured sample per 2s,
# can miss the peak PSS. Latency from a finished driver run stays usable.
MAX_SAMPLE_GAP_SECONDS = 2.0
MIN_MEASURED_SAMPLES_PER_SECOND = 0.5

def column(rows, key):
    return [int(row[key]) for row in rows]

for name in ('idle', 'warmup', 'measured'):
    data = [row for row in samples if row['phase'] == name]
    pss = column(data, 'pss_kib')
    rss = column(data, 'rss_kib')
    available = column(data, 'mem_available_kib')
    print(
        f'{name}: samples={len(data)} '
        f'pss_median_kib={statistics.median(pss) if pss else "missing"} '
        f'pss_peak_kib={max(pss) if pss else "missing"} '
        f'rss_peak_kib={max(rss) if rss else "missing"} '
        f'mem_available_min_kib={min(available) if available else "missing"}'
    )
if samples:
    print(
        f'all: samples={len(samples)} pss_peak_kib={max(column(samples, "pss_kib"))} '
        f'rss_peak_kib={max(column(samples, "rss_kib"))} '
        f'mem_available_min_kib={min(column(samples, "mem_available_kib"))}'
    )
    measured = [row for row in samples if row['phase'] == 'measured']
    if len(measured) >= 2:
        print(f"measured_disk_read_sectors={int(measured[-1]['disk_read_sectors']) - int(measured[0]['disk_read_sectors'])}")
        print(f"measured_disk_write_sectors={int(measured[-1]['disk_write_sectors']) - int(measured[0]['disk_write_sectors'])}")
    first, last = samples[0], samples[-1]
    print('swap: first/last free_kib, pswpin, pswpout:', [(row['swap_free_kib'], row['pswpin'], row['pswpout']) for row in (first, last)])
    swapped = any(int(last[key]) > int(first[key]) for key in ('pswpin', 'pswpout')) or min(int(row['swap_free_kib']) for row in samples) < int(first['swap_free_kib'])
    print('latency_swap_status=' + ('INVALID: swap activity observed' if swapped else 'no swap activity observed'))
    oom_kill_increased = int(last['oom_kill']) > int(first['oom_kill'])
    print('oom_kill_increased=' + str(oom_kill_increased))

active = [row for row in samples if row['phase'] in ('idle', 'warmup', 'measured')]
gaps = [float(active[index]['timestamp']) - float(active[index - 1]['timestamp']) for index in range(1, len(active))]
max_gap = max(gaps) if gaps else None
if max_gap is None:
    print('sample_gap_max_seconds=missing')
else:
    print(f'sample_gap_max_seconds={max_gap:.3f}')

def percentile(values, fraction):
    if not values:
        return 'missing'
    return values[max(0, math.ceil(fraction * len(values)) - 1)]

for kind in ('point', 'range', 'aggregate'):
    values = sorted(float(row['seconds']) * 1000 for row in latencies if row['type'] == kind)
    print(f'{kind}: count={len(values)} p50_ms={percentile(values, .5)} p95_ms={percentile(values, .95)}')
if (root / 'run.txt').exists():
    run = (root / 'run.txt').read_text()
    print(run.strip())
    fields = dict(line.split('=', 1) for line in run.splitlines() if '=' in line)
    elapsed = float(fields.get('measured_seconds') or 0)
    if elapsed > 0:
        print(f'measured_window_query_completion_rate_per_second={len(latencies) / elapsed:.3f}')
        print('throughput_note=completed queries initiated in measured window divided by initiation-window duration; in-flight queries were drained afterward')
if (root / 'status.csv').exists():
    status = {row['label']: row for row in csv.DictReader((root / 'status.csv').open())}
    if 'measured_start' in status and 'measured_end' in status:
        for key in ('innodb_buffer_pool_reads', 'innodb_buffer_pool_read_requests', 'aria_pagecache_reads', 'aria_pagecache_read_requests'):
            print(f'measured_{key}_delta={int(status["measured_end"][key]) - int(status["measured_start"][key])}')

measured_rows = [row for row in samples if row['phase'] == 'measured']
fields = {}
if (root / 'run.txt').exists():
    fields = dict(line.split('=', 1) for line in (root / 'run.txt').read_text().splitlines() if '=' in line)
elapsed = float(fields.get('measured_seconds') or 0)
reasons = []
if oom_kill_increased:
    reasons.append('OOM kill observed during run')
if max_gap is None or max_gap > MAX_SAMPLE_GAP_SECONDS:
    shown = 'missing' if max_gap is None else f'{max_gap:.3f}s'
    reasons.append(f'sample gap {shown} exceeds {MAX_SAMPLE_GAP_SECONDS:.0f}s')
if elapsed <= 0:
    reasons.append('measured duration missing')
else:
    rate = len(measured_rows) / elapsed
    print(f'measured_samples_per_second={rate:.3f}')
    if rate < MIN_MEASURED_SAMPLES_PER_SECOND:
        reasons.append(f'measured coverage {rate:.3f}/s is below {MIN_MEASURED_SAMPLES_PER_SECOND:.1f}/s')
    configured = fields.get('configured_measured_seconds')
    if configured is None:
        reasons.append('run record missing configured_measured_seconds')
    elif elapsed + 0.5 < float(configured):
        reasons.append(f'measured phase ended early: {elapsed:.1f}s of {configured}s configured')
errors_text = fields.get('errors', '').strip()
if fields and errors_text != '[]':
    reasons.append('driver reported errors: ' + (errors_text or 'missing'))
if reasons:
    print('memory_evidence=incomplete')
    print('memory_evidence_reason=' + '; '.join(reasons))
    print('memory_comparison=excluded')
else:
    print('memory_evidence=complete')
    print('memory_comparison=usable')
