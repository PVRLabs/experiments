#!/usr/bin/env python3
"""Reanalyze curated evidence using only this directory and Python's standard library."""
import csv
import json
import math
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent

def read(path):
    return json.loads((HERE/path).read_text())
def csv_rows(path):
    with (HERE/path).open() as f:
        return list(csv.DictReader(f))
def check(condition, message):
    if not condition:
        raise ValueError(message)
def near(a,b):
    return abs(a-b) < 1e-8

native=read('results/native-runtime.json')
obs=read('data/runtime/observations.json')
rows=csv_rows('data/runtime/os-samples.csv')
check(obs['phase_seconds']==[60,120,300,60] and obs['measured_run_status']=='completed','Complete measured phases')
check(obs['heap_argument']=='-Xmx80m' and obs['graceful_shutdown'],'Launch/shutdown observations')
check(near(native['startup_seconds'],obs['startup_seconds']),'Retained startup observation')
check(all(float(b['monotonic'])>float(a['monotonic']) for a,b in zip(rows,rows[1:])),'Monotonic sample order')
check(not obs['kernel_oom_kill_seen'] and obs['final_oom_kill']==int(rows[0]['oom_kill']),'No OOM delta')
check(all(int(r['swap_used_kib'])==0 for r in rows),'No swap use')
check(all(r['pswpin']==rows[0]['pswpin'] and r['pswpout']==rows[0]['pswpout'] for r in rows),'No paging activity')
for process in ['app','mariadb','fixture']:
    active=[r for r in rows if r['phase']!='before-launch']
    identities={(r[process+'_pid'],r[process+'_start_ticks']) for r in active}
    check(len(identities)==1 and all(r[process+'_pid'] for r in active),process+' identity continuity')
for phase in ['idle','warmup','workload','recovery']:
    samples=[r for r in rows if r['phase']==phase]
    accepted=native['phases'][phase]
    check(len(samples)==accepted['samples'],phase+' sample count')
    check(near(float(samples[-1]['monotonic'])-float(samples[0]['monotonic']),accepted['elapsed_seconds']),phase+' span')
    check(near(min(int(r['mem_available_kib']) for r in samples)/1024,accepted['mem_available_min_mib']),phase+' host minimum')
    for process in ['app','mariadb','fixture']:
        rss=[int(r[process+'_rss_kib'])/1024 for r in samples]
        s=accepted['processes'][process]
        check(near(statistics.median(rss),s['rss_median_mib']),phase+' '+process+' RSS median')
        check(near(max(rss),s['rss_max_sampled_mib']),phase+' '+process+' RSS sampled peak')
        cpu=(int(samples[-1][process+'_cpu_ticks'])-int(samples[0][process+'_cpu_ticks']))/obs['clock_ticks']
        check(near(cpu,s['cpu_seconds_sampled']),phase+' '+process+' CPU delta')
        check(all(int(b[process+'_cpu_ticks'])>=int(a[process+'_cpu_ticks']) for a,b in zip(samples,samples[1:])),process+' CPU order')
    cg=[int(r['db_cgroup_bytes'])/1048576 for r in samples]
    check(near(statistics.median(cg),accepted['mariadb_cgroup_mib']['median']),phase+' DB cgroup median')
    check(near(max(cg),accepted['mariadb_cgroup_mib']['max_sampled']),phase+' DB cgroup peak')
for phase,count in [('warmup',600),('workload',1500)]:
    requests=csv_rows(f'data/runtime/{phase}-requests.csv')
    accepted=native[phase]
    check(len(requests)==count==accepted['successful']==accepted['offered'] and accepted['errors']==0,phase+' request count')
    check([int(r['index']) for r in requests]==list(range(count)),phase+' request sequence')
    check(all(r['ok']=='True' and int(r['status'])==200 for r in requests),phase+' request outcomes')
    check(all(r['path']==('/api/quotes/latest' if i%2==0 else '/api/quotes/history') for i,r in enumerate(requests)),phase+' route alternation')
    latency=sorted(float(r['latency_ms']) for r in requests)
    for percentile in [.5,.95]:
        check(near(latency[math.ceil(count*percentile)-1],accepted[f'p{int(percentile*100)}_ms']),phase+' percentile')
    check(near(max(float(r['lag_ms']) for r in requests),accepted['max_dispatch_lag_ms']),phase+' dispatch lag')
    for route,summary in accepted['routes'].items():
        values=sorted(float(r['latency_ms']) for r in requests if r['path']==route)
        check(len(values)==summary['successful'],route+' count')
        for percentile in [.5,.95]:
            check(near(values[math.ceil(len(values)*percentile)-1],summary[f'p{int(percentile*100)}_ms']),route+' percentile')
check(near(min(int(r['mem_available_kib']) for r in rows)/1024,native['mem_available_min_all_samples_mib']),'All-sample host minimum')
for kind in ['some','full']:
    delta=obs['final_memory_psi_us'][kind]-int(rows[0]['psi_'+kind+'_us'])
    check(delta==native['memory_psi_stall_microseconds'][kind],'PSI '+kind)
load=[r for r in rows if r['phase']=='workload']
check(sum(int(r['mem_available_kib'])<32768 for r in load)==native['workload_samples_below_32_mib'],'Low-headroom samples')
check(near(max(float(b['monotonic'])-float(a['monotonic']) for a,b in zip(load,load[1:])),native['workload_sample_gap_max_seconds']),'Sampling gap')
check(obs['metric_scrape_count']==native['metrics_scrapes'],'Retained metric scrape inventory')
history=read('data/runtime/history.json')
check(len(history)==30 and [r['id'] for r in history]==list(range(1,31)),'Thirty persisted quote IDs')
for symbol in ['AAPL','GOOG','NVDA']:
    check([(r['cycle'],r['sampleIndex']) for r in history if r['symbol']==symbol]==[(0,i) for i in range(10)],symbol+' batches')
latest=read('data/runtime/latest.json')
check(latest==history[-3:],'Latest matches final batch')
export=(HERE/'data/runtime/database-export.txt').read_text()
check(all(f'{s}\t10\n' in export for s in ['AAPL','GOOG','NVDA']),'SQL export row counts')
check(all(f'0\t{i}\t09:{30+i:02d}' in export for i in range(10)),'SQL export batch order')

build=read('results/build.json')
check(build['exit_code']==0 and build['optimization_level']==2,'Successful default optimized build')
check(sum(build['payload_files'].values())==build['payload_bytes'],'Payload size arithmetic')
prep=read('results/functional.json')
check(all(prep['checks'].values()) and len(prep['checks'])==8,'Retained functional observations')
old=read('results/historical-f.json')
comparison=read('results/comparison.json')
check(comparison['native']==native,'Comparison matches native dataset')
for key,value in old.items():
    if key=='phases':
        for phase,summary in value.items():
            check(comparison['historical_F'][key][phase]==summary,'Historical F phase: '+phase)
    elif key!='source_url':
        check(comparison['historical_F'][key]==value,'Historical F snapshot: '+key)

print('PASS: curated runtime, request percentiles, memory/CPU, ingestion and retained build/contract observations')
print('Startup and compiler timing are retained observations; see reproduction-guide.md.')
