#!/usr/bin/env python3
"""Validate six unmonitored runs; optional partial output is explicitly incomplete."""
import argparse
from collections import Counter
import contextlib
import io
import json
from pathlib import Path
import sys
import analyze

VARIANTS = ['javalin-jdbi3', 'javalin-mybatis', 'javalin-jooq']


def compare(roots):
    rows, issues, signatures, identities, intervals = [], [], [], [], []
    chronological=[]
    boots=[]
    observed_memory=[]
    for root in roots:
        meta = json.loads((root/'run.json').read_text())
        with contextlib.redirect_stdout(io.StringIO()):
            result = analyze.analyze(root)  # Recompute validity; never trust stale summaries.
        if meta['smoke']:
            issues.append(f'{root}: preparation is not measured evidence')
        if not result['validity']['valid_for_comparison']:
            issues.append(f'{root}: invalid evidence: '+ '; '.join(result['validity']['issues']))
        if 'preparation' in meta:
            preparation=json.loads((root/meta['preparation']).read_text())
            identity={key:preparation[key] for key in ['source_commit','application_jars','versions','jvm_flags','vm']}
        else:
            # Existing preparation archives retain their original format.
            manifest=json.loads((root/'input-manifest.json').read_text())
            identity={'application_jars':{k:v for k,v in manifest['artifacts'].items()
                      if k.startswith('javalin-') and k.endswith('.jar')}}
        observed_memory.append(result['actual_mem_mib'] * 1024)
        runtime={k:v for k,v in meta.get('runtime',{}).items() if k not in ['boot_id','uptime_seconds','mem_total_kib']}
        signatures.append(json.dumps(dict(vm=meta['vm'],durations=meta['durations'],
                          preparation=identity,runtime=runtime),sort_keys=True))
        identities.append((meta['vm'], meta['guest']))
        phases = json.loads((root/'phases.json').read_text())
        if phases:
            intervals.append((phases[0]['epoch'], phases[-1]['epoch']))
            chronological.append((phases[0]['epoch'],meta['variant'],meta['monitored']))
        boots.append(meta.get('runtime',{}).get('boot_id'))
        phase = result['phases'].get('workload', {})
        http = (result.get('http') or {}).get('overall', {})
        rows.append(dict(run=str(root), variant=meta['variant'], monitored=meta['monitored'],
                         valid=result['validity']['valid_for_comparison'],
                         actual_mem_mib=result['actual_mem_mib'],
                         ready_seconds=result['startup_to_ready_seconds'],
                         p50_ms=http.get('p50_ms'), p95_ms=http.get('p95_ms'), errors=http.get('errors'),
                         rss_median_mib=phase.get('java_rss_median_mib'), rss_peak_mib=phase.get('java_rss_peak_mib'),
                         min_available_mib=phase.get('min_available_mib'), cpu_pct=phase.get('host_busy_cpu_pct'),
                         correct=result['persistence_state']['matches']))
    if len({p.resolve() for p in roots}) != len(roots) or len(set(identities)) != len(identities):
        issues.append('Duplicate run directory or guest run identity')
    counts = Counter(r['variant'] for r in rows if not r['monitored'])
    if counts != Counter({v:2 for v in VARIANTS}):
        issues.append('Main comparison requires exactly two unmonitored runs per variant')
    sequence=[variant for _,variant,monitored in sorted(chronological) if not monitored]
    if sequence != VARIANTS + list(reversed(VARIANTS)):
        issues.append('Chronological main runs must be Jdbi, MyBatis, jOOQ, jOOQ, MyBatis, Jdbi')
    if any(not isinstance(boot,str) or not boot.strip() for boot in boots) or len(set(boot for boot in boots if isinstance(boot,str))) != len(boots):
        issues.append('Every measured run requires a recorded, distinct VM boot ID')
    monitored = [r for r in rows if r['monitored']]
    if len(monitored) > 1 or any(r['variant'] not in VARIANTS for r in monitored):
        issues.append('At most one monitored follow-up of a known variant is allowed')
    if len(set(signatures)) > 1:
        issues.append('Runs do not share VM, memory, phase configuration, and frozen inputs')
    # Reboots in the unchanged 512 MiB VM exposed a one-page MemTotal variation.
    # Preserve actual values and reject larger differences, rather than rounding
    # memory values in the evidence or ignoring memory comparability entirely.
    if observed_memory and max(observed_memory)-min(observed_memory) > 4:
        issues.append('Actual MemTotal differs by more than one 4 KiB page')
    if any(b[0] < a[1] for a,b in zip(sorted(intervals), sorted(intervals)[1:])):
        issues.append('Run intervals overlap; runs must be independent')
    ranges = {}
    # Invalid/incomplete evidence never produces an apparently complete ranking.
    if not issues:
        for variant in VARIANTS:
            group = [r for r in rows if r['variant'] == variant and not r['monitored']]
            ranges[variant] = {key:[min(r[key] for r in group),max(r[key] for r in group)]
                              for key in ['ready_seconds','p50_ms','p95_ms','rss_median_mib','rss_peak_mib']}
    return dict(complete=not issues, issues=issues, runs=rows, unmonitored_ranges=ranges)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--partial', action='store_true', help='Allow diagnostic incomplete output; ranges remain suppressed')
    args = parser.parse_args()
    result = compare(args.runs)
    print(json.dumps(result, indent=2))
    if not result['complete'] and not args.partial:
        sys.exit(1)


if __name__ == '__main__':
    main()
