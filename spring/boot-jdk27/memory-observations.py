#!/usr/bin/env python3
"""Analyze existing Prometheus and /proc data; add no runtime diagnostics."""
import argparse
import json
import math
from pathlib import Path
import re
import statistics

PATTERN=re.compile(r'^(jvm_memory_(?:used|committed|max)_bytes|jvm_buffer_(?:memory_used_bytes|total_capacity_bytes|count_buffers)|jvm_threads_live_threads|jvm_classes_loaded_classes)(\{[^}]*\})?\s+(\S+)')


def observations(samples, metrics):
    measured_phases=('recorded-load','workload')
    series={}
    aggregates={}
    for row in metrics:
        if row['phase'] not in measured_phases: continue
        totals={}
        for line in row['prometheus'].splitlines():
            match=PATTERN.match(line)
            if not match: continue
            value=float(match[3])
            if not math.isfinite(value): continue
            key=match[1]+(match[2] or '')
            series.setdefault(key,[]).append(value)
            if match[1] in ('jvm_memory_used_bytes','jvm_memory_committed_bytes'):
                labels=match[2] or ''
                group='heap' if 'area="heap"' in labels else 'nonheap'
                kind='used' if match[1]=='jvm_memory_used_bytes' else 'committed'
                total=group+'_'+kind+'_bytes'
                totals[total]=totals.get(total,0)+value
                if 'CodeHeap' in labels:
                    total='code_cache_'+kind+'_bytes'
                    totals[total]=totals.get(total,0)+value
        for key,value in totals.items():
            aggregates.setdefault(key,[]).append(value)
    gauges={k:dict(samples=len(v),median=statistics.median(v),minimum=min(v),maximum=max(v),first=v[0],last=v[-1]) for k,v in sorted(series.items())}
    rows=[s for s in samples if s['phase'] in measured_phases]
    os={}
    for name in ('VmRSS','RssAnon','RssFile','RssShmem','VmData','VmStk','VmExe','VmLib','VmPTE'):
        values=[]
        for row in rows:
            status=row['processes'].get('app',{}).get('status','')
            fields={line.split(':',1)[0]:line.split(':',1)[1].split()[0] for line in status.splitlines() if ':' in line and line.split(':',1)[1].split()}
            if name in fields: values.append(int(fields[name])/1024)
        os[name]=dict(samples=len(values),missing=len(rows)-len(values),median_mib=statistics.median(values) if values else None,maximum_mib=max(values) if values else None)
    return dict(source='existing 10-second Prometheus scrapes and 1-second /proc status; measured workload phases only',
                limitation='JVM gauges are not RSS or complete native allocation accounting; max=-1 means undefined, not negative capacity',
                prometheus=gauges,
                derived_simultaneous_pool_sums={k:dict(samples=len(v),median=statistics.median(v),minimum=min(v),maximum=max(v),first=v[0],last=v[-1]) for k,v in sorted(aggregates.items())},
                proc_status=os)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('samples',type=Path)
    p.add_argument('metrics',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=observations([json.loads(x) for x in a.samples.read_text().splitlines()],
                        [json.loads(x) for x in a.metrics.read_text().splitlines()])
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Observed',len(result['prometheus']),'JVM gauges and',len(result['proc_status']),'OS memory fields')
