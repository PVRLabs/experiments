#!/usr/bin/env python3
"""Recompute published observations using only this curated evidence package."""
import csv
import importlib.util
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent

def load(path):
    return json.loads(path.read_text())

def close(actual, expected):
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-9):
        raise ValueError(f'measurement differs: {actual} != {expected}')

def read(name):
    path = HERE / 'data' / name
    rows = list(csv.DictReader((path / 'samples.csv').open()))
    requests = list(csv.DictReader((path / 'requests.csv').open()))
    return path, rows, requests

def memory(rows):
    return dict(samples=len(rows), app_rss_median_mib=statistics.median(float(r['app_rss_mib']) for r in rows),
                mem_available_min_mib=min(float(r['mem_available_mib']) for r in rows))

def traffic(rows, expected):
    if [int(r['index']) for r in rows] != list(range(expected['offered'])):
        raise ValueError('missing, reordered or duplicate requests')
    good = sorted(float(r['latency_ms']) for r in rows if r['ok'] == 'True')
    if len(good) != expected['successful'] or len(rows)-len(good) != expected['errors']:
        raise ValueError('request outcomes differ')
    if any(r['ok'] == 'True' and r['status'] != '200' for r in rows):
        raise ValueError('unexpected successful status')
    close(good[math.ceil(len(good)*.5)-1], expected['p50_ms'])
    close(good[math.ceil(len(good)*.95)-1], expected['p95_ms'])
    return dict(successful=len(good), errors=len(rows)-len(good), p50_ms=expected['p50_ms'], p95_ms=expected['p95_ms'])

comparison = load(HERE / 'results/comparison.json')
mybatis = load(HERE / 'results/mybatis-comparison.json')
stability = load(HERE / 'results/stability-F-001.json')
report = {}
for name in ('regular-A-001','optimized-F-001','mybatis-memory-001','h2-F-001','stability-F-001'):
    path, rows, requests = read(name)
    phase = 'recorded-load' if name == 'stability-F-001' else 'workload'
    measured = [r for r in rows if r['phase'] == phase]
    result = memory(measured)
    result.update(traffic(requests, load(path / 'workload-summary.json')))
    if max(float(r['swap_used_mib']) for r in rows) != 0 or len({r['oom_kill'] for r in rows}) != 1:
        raise ValueError('swap use or OOM counter increase')
    if name in ('regular-A-001','optimized-F-001'):
        expected = comparison['runs']['A' if name == 'regular-A-001' else 'F']
        close(load(path / 'startup.json')['seconds'], expected['startup_seconds'])
        for label in ('idle','warmup','workload','recovery'):
            phase_rows = [r for r in rows if r['phase'] == label]
            saved = expected['phases'][label]
            close(len(phase_rows), saved['samples'])
            close(min(float(r['mem_available_mib']) for r in phase_rows), saved['mem_available_min_mib'])
            for process, values in saved['processes'].items():
                rss = [float(r[process+'_rss_mib']) for r in phase_rows]
                close(statistics.median(rss), values['rss_median_mib'])
                close(max(rss), values['rss_max_sampled_mib'])
        close(sum(float(r['mem_available_mib']) < 32 for r in measured), expected['workload_samples_below_32_mib'])
        traffic(requests, expected['workload'])
    if name in ('optimized-F-001','mybatis-memory-001'):
        expected = mybatis['jdbc' if name == 'optimized-F-001' else 'mybatis']['first_minute_workload']
        boundary = next(float(r['monotonic']) for r in rows if r['phase'] == 'transition-to-workload')
        first = [r for r in measured if float(r['monotonic']) < boundary+60]
        close(len(first), expected['samples'])
        close(memory(first)['app_rss_median_mib'], expected['processes']['app']['rss_median_mib'])
        close(memory(first)['mem_available_min_mib'], expected['mem_available_min_mib'])
        traffic(requests[:300], dict(offered=300, **{k:expected[k] for k in ('successful','errors','p50_ms','p95_ms')}))
    if name == 'stability-F-001':
        expected = stability['recorded_load']
        close(len(measured), expected['samples'])
        close(result['mem_available_min_mib'], expected['mem_available_min_mib'])
        for process, values in expected['processes'].items():
            rss = [float(r[process+'_rss_mib']) for r in measured]
            close(statistics.median(rss), values['rss_median_mib'])
            close(max(rss), values['rss_peak_mib'])
    report[name] = result

spec = importlib.util.spec_from_file_location('memory_observations', HERE / 'memory-observations.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for name, saved in [('optimized-F-001','mariadb-F-memory-observations.json'),('h2-F-001','h2-F-memory-observations.json')]:
    path = HERE / 'data' / name
    samples = [json.loads(s) for s in (path/'memory-samples.jsonl').read_text().splitlines()]
    metrics = [json.loads(s) for s in (path/'memory-metrics.jsonl').read_text().splitlines()]
    if module.observations(samples, metrics) != load(HERE/'results'/saved):
        raise ValueError(f'JVM/OS memory reanalysis differs for {name}')
    close(report[name]['app_rss_median_mib'], load(HERE/'results'/saved)['proc_status']['VmRSS']['median_mib'])
print(json.dumps(report, indent=2))
print('Validated request outcomes/percentiles, phase memory, matched MyBatis window, monitor RSS and JVM/OS summaries.')
