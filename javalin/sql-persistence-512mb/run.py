#!/usr/bin/env python3
"""512 MiB execution; preparation is separate, monitored runs pause for inspection."""
import argparse
import datetime
import http.client
import json
from pathlib import Path
import shlex
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT
sys.path.insert(0, str(ROOT))
import workload
import smoke


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', choices=['javalin-jdbi3', 'javalin-mybatis', 'javalin-jooq'])
    parser.add_argument('--vm', default='javalin-512')
    parser.add_argument('--release', required=True)
    parser.add_argument('--preparation', '--manifest', dest='preparation', type=Path,
                        default=ROOT/'results/preparation/preparation-compact-002.json')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--monitored', action='store_true')
    parser.add_argument('--selection', help='Operator selection rationale; required for measured monitored run')
    parser.add_argument('--app-port', type=int, default=18080)
    parser.add_argument('--monitor-port', type=int, default=19090)
    parser.add_argument('--baseline', type=float)
    parser.add_argument('--idle', type=float)
    parser.add_argument('--recovery', type=float)
    parser.add_argument('--finish', type=Path)
    args = parser.parse_args()
    if args.monitored and not args.smoke and not args.selection and not args.finish:
        parser.error('Record explicit operator selection with --selection')
    def vm(*cmd):
        return subprocess.check_output([str(REPO/'tools/vm.sh'), 'exec', args.vm, *cmd], text=True)
    def guest(action, run):
        return vm('bash', args.release+'/guest.sh', action, args.variant, run, args.release)
    def analyze_collected(directory,run):
        with (directory/'analysis-output.txt').open('w') as output:
            result=subprocess.run([sys.executable,str(ROOT/'analyze.py'),str(directory)],stdout=output)
        if result.returncode:
            guest('diagnostics',run)
            for name in ['processes-diagnostic.txt','kernel-diagnostic.txt','memory-diagnostic.txt']:
                (directory/'guest'/name).write_text(vm('cat',run+'/'+name))
            result.check_returncode()
    def fetch(path, monitor=False):
        connection = http.client.HTTPConnection('127.0.0.1', args.monitor_port if monitor else args.app_port, timeout=2)
        try:
            return workload.request(connection, 'GET', path)
        finally:
            connection.close()
    if args.finish:
        meta = json.loads((args.finish/'run.json').read_text())
        assert meta['variant'] == args.variant and meta['release'] == args.release and meta['vm'] == args.vm
        guest('stop', meta['guest'])
        subprocess.check_call([str(REPO/'tools/vm.sh'), 'get', args.vm, meta['guest'], str(args.finish/'guest')])
        analyze_collected(args.finish,meta['guest'])
        return
    ident = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+args.variant
    local = ROOT/'results'/('preparation' if args.smoke else 'measured')/ident
    local.mkdir(parents=True, exist_ok=False)
    run = '/opt/sql512/'+('smoke-' if args.smoke else 'run-')+ident
    preparation=json.loads(args.preparation.read_text())
    assert json.loads(vm('cat',args.release+'/preparation.json')) == preparation, 'Preparation record differs from deployment'
    release_quoted=shlex.quote(args.release)
    observed=vm('bash','-c',
        'set -eu; test "$(getconf _NPROCESSORS_ONLN)" = 1; '
        'test "$(wc -l < /proc/swaps)" = 1; '
        'awk \'/^MemTotal:/{if ($2<450000 || $2>524288) exit 1}\' /proc/meminfo; '
        '! pgrep -x java; ! pgrep -x statlite; '
        'cd '+release_quoted+'; sha256sum -c SHA256SUMS >/dev/null; '
        'getconf _NPROCESSORS_ONLN; '
        'awk \'/^MemTotal:/{print $2} /^SwapTotal:/{print $2}\' /proc/meminfo; '
        'cat /etc/alpine-release; uname -r; cat /proc/sys/kernel/random/boot_id; '
        'cut -d " " -f 1 /proc/uptime; java -version 2>&1').splitlines()
    runtime=dict(cpus=int(observed[0]),mem_total_kib=int(observed[1]),swap_total_kib=int(observed[2]),
                 os='Alpine '+observed[3],kernel=observed[4],boot_id=observed[5],
                 uptime_seconds=float(observed[6]),jdk='\n'.join(observed[7:]),
                 jvm_flags=preparation['jvm_flags'])
    phases = []
    def phase(name, duration=0):
        phases.append({'phase':name, 'epoch':time.time(), 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        (local/'phases.json').write_text(json.dumps(phases, indent=2))
        print(name, flush=True)
        if duration:
            time.sleep(duration)
    durations = {name:getattr(args,name) if getattr(args,name) is not None else (6 if args.smoke else 30) for name in ['baseline','idle','recovery']}
    if args.smoke and args.monitored and args.idle is None:
        durations['idle'] = 35  # Allow an application target poll in preparation.
    meta = dict(guest=run, variant=args.variant, smoke=args.smoke, monitored=args.monitored, selection=args.selection,
                vm=args.vm, release=args.release, durations=durations, app_port=args.app_port, monitor_port=args.monitor_port,
                preparation=os.path.relpath(args.preparation.resolve(),local.resolve()),runtime=runtime)
    (local/'run.json').write_text(json.dumps(meta, indent=2))
    print(local, flush=True)
    keep = False
    initialized = False
    try:
        guest('init', run)
        initialized = True
        phase('baseline', durations['baseline'])
        if args.monitored:
            guest('monitor',run)
            phase('monitor-only',90)
            status, body = fetch('/api/series?target=statlite-self&range=1h', True)
            assert status == 200 and len(body.get('points',[])) >= 2
            (local/'monitor-only-self-series.json').write_text(json.dumps(body,indent=2))
        phase('startup')
        guest('java',run)
        probes=[]
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            probe={'epoch':time.time()}
            try:
                status,body=fetch('/ready')
                probe.update(status=status,body=body,completed_epoch=time.time())
                probes.append(probe)
                if status==200 and body=={'status':'UP'}:
                    break
            except Exception as error:
                probe['error']=str(error)
                probes.append(probe)
            time.sleep(.1)
        else:
            raise RuntimeError('Readiness timeout')
        (local/'probes.json').write_text(json.dumps(probes,indent=2))
        (local/'java-launch-utc.txt').write_text(vm('cat',run+'/java-launch-utc.txt'))
        if not args.smoke:
            guest('slow',run)
        phase('idle',durations['idle'])
        phase('workload')
        events=workload.run(args.app_port,local/'http.jsonl',15 if args.smoke else 1500)
        (local/'http-summary.json').write_text(json.dumps(workload.summarize(events),indent=2))
        phase('recovery',durations['recovery'])
        phase('measurement-cutoff')
        guest('cutoff',run)
        status,state=fetch('/inspection/state')
        assert status==200
        (local/'db-state.json').write_text(json.dumps({'status':status,'body':state},indent=2))
        from decimal import Decimal
        assert state['rows']==(1179 if args.smoke else 2070)
        assert state['maxSequence']==(392 if args.smoke else 689)
        if not args.smoke:
            assert Decimal(str(state['priceSum']))==Decimal('630374.22')
        assert len(events)==(15 if args.smoke else 1500), 'Incomplete workload; preserve this run'
        assert all(e['ok'] for e in events), 'Workload errors; preserve this run'
        if args.smoke:
            smoke.check(args.variant,local,port=args.app_port)
            before=fetch('/inspection/state')[1]
            guest('stop-java',run)
            guest('java',run)
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                try:
                    if fetch('/ready')[0]==200:
                        break
                except Exception:
                    pass
                time.sleep(.1)
            assert fetch('/inspection/state')[1]==before
            (local/'persistence.json').write_text(json.dumps(before,indent=2))
        if args.monitored:
            for path,name in [('/api/summary','dashboard-summary'),('/api/latest','dashboard-latest')]:
                status,body=fetch(path,True)
                assert status==200
                (local/(name+'.json')).write_text(json.dumps(body,indent=2))
                if name == 'dashboard-summary':
                    target = next(t for t in body['targets'] if t['metadata']['name'] == args.variant)
                    assert target['latest']['status'] == 'ok', 'Application monitoring sample missing'
        if args.monitored and not args.smoke:
            keep=True
            print('INSPECTION REQUIRED: monitoring remains running. Verify tunnel URL and inspect the last hour; use --finish only after operator completion/skip.',flush=True)
    except Exception as error:
        (local/'failure.txt').write_text(repr(error)+'\n')
        if initialized:
            try:
                guest('diagnostics',run)
            except Exception as diagnostic_error:
                (local/'diagnostic-failure.txt').write_text(str(diagnostic_error))
        raise
    finally:
        if initialized and not keep:
            guest('stop',run)
            subprocess.check_call([str(REPO/'tools/vm.sh'),'get',args.vm,run,str(local/'guest')])
            if (local/'failure.txt').exists():
                with (local/'analysis-output.txt').open('w') as output:
                    subprocess.run([sys.executable,str(ROOT/'analyze.py'),str(local),'--diagnostic'],stdout=output,check=False)
    if not keep:
        analyze_collected(local,run)
        print('COMPLETE',local,flush=True)


if __name__=='__main__':
    main()
