#!/usr/bin/env python3
"""Summarize retained raw files; never launch applications."""
import argparse
import json
from pathlib import Path
import statistics


def percentile(values, fraction):
    values = sorted(values)
    if not values: return None
    position = (len(values) - 1) * fraction
    low = int(position)
    return values[low] + (values[min(low + 1, len(values)-1)] - values[low]) * (position-low)


def analyze(folder):
    metadata = json.loads((folder/'metadata.json').read_text())
    samples = json.loads((folder/'samples.json').read_text())
    requests = json.loads((folder/'requests.json').read_text())
    result = {'variant': metadata['variant'], 'mode': metadata['mode'], 'startup_seconds': metadata.get('readiness_seconds'), 'phases': {}}
    for phase in sorted({s['phase'] for s in samples}):
        current = [s for s in samples if s['phase'] == phase]
        traffic = [r for r in requests if r['phase'] == phase]
        metrics = {}
        for key in ['VmRSS_kib','Pss_kib','MemAvailable_kib']:
            values = [s[key] for s in current if key in s]
            metrics[key] = {'median': statistics.median(values) if values else None, 'peak': max(values) if values else None, 'min': min(values) if values else None}
        metrics['requests'] = {}
        for path in sorted({r['path'] for r in traffic}):
            group = [r for r in traffic if r['path'] == path]
            values = [r['seconds'] * 1000 for r in group]
            span = max(s['time'] for s in current) - min(s['time'] for s in current) if len(current)>1 else 0
            metrics['requests'][path] = {'count':len(group),'errors':sum(r['status'] != 200 for r in group),'observed_requests_per_second':len(group)/span if span else None,'p50_ms':percentile(values,.5),'p95_ms':percentile(values,.95),'p99_ms':percentile(values,.99)}
        result['phases'][phase] = metrics
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);args=parser.parse_args()
    result=[analyze(p.parent) for p in sorted(args.directory.glob('*/metadata.json'))]
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
