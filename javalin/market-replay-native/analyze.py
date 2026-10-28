#!/usr/bin/env python3
"""Reanalyze selected public evidence; no private files or dependencies required."""
import json
import math
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent

def load(path):
    return json.loads(path.read_text())

baseline = load(root / '../../spring/boot-jdk27/results/comparison.json')['runs']['F']
metadata = load(root / 'results/experiment.json')
assert baseline['raw_run'] == metadata['baseline']['run']
runs = {}
for path in sorted((root / 'results').glob('*comparison.json')):
    data = load(path)
    if 'javalin' not in data:
        continue
    accepted = data['javalin']
    run = accepted['source_run']
    runs[run] = accepted
    evidence = root / 'evidence' / run
    assert load(evidence / 'readiness.json')['seconds'] == accepted['startup_seconds']
    for phase in ['idle', 'warmup', 'workload', 'recovery']:
        rows = [r for r in load(evidence / 'memory-samples.json') if r['phase'] == phase]
        expected = accepted['phases'][phase]
        assert len(rows) == expected['samples']
        assert rows[-1]['monotonic'] - rows[0]['monotonic'] == expected['elapsed_seconds']
        assert min(r['mem_available_mib'] for r in rows) == expected['mem_available_min_mib']
        for process, metrics in expected['processes'].items():
            rss = [r['rss_mib'][process] for r in rows]
            assert statistics.median(rss) == metrics['rss_median_mib']
            assert max(rss) == metrics['rss_max_sampled_mib']
    for phase, count in [('warmup', 600), ('workload', 1500)]:
        requests = load(evidence / (phase + '-requests.json'))
        expected = accepted[phase]
        assert len(requests) == count == expected['offered']
        assert [r['index'] for r in requests] == list(range(count))
        assert all(r['ok'] and r['status'] == 200 for r in requests)
        values = sorted(r['latency_ms'] for r in requests)
        assert len(values) == expected['successful'] and expected['errors'] == 0
        for percentile in [50, 95]:
            assert values[math.ceil(len(values)*percentile/100)-1] == expected[f'p{percentile}_ms']
        for route, summary in expected['routes'].items():
            values = sorted(r['latency_ms'] for r in requests if r['path'] == route)
            assert len(values) == summary['successful']
            for percentile in [50, 95]:
                assert values[math.ceil(len(values)*percentile/100)-1] == summary[f'p{percentile}_ms']
    history = load(evidence / 'history.json')
    assert len(history) == 30 and len({r['id'] for r in history}) == 30
    for symbol in {r['symbol'] for r in history}:
        assert sorted((r['cycle'], r['sampleIndex']) for r in history if r['symbol'] == symbol) == [(0, i) for i in range(10)]
    assert accepted['oom_kill_delta_total'] == 0 and not accepted['kernel_oom_kill_seen']
    assert all(p['swap_used_max_mib'] == p['pswpin_delta'] == p['pswpout_delta'] == 0 for p in accepted['phases'].values())
    for label, value, reference in [
        ('startup', accepted['startup_seconds'], baseline['startup_seconds']),
        ('workload_app_rss', accepted['phases']['workload']['processes']['app']['rss_median_mib'], baseline['phases']['workload']['processes']['app']['rss_median_mib'])]:
        absolute_key = 'startup_seconds' if label == 'startup' else 'workload_app_rss_mib'
        assert math.isclose(data['differences'][absolute_key], value-reference, abs_tol=1e-12)
        assert math.isclose(data['differences'][label+'_reduction_percent'], (reference-value)/reference*100, abs_tol=1e-10)
    print(f'{run}: requests, phase RSS, readiness, history and accepted checks agree')

comparison = load(root / 'results/comparison.json')
if 'runs' in comparison:
    hotspot = load(root / '../market-replay-jdk27/results/comparison.json')['javalin']
    for name, expected in comparison['runs'].items():
        actual = baseline if name == 'spring_f' else hotspot if name == 'javalin_hotspot' else runs[expected['source_run']]
        assert expected['startup_seconds'] == actual['startup_seconds']
        assert expected['workload_app_rss_mib'] == actual['phases']['workload']['processes']['app']['rss_median_mib']
        assert expected['http'] == actual['workload']
    for metric, delta in comparison['o2_vs_ob'].items():
        ob = comparison['runs']['native_ob'][metric]
        o2 = comparison['runs']['native_o2'][metric]
        assert math.isclose(delta['absolute'], o2-ob, abs_tol=1e-12)
        assert math.isclose(delta['percent'], (o2-ob)/ob*100, abs_tol=1e-10)
    print('Four-configuration values and optimization differences agree')
