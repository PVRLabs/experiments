#!/usr/bin/env python3
"""Derive phase evidence without conflating heap, RSS and available RAM."""
import argparse,csv,json,statistics
from pathlib import Path
import workload
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
    samples=[{k:float(v) for k,v in r.items()} for r in csv.DictReader((root/'guest/os.csv').open())]
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
            paging.append({'epoch':right['epoch'],'seconds':dt,'in_mib_s':(right['pswpin_pages']-left['pswpin_pages'])*4096/1048576/dt,'out_mib_s':(right['pswpout_pages']-left['pswpout_pages'])*4096/1048576/dt})
        streak=longest=0
        for r in paging:
            streak=streak+r['seconds'] if max(r['in_mib_s'],r['out_mib_s'])>1 else 0
            longest=max(longest,streak)
        summaries[name]={
          'sample_count':len(rows),'min_available_mib':min(s['mem_available_kib'] for s in rows)/1024,
          'headroom_dips':[{'epoch':s['epoch'],'available_mib':s['mem_available_kib']/1024} for s in rows if s['mem_available_kib']<24576],
          'java_rss_median_mib':statistics.median(s['java_rss_kib'] for s in rows)/1024,
          'java_rss_peak_mib':max(s['java_rss_kib'] for s in rows)/1024,
          'monitor_rss_median_mib':statistics.median(s['monitor_rss_kib'] for s in rows)/1024,
          'max_swap_used_mib':max(s['swap_used_kib'] for s in rows)/1024,
          'swap_in_mib':(last['pswpin_pages']-first['pswpin_pages'])*4096/1048576,
          'swap_out_mib':(last['pswpout_pages']-first['pswpout_pages'])*4096/1048576,
          'longest_paging_above_1_mib_s_seconds':longest,'host_busy_cpu_pct':cpu['busy_pct'],
          'late_cpu_pct':late_cpu['busy_pct'],
          'late_java_rss_median_mib':statistics.median(s['java_rss_kib'] for s in rows if s['epoch']>=max(begin,end-60))/1024,
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
            summaries[name]['minute_headroom_medians_mib']=[statistics.median(s['mem_available_kib']/1024 for s in rows if begin+m*60<=s['epoch']<begin+(m+1)*60) for m in range(5)] if not meta['smoke'] else None
    events=[json.loads(line) for line in (root/'http.jsonl').read_text().splitlines()] if (root/'http.jsonl').exists() else []
    launch_path=root/'java-launch-utc.txt'
    if not launch_path.exists():launch_path=root/'guest/java-launch-utc.txt'
    import datetime
    launch=datetime.datetime.fromisoformat(launch_path.read_text().strip().replace('Z','+00:00')).timestamp() if launch_path.exists() else None
    probes=json.loads((root/'probes.json').read_text())
    ready=next((r.get('completed_epoch',r['epoch']) for r in probes if r.get('status')==200),None)
    startup_note=None
    if meta['smoke'] and launch and ready and launch>ready:
        launch=next(p['epoch'] for p in phases if p['phase']=='startup')
        startup_note='Early smoke reused guest launch file during persistence reopen; uses pre-command phase timestamp instead.'
    result={'variant':meta['variant'],'smoke':meta['smoke'],'actual_mem_mib':samples[0]['mem_total_kib']/1024,
            'startup_to_ready_seconds':ready-launch if ready and launch else None,
            'readiness_uncertainty':'100 ms probe cadence plus request/tunnel duration; sample timestamp is before successful request',
            'phases':summaries,'http':workload.summarize(events) if events else None}
    result['cpu_note']='Busy excludes idle, I/O wait and steal. Legacy samples lack steal: exact busy is null; busy_plus_steal is the corrected upper bound, not an assumed zero steal value.'
    result['startup_note']=startup_note
    if (root/'db-state.json').exists():
        from decimal import Decimal
        data=workload.fixture()
        expected=sum((Decimal(str(price)) for b in data for price in b['prices'].values()),Decimal(0))
        count=sum(e.get('ok') and e['route']=='batch' for e in events)
        expected+=sum((Decimal(str(price)) for b in data[:count] for price in b['prices'].values()),Decimal(0))
        state=json.loads((root/'db-state.json').read_text(),parse_float=Decimal)['body']
        result['persistence_state']={'actual':{k:str(v) if isinstance(v,Decimal) else v for k,v in state.items()},'expected_rows':1170+3*count,'expected_price_sum':str(expected),'matches':state['rows']==1170+3*count and state['priceSum']==expected and state['maxSequence']==389+count}
    (root/'analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();analyze(a.run)
