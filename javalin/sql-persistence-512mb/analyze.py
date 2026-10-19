#!/usr/bin/env python3
"""Derive phase evidence without conflating heap, RSS and available RAM."""
import argparse,csv,json,statistics
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import workload
from validation import sampling_coverage, workload_and_state
def cpu_breakdown(items):
    """CPU tick deltas; legacy traces cannot separate unrecorded steal."""
    keys = ('busy_pct', 'iowait_pct', 'steal_pct', 'busy_plus_steal_pct')
    if len(items) < 2:
        return dict.fromkeys(keys)
    first, last = items[0], items[-1]
    total = last['cpu_total_ticks'] - first['cpu_total_ticks']
    if total <= 0:
        return dict.fromkeys(keys)
    idle = last['cpu_idle_ticks'] - first['cpu_idle_ticks']
    iowait = last['cpu_iowait_ticks'] - first['cpu_iowait_ticks']
    known_steal = 'cpu_steal_ticks' in first and 'cpu_steal_ticks' in last
    steal = last['cpu_steal_ticks'] - first['cpu_steal_ticks'] if known_steal else None
    return {'busy_pct': 100*(total-idle-iowait-steal)/total if known_steal else None,
            'iowait_pct': 100*iowait/total,
            'steal_pct': 100*steal/total if known_steal else None,
            'busy_plus_steal_pct': 100*(total-idle-iowait)/total}

