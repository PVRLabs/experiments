#!/usr/bin/python3
import csv
import statistics
import sys
from pathlib import Path
p = Path(sys.argv[1])
with (p / 'memory.csv').open() as f: samples = list(csv.DictReader(f))
with (p / 'latencies.csv').open() as f: latencies = list(csv.DictReader(f))
for phase in ('idle', 'measured'):
    data = [int(r['pss_kib']) for r in samples if r['phase'] == phase]
    print(f'{phase}: samples={len(data)} pss_median_kib={statistics.median(data) if data else "missing"} pss_peak_kib={max(data) if data else "missing"}')
for kind in ('point', 'range', 'aggregate'):
    values = sorted(float(r['seconds']) * 1000 for r in latencies if r['type'] == kind)
    def percentile(p): return values[max(0, __import__('math').ceil(p * len(values)) - 1)] if values else 'missing'
    print(f'{kind}: count={len(values)} p50_ms={percentile(.5)} p95_ms={percentile(.95)}')
run = (p / 'run.txt').read_text()
duration = float(next(line.split('=', 1)[1] for line in run.splitlines() if line.startswith('configured_measured_seconds=')))
print(run.strip())
print(f'total_throughput_per_second={len(latencies) / duration:.3f}')
if samples:
    print('swap: first/last free_kib, pswpin, pswpout:', [(r['swap_free_kib'], r['pswpin'], r['pswpout']) for r in (samples[0], samples[-1])])
    swapped = any(int(samples[-1][key]) > int(samples[0][key]) for key in ('pswpin', 'pswpout')) or min(int(r['swap_free_kib']) for r in samples) < int(samples[0]['swap_free_kib'])
    print('latency_swap_status=' + ('INVALID: swap activity observed' if swapped else 'no swap activity observed'))
