#!/usr/bin/env python3
"""Recompute public headline figures from curated timed-window CSV evidence."""
import csv
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent / 'data'
with (root / 'process-memory.csv').open() as f:
    memory = list(csv.DictReader(f))
with (root / 'cpu-buckets.csv').open() as f:
    cpu = list(csv.DictReader(f))
with (root / 'requests.csv').open() as f:
    requests = list(csv.DictReader(f))
for phase in ['spring', 'quarkus', 'micronaut', 'shared']:
    print(phase)
    for name in ['spring', 'quarkus', 'micronaut', 'statlite', 'fixture']:
        rss = [float(r['rss_kib']) / 1024 for r in memory if r['phase'] == phase and r['process'] == name]
        if rss:
            print(f'  {name}: RSS median {statistics.median(rss):.1f} MiB, peak {max(rss):.1f} MiB, n={len(rss)}')
    for name in ['host', 'spring', 'quarkus', 'micronaut']:
        values = [float(r['value_percent']) for r in cpu if r['phase'] == phase and r['series'] == name]
        if values:
            print(f'  {name}: CPU mean {statistics.mean(values):.3f}%, median {statistics.median(values):.3f}%, highest bucket {max(values):.3f}%, n={len(values)}')
    rows = [r for r in requests if r['phase'] == phase]
    print(f'  scripted requests {len(rows)}, errors {sum(r["ok"] != "True" for r in rows)}')
