#!/usr/bin/env python3
"""Recompute summaries using only this package's curated OS/HTTP evidence."""
import csv
import json
import os
from pathlib import Path
import compare

ROOT = Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)
    roots = sorted(Path('results/measured').glob('*'))
    roots = [p for p in roots if (p/'run.json').is_file()]
    main_roots = [p for p in roots if not json.loads((p/'run.json').read_text())['monitored']]
    for name, group in [('main-comparison.json', main_roots), ('complete-comparison.json', roots)]:
        report = compare.compare(group)
        assert report['complete'], report['issues']
        (ROOT/name).write_text(json.dumps(report, indent=2)+'\n')
    for root in roots:
        assert not (root/'guest/oom-events.txt').read_text().strip(), root
        assert json.loads((root/'run.json').read_text())['runtime']['swap_total_kib'] == 0, root
    monitored = [p for p in roots if json.loads((p/'run.json').read_text())['monitored']]
    assert len(monitored) == 1
    root = monitored[0]
    phases = json.loads((root/'phases.json').read_text())
    with (root/'guest/os.csv').open() as source:
        samples = [{k:float(v) for k,v in row.items()} for row in csv.DictReader(source)]
    cpu = {}
    for i, phase in enumerate(phases[:-1]):
        if phase['phase'] not in ['monitor-only', 'workload']:
            continue
        rows = [s for s in samples if phase['epoch'] <= s['epoch'] < phases[i+1]['epoch'] and s['monitor_pid'] > 0]
        assert len({s['monitor_pid'] for s in rows}) == 1
        first, last = rows[0], rows[-1]
        cpu[phase['phase']] = (last['monitor_cpu_ticks']-first['monitor_cpu_ticks'])/(last['uptime']-first['uptime'])
    summary = {
        'purpose':'Frozen MyBatis StatLite demonstration; one repeat does not isolate causal overhead.',
        'runs':[r for r in report['runs'] if r['variant'] == 'javalin-mybatis'],
        'monitor_cpu_pct_single_vcpu':cpu,
        'monitor_cpu_method':'100 Hz process tick deltas between samples with a live unchanged monitor PID, divided by elapsed uptime.',
        'recorded_sqlite_integrity_check':json.loads((root/'monitoring-integrity.json').read_text()),
        'inspection':'Operator completed dashboard inspection; both screenshots included. Services stopped before archive collection.'
    }
    (ROOT/'monitored-comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('PASS: six unmonitored runs plus one monitored MyBatis repeat; zero workload errors, correct final states and valid sampling.')


if __name__ == '__main__':
    main()
