#!/usr/bin/env python3
"""Run measured phases through shared helpers; stop at operator inspection."""
import argparse, datetime, http.client, json, subprocess, time
from pathlib import Path
import workload
ROOT=Path(__file__).resolve().parent
REPO=ROOT
VM='javalin-256'; RELEASE='/opt/vps256/release-003-extracted'
def vm(*args):
    return subprocess.check_output([str(REPO/'tools/vm.sh'),'exec',VM,*args],text=True)
def guest(action,variant,run,release=RELEASE):
    return vm('bash',release+'/guest.sh',action,variant,run,release)
def fetch(port,path,timeout=2):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=timeout)
    try:return workload.request(c,'GET',path)
    finally:c.close()
def main():
    global VM
    p=argparse.ArgumentParser();p.add_argument('variant',choices=['javalin','spring']);p.add_argument('--smoke',action='store_true');p.add_argument('--finish',type=Path)
    p.add_argument('--vm',default=VM);p.add_argument('--app-port',type=int,default=18080);p.add_argument('--monitor-port',type=int,default=19090)
    a=p.parse_args()
    VM=a.vm
    app_port=a.app_port;monitor_port=a.monitor_port
    if a.finish:
        meta=json.loads((a.finish/'run.json').read_text())
        VM=meta.get('vm',VM)
        if meta['variant']!=a.variant:raise ValueError('Run variant does not match')
        print(guest('stop',a.variant,meta['guest'],meta['release']))
        subprocess.check_call([str(REPO/'tools/vm.sh'),'get',VM,meta['guest'],str(a.finish/'guest')]);return
    ident=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+a.variant
    local=ROOT/'results'/('preparation/smoke-'+ident if a.smoke else 'run-'+ident)
    local.mkdir(parents=True)
    run='/opt/vps256/'+('smoke-' if a.smoke else 'run-')+ident
    (local/'run.json').write_text(json.dumps({'guest':run,'variant':a.variant,'smoke':a.smoke,'release':RELEASE,'vm':VM,'app_port':app_port,'monitor_port':monitor_port},indent=2))
    import shutil
    manifest=ROOT/'evidence/inputs.json'
    shutil.copyfile(manifest,local/'input-manifest.json')
    timeline=[]
    def phase(name,duration=0):
        event={'phase':name,'epoch':time.time(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monotonic':time.monotonic()}
        timeline.append(event);(local/'phases.json').write_text(json.dumps(timeline,indent=2));print(event,flush=True)
        if duration:time.sleep(duration)
    print(guest('init',a.variant,run),flush=True)
    (local/'guest-preflight.txt').write_text(vm('bash','-c','set -e; date -u; cat /proc/meminfo /proc/swaps; cat /proc/sys/vm/swappiness; rc-status -a; ps -eo pid,comm,rss,args; cd '+RELEASE+'; sha256sum -c SHA256SUMS'))
    phase('baseline',6 if a.smoke else 60)
    print(guest('monitor',a.variant,run),flush=True)
    phase('monitor-only',65 if a.smoke else 90)
    status,summary=fetch(monitor_port,'/api/summary')
    (local/'monitor-only-summary.json').write_text(json.dumps(summary,indent=2))
    if status!=200:raise RuntimeError('Monitor unavailable')
    self_target=next(t for t in summary['targets'] if t['metadata']['name']=='statlite-self')
    if self_target['latest']['status']!='ok':raise RuntimeError('Self target did not collect')
    status,series=fetch(monitor_port,'/api/series?target=statlite-self&range=1h')
    (local/'monitor-only-self-series.json').write_text(json.dumps(series,indent=2))
    if status!=200 or len(series.get('points',[]))<2:raise RuntimeError('Missing two self-target samples')
    phase('startup');print(guest('java',a.variant,run),flush=True)
    probes=[];deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        event={'epoch':time.time()}
        try:
            status,body=fetch(app_port,'/ready',1);event.update(status=status,body=body,completed_epoch=time.time())
            probes.append(event)
            if status==200 and body=={'status':'UP'}:break
        except Exception as e: event['error']=str(e);probes.append(event)
        time.sleep(.1)
    else:
        (local/'probes.json').write_text(json.dumps(probes,indent=2));phase('startup-failed');guest('cutoff',a.variant,run);return
    (local/'probes.json').write_text(json.dumps(probes,indent=2))
    (local/'java-launch-utc.txt').write_text(vm('cat',run+'/java-launch-utc.txt'))
    print(guest('slow',a.variant,run),flush=True)
    phase('idle',8 if a.smoke else 180)
    phase('workload')
    events=workload.run(app_port,local/'http.jsonl',15 if a.smoke else 1500)
    (local/'http-summary.json').write_text(json.dumps(workload.summarize(events),indent=2))
    phase('recovery',35 if a.smoke else 120)
    phase('measurement-cutoff');print(guest('cutoff',a.variant,run),flush=True)
    for path,name,port in [('/inspection/state','db-state',app_port),('/api/summary','dashboard-summary',monitor_port),('/api/latest','dashboard-latest',monitor_port),('/statlite/metrics' if a.variant=='javalin' else '/actuator/health','app-metrics-health',app_port)]:
        status,body=fetch(port,path);(local/(name+'.json')).write_text(json.dumps({'status':status,'body':body},indent=2))
    print('INSPECTION READY:',local,run,flush=True)
    if a.smoke:
        import smoke
        smoke.check(a.variant,local,port=app_port)
        before=fetch(app_port,'/inspection/state')[1]
        print(guest('stop-java',a.variant,run));print(guest('java',a.variant,run))
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            try:
                if fetch(app_port,'/ready')[0]==200:break
            except Exception:pass
            time.sleep(.1)
        assert fetch(app_port,'/inspection/state')[1]==before, 'Persistence differs after reopen'
        (local/'persistence.json').write_text(json.dumps(before,indent=2))
        print(guest('stop',a.variant,run));subprocess.check_call([str(REPO/'tools/vm.sh'),'get',VM,run,str(local/'guest')])
if __name__=='__main__':main()