def analyze(root):
    meta=json.loads((root/'run.json').read_text());phases=json.loads((root/'phases.json').read_text())
    with (root/'guest/os.csv').open() as source:
        samples=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(source)]
    coverage=sampling_coverage(meta,phases,samples)
    summaries={}
    for i,phase in enumerate(phases[:-1]):
        begin=phase['epoch'];end=phases[i+1]['epoch'];rows=[s for s in samples if begin<=s['epoch']<end]
        if not rows:continue
        name=phase['phase'];first=rows[0];last=rows[-1];elapsed=last['uptime']-first['uptime']
        cpu = cpu_breakdown(rows)
        late_cpu = cpu_breakdown([s for s in rows if s['epoch'] >= end-60])
        paging=[]
        for left,right in zip(rows,rows[1:]):
            dt=right['uptime']-left['uptime']
            if dt <= 0: continue
            paging.append({'epoch':right['epoch'],'seconds':dt,'in_mib_s':(right['pswpin_pages']-left['pswpin_pages'])*4096/1048576/dt,'out_mib_s':(right['pswpout_pages']-left['pswpout_pages'])*4096/1048576/dt})
        streak=longest=0
        for r in paging:
            streak=streak+r['seconds'] if max(r['in_mib_s'],r['out_mib_s'])>1 else 0
            longest=max(longest,streak)
        summaries[name]={
          'sample_count':len(rows),
          'host_major_faults':last.get('host_major_faults',0)-first.get('host_major_faults',0),
          'java_major_faults':last.get('java_major_faults',0)-first.get('java_major_faults',0),'min_available_mib':min(s['mem_available_kib'] for s in rows)/1024,
          'headroom_dips':[{'epoch':s['epoch'],'available_mib':s['mem_available_kib']/1024} for s in rows if s['mem_available_kib']<24576],
          'java_rss_median_mib':statistics.median(s['java_rss_kib'] for s in rows)/1024,
          'java_rss_peak_mib':max(s['java_rss_kib'] for s in rows)/1024,
          'monitor_rss_median_mib':statistics.median(s['monitor_rss_kib'] for s in rows)/1024,
          'max_swap_used_mib':max(s['swap_used_kib'] for s in rows)/1024,
          'swap_in_mib':(last['pswpin_pages']-first['pswpin_pages'])*4096/1048576,
          'swap_out_mib':(last['pswpout_pages']-first['pswpout_pages'])*4096/1048576,
          'longest_paging_above_1_mib_s_seconds':longest,'host_busy_cpu_pct':cpu['busy_pct'],
          'late_cpu_pct':late_cpu['busy_pct'],
          'late_java_rss_median_mib':statistics.median(part)/1024 if (part := [s['java_rss_kib'] for s in rows if s['epoch']>=max(begin,end-60)]) else None,
          'java_cpu_pct':100*(last['java_cpu_ticks']-first['java_cpu_ticks'])/100/elapsed if elapsed and first['java_pid']==last['java_pid'] else None,
          'max_threads':max(s['java_threads'] for s in rows)}
        summaries[name].update(host_iowait_pct=cpu['iowait_pct'], host_steal_pct=cpu['steal_pct'],
                               host_busy_plus_steal_pct=cpu['busy_plus_steal_pct'],
                               late_busy_plus_steal_pct=late_cpu['busy_plus_steal_pct'],
                               late_iowait_pct=late_cpu['iowait_pct'], late_steal_pct=late_cpu['steal_pct'])
        summaries[name]['java_rss_first_last_mib']=[first['java_rss_kib']/1024,last['java_rss_kib']/1024]
        if name=='workload':
            medians=[]
            for minute in range(5):
                part=[s['java_rss_kib']/1024 for s in rows if begin+minute*60<=s['epoch']<begin+(minute+1)*60]
                medians.append(statistics.median(part) if part else None)
            summaries[name]['minute_rss_medians_mib']=medians
            summaries[name]['minute_headroom_medians_mib']=[statistics.median(part) if (part := [s['mem_available_kib']/1024 for s in rows if begin+m*60<=s['epoch']<begin+(m+1)*60]) else None for m in range(5)] if not meta['smoke'] else None
    events=[json.loads(line) for line in (root/'http.jsonl').read_text().splitlines()] if (root/'http.jsonl').exists() else []
    launch_path=root/'java-launch-utc.txt'
    if not launch_path.exists():launch_path=root/'guest/java-launch-utc.txt'
    import datetime
    launch=datetime.datetime.fromisoformat(launch_path.read_text().strip().replace('Z','+00:00')).timestamp() if launch_path.exists() else None
    probes=json.loads((root/'probes.json').read_text()) if (root/'probes.json').exists() else []
    ready=next((r.get('completed_epoch',r['epoch']) for r in probes if r.get('status')==200),None)
    startup_note=None
    if meta['smoke'] and launch and ready and launch>ready:
        launch=next(p['epoch'] for p in phases if p['phase']=='startup')
        startup_note='Early smoke reused guest launch file during persistence reopen; uses pre-command phase timestamp instead.'
    result={'variant':meta['variant'],'smoke':meta['smoke'],'actual_mem_mib':samples[0]['mem_total_kib']/1024 if samples else None,
            'startup_to_ready_seconds':ready-launch if ready and launch else None,
            'readiness_uncertainty':'100 ms probe cadence plus request/tunnel duration; sample timestamp is before successful request',
            'phases':summaries,'http':workload.summarize(events) if events else None}
    result['cpu_note']='Busy excludes idle, I/O wait and steal. Legacy samples lack steal: exact busy is null; busy_plus_steal is the corrected upper bound, not an assumed zero steal value.'
    result['startup_note']=startup_note
    from decimal import Decimal
    state=None
    if (root/'db-state.json').exists():
        payload=json.loads((root/'db-state.json').read_text(),parse_float=Decimal)
        if payload.get('status') == 200:
            state=payload['body']
    with (workload.ROOT/'common/src/main/resources/quotes.csv').open() as source:
        fixture_rows=list(csv.DictReader(source))
    fixture=[{'prices':{r['symbol']:r['price'] for r in fixture_rows[i:i+3]}} for i in range(0,len(fixture_rows),3)]
    http_validity,persistence=workload_and_state(meta,events,state,fixture)
    issues=list(coverage['issues'])
    if not http_validity['valid']: issues.append('Incomplete or failed HTTP workload')
    if not persistence['matches']: issues.append('Database does not match required final state')
    if launch is None or ready is None or ready < launch: issues.append('Missing or invalid readiness evidence')
    if (root/'failure.txt').exists(): issues.append('Runner recorded a failure')
    result['sampling_coverage']=coverage
    result['workload_validity']=http_validity
    result['persistence_state']=persistence
    result['validity']={'valid':not issues,'valid_for_comparison':not meta['smoke'] and not issues,'issues':issues}
    (root/'analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--diagnostic',action='store_true');a=p.parse_args()
    result=analyze(a.run)
    if not result['validity']['valid'] and not a.diagnostic: sys.exit(1)
