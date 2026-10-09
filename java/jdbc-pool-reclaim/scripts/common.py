"""Small shared readers used by the guest runner and offline summarizer."""
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics

# Overrides and resolved expectations are separate: default sizing is never supplied.
CONFIGS = {
    'default': {'sizing_overrides': {}, 'expected_minimum': 10, 'expected_maximum': 10, 'idle_ms': 0},
    'no-reclaim': {'sizing_overrides': {'minimum-idle': 1, 'maximum-pool-size': 10},
                   'expected_minimum': 1, 'expected_maximum': 10, 'idle_ms': 0},
    'reclaim': {'sizing_overrides': {'minimum-idle': 1, 'maximum-pool-size': 10},
                'expected_minimum': 1, 'expected_maximum': 10, 'idle_ms': 10000},
}
ORDER = ['default-1', 'no-reclaim-1', 'reclaim-1', 'reclaim-2', 'no-reclaim-2', 'default-2']
FLAGS = ['-Xms32m', '-Xmx192m', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=2']
# Workload seconds from end of baseline. The revisit is secondary evidence.
TIMELINE = {'A_start': 0, 'A_end': 16, 'B_start': 12, 'B_end': 68,
            'quiet_end': 128, 'A_revisit': 128, 'B_revisit': 130,
            'revisit_end': 134, 'final_end': 144, 'wave_interval': 2}
WINDOWS = {'initial': (-10, 0), 'A_just_idle': (16, 21),
           'B_busy_A_idle': (58, 68), 'both_quiet': (118, 128), 'final': (134, 144)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def jsonlines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def meminfo(raw):
    return {match[1]: int(match[2]) for match in re.finditer(r'^([\w()]+):\s+(\d+)', raw, re.M)}


def pool_metrics(raw, name):
    result = {}
    for line in raw.splitlines():
        match = re.fullmatch(r'hikaricp_connections(?:_(active|idle))?\{([^}]+)\}\s+([0-9.eE+-]+)', line)
        if match and f'pool="{name}"' in match[2]:
            result[match[1] or 'total'] = int(float(match[3]))
    if set(result) != {'active', 'idle', 'total'}:
        raise ValueError(f'Missing/ambiguous Hikari metrics for {name}: {result}')
    return result


def median(values):
    return statistics.median(values) if values else None


def latency(rows):
    successful = [row for row in rows if not row['error']]
    failed = [float(row['elapsed_ms']) for row in rows if row['error']]
    values = sorted(float(row['elapsed_ms']) for row in successful)
    # Nearest rank p95. These descriptive percentiles are not inferential statistics.
    import math
    return {'n': len(rows), 'successes': len(successful), 'errors': len(failed),
            'failed_max_ms': max(failed, default=None),
            'median_ms': median(values),
            'p95_ms': values[max(0, math.ceil(.95 * len(values)) - 1)] if values else None,
            'max_ms': max(values) if values else None}


def check_busy_window(samples, configuration, window=None):
    """Validate matched connection states throughout the late B-busy window."""
    lo, hi = WINDOWS['B_busy_A_idle'] if window is None else window
    selected = [s for s in samples if lo <= s['elapsed'] < hi]
    a_bounds = (1, 2) if configuration == 'reclaim' else (10, 10)
    observations, violations = [], []
    for sample in selected:
        pools = {n: sample.get('apps', {}).get(n, {}).get('pool', {}) for n in ['A', 'B']}
        pg = sample.get('pg', {})
        complete = (all(set(pools[n]) >= {'total', 'active', 'idle'} for n in ['A', 'B'])
                    and set(pg) >= {'A', 'B', 'aggregate'})
        if not complete:
            violations.append(dict(elapsed=sample['elapsed'], reason='Incomplete pool/PG observation'))
            continue
        observations.append(dict(elapsed=sample['elapsed'], pools=pools, pg=pg))
        if not (a_bounds[0] <= pools['A']['total'] <= a_bounds[1]
                and a_bounds[0] <= pg['A'] <= a_bounds[1]
                and pools['A']['active'] == 0
                and pools['B']['total'] == pg['B'] == 10
                and a_bounds[0] + 10 <= pg['aggregate'] <= a_bounds[1] + 10):
            violations.append(dict(elapsed=sample['elapsed'], reason='Unexpected connection state'))
    busy_samples = sum(o['pools']['B']['active'] > 0 for o in observations)
    if len(observations) < 5:
        violations.append(dict(reason='Fewer than five complete samples'))
    if not busy_samples:
        violations.append(dict(reason='No observed active B connections'))
    return dict(status='failed' if violations else 'passed', configuration=configuration,
                window=[lo, hi], expected_A_total=list(a_bounds), expected_B_total=10,
                expected_pg_aggregate=[a_bounds[0] + 10, a_bounds[1] + 10],
                complete_samples=len(observations), B_active_samples=busy_samples,
                observations=observations, violations=violations)


def summarize_run(root):
    root = Path(root)
    run = json.loads((root / 'run.json').read_text())
    samples = jsonlines(root / 'samples.jsonl')
    with (root / 'requests.csv').open() as stream:
        requests = list(csv.DictReader(stream))
    result = {'run': root.name, 'configuration': run['configuration'],
              'status': run['status'], 'mode': run['mode'], 'note': run.get('error', '')}
    result['peak_aggregate_pg'] = max((s['pg']['aggregate'] for s in samples if 'pg' in s), default=None)
    for name in ['A', 'B']:
        result[f'peak_{name}_pg'] = max((s['pg'][name] for s in samples if 'pg' in s), default=None)
        result[f'peak_{name}_hikari_total'] = max((s['apps'][name]['pool']['total'] for s in samples
             if 'pool' in s.get('apps', {}).get(name, {})), default=None)
    result['sample_errors'] = sum(bool(s.get('errors')) for s in samples)
    result['supporting_warnings'] = sum(bool(s.get('warnings')) for s in samples)
    for label, (lo, hi) in WINDOWS.items():
        selected = [s for s in samples if lo <= s['elapsed'] < hi]
        result[f'{label}_samples'] = len(selected)
        for key in ['aggregate', 'A', 'B']:
            result[f'{label}_pg_{key}'] = median([s['pg'][key] for s in selected if 'pg' in s])
        result[f'{label}_available_mib'] = median([s['host']['MemAvailable'] / 1024 for s in selected if 'host' in s])
        for key in ['pss_kib', 'private_kib', 'cgroup_bytes']:
            divisor = 1048576 if key == 'cgroup_bytes' else 1024
            result[f'{label}_pg_{key}_mib'] = median([s['pg_memory'][key] / divisor for s in selected
                                                     if s.get('pg_memory', {}).get(key) is not None])
        for name in ['A', 'B']:
            result[f'{label}_{name}_rss_mib'] = median([s['apps'][name]['rss_kib'] / 1024 for s in selected
                                                       if 'rss_kib' in s.get('apps', {}).get(name, {})])
            for key in ['active', 'idle', 'total']:
                result[f'{label}_{name}_hikari_{key}'] = median([s['apps'][name]['pool'][key] for s in selected
                                                               if 'pool' in s.get('apps', {}).get(name, {})])
    mechanism_path = root / 'mechanism-check.json'
    mechanism = json.loads(mechanism_path.read_text()) if mechanism_path.exists() else {}
    result['mechanism_status'] = mechanism.get('status', 'not-recorded')
    result['mechanism_samples'] = mechanism.get('complete_samples', 0)
    for name in ['A', 'B']:
        for stage in ['burst', 'revisit']:
            rows = [r for r in requests if r['instance'] == name and r['stage'] == stage]
            for key, value in latency(rows).items():
                result[f'{name}_{stage}_{key}'] = value
            acquisitions = [float(r['acquisition_ms']) for r in rows if not r['error'] and r['acquisition_ms']]
            result[f'{name}_{stage}_borrow_median_ms'] = median(acquisitions)
            result[f'{name}_{stage}_borrow_max_ms'] = max(acquisitions, default=None)
    for key, value in latency([r for r in requests if r['stage'] != 'warmup']).items():
        result[f'overall_{key}'] = value
    save(root / 'summary.json', result)
    return result


def summarize_session(root):
    root = Path(root)
    rows = [summarize_run(p) for p in sorted(root.iterdir()) if (p / 'run.json').exists()]
    rows.sort(key=lambda row: ORDER.index(row['run']) if row['run'] in ORDER else 0)
    if rows:
        with (root / 'summary.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return rows
