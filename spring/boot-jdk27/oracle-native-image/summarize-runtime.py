#!/usr/bin/env python3
"""Summarize one guest run; preserve raw samples and phase boundaries."""
import argparse
import json
from pathlib import Path
import statistics

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('run', type=Path)
a = p.parse_args()
samples = [json.loads(line) for line in (a.run/'samples.jsonl').read_text().splitlines()]

def kv(text):
    return {line.split()[0].rstrip(':'): line.split()[1] for line in text.splitlines() if len(line.split()) >= 2}

def proc_cpu(text):
    # comm may contain spaces; fields following ')' start at proc field 3.
    fields = text.rsplit(')', 1)[1].split()
    return int(fields[11])+int(fields[12])

result = {'startup': json.loads((a.run/'ready.json').read_text()), 'phases': {}}
clock_ticks = int((a.run/'clock-ticks.txt').read_text())
kernel = (a.run/'kernel-after.log').read_text()
result['kernel_oom_kill_seen'] = 'Out of memory: Killed process' in kernel
if (a.run/'host-final.json').exists():
    final = json.loads((a.run/'host-final.json').read_text())
    result['oom_kill_delta_total'] = int(kv(final['vmstat']).get('oom_kill', 0))-int(kv(samples[0]['vmstat']).get('oom_kill',0))

for phase in dict.fromkeys(s['phase'] for s in samples):
    rows = [s for s in samples if s['phase'] == phase]
    host = [kv(s['meminfo']) for s in rows]
    vm = [kv(s['vmstat']) for s in rows]
    summary = dict(samples=len(rows), elapsed_seconds=rows[-1]['monotonic']-rows[0]['monotonic'],
        mem_available_min_mib=min(int(h['MemAvailable']) for h in host)/1024,
        swap_used_max_mib=max(int(h['SwapTotal'])-int(h['SwapFree']) for h in host)/1024,
        pswpin_delta=int(vm[-1]['pswpin'])-int(vm[0]['pswpin']),
        pswpout_delta=int(vm[-1]['pswpout'])-int(vm[0]['pswpout']),
        oom_kill_delta=int(vm[-1].get('oom_kill',0))-int(vm[0].get('oom_kill',0)),
        processes={})
    for name in ['app', 'mariadb', 'fixture', 'statlite']:
        procs = [s['processes'][name] for s in rows if name in s['processes']]
        if not procs:
            continue
        # PID alone can be reused; proc field 22 identifies the process lifetime.
        identities = {(proc['pid'], int(proc['stat'].rsplit(')', 1)[1].split()[19])) for proc in procs}
        counters = [proc_cpu(proc['stat']) for proc in procs]
        reason = None
        if len(procs) != len(rows):
            reason = 'missing process samples'
        elif len(identities) != 1:
            reason = 'process identity changed'
        elif any(later < earlier for earlier, later in zip(counters, counters[1:])):
            reason = 'CPU counter decreased'
        rss = [int(kv(proc['status']).get('VmRSS',0))/1024 for proc in procs]
        summary['processes'][name] = dict(rss_median_mib=statistics.median(rss), rss_max_sampled_mib=max(rss),
            cpu_seconds_sampled=(counters[-1]-counters[0])/clock_ticks if reason is None else None,
            cpu_samples_complete=reason is None)
        if reason is not None:
            summary['processes'][name]['cpu_incomplete_reason'] = reason
    memory = [int(s['database_cgroup']['memory.current'])/1048576 for s in rows if 'memory.current' in s['database_cgroup']]
    if memory:
        summary['mariadb_cgroup_mib'] = dict(median=statistics.median(memory), max_sampled=max(memory))
    result['phases'][phase] = summary
(a.run/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
