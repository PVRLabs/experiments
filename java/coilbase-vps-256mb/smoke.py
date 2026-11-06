#!/usr/bin/env python3
"""Packaged-app preparation only: HTTP contract, metrics, reopen and partial rollback."""
import argparse, json, os, subprocess, time, urllib.error, urllib.request
from pathlib import Path
import workload

ROOT=Path(__file__).resolve().parent

def check(variant,bundle,output,port):
    output.mkdir(parents=True,exist_ok=False)
    db=output/'db';db.mkdir()
    jar=bundle/('coilbase/app.jar' if variant=='coilbase' else 'spring/spring-app-1.0.jar')
    env=dict(os.environ,PORT=str(port))
    command=['java','-Xms16m','-Xmx80m','-XX:+UseSerialGC','-Xss512k',f'-Drun.dir={db}','-jar',str(jar)]
    if variant=='spring':command.append(f'--server.port={port}')
    def call(method,path,body=None,raw=None):
        data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=data,method=method,headers={'Content-Type':'application/json'})
        try:r=urllib.request.urlopen(req,timeout=5)
        except urllib.error.HTTPError as e:r=e
        with r:return r.status,json.loads(r.read())
    def start(label):
        log=(output/(label+'.log')).open('w')
        p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
        log.close()
        try:
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if p.poll() is not None:raise AssertionError(f'{variant} exited; see {output}')
                try:
                    if call('GET','/ready')[0]==200:return p
                except (OSError,ValueError):pass
                time.sleep(.1)
            raise AssertionError('readiness timeout')
        except BaseException:
            stop(p);raise
    def stop(p):
        p.terminate()
        try:p.wait(timeout=15)
        except subprocess.TimeoutExpired:p.kill();p.wait();raise AssertionError('unclean shutdown')
    p=start('initial')
    try:
        initial=call('GET','/inspection/state')[1];assert initial['rows']==1170,initial
        events=workload.run(port,output/'http.jsonl',15)
        assert all(e['ok'] for e in events),events
        state=call('GET','/inspection/state')[1];assert state['rows']==1179 and state['maxSequence']==392,state
        for symbol in ['AAPL','GOOG','NVDA']:
            code,rows=call('GET',f'/api/quotes/history?symbol={symbol}&limit=390');assert code==200 and len(rows)==390
        for path in ['/api/quotes/history','/api/quotes/history?symbol=INVALID','/api/quotes/history?symbol=AAPL&limit=abc','/api/quotes/history?symbol=AAPL&limit=0','/api/quotes/history?symbol=AAPL&limit=391']:
            assert call('GET',path)[0]==400,path
        base=dict(workload.fixture()[0],sequence=393,cycle=1,sampleIndex=0)
        for body in [{},dict(base,prices={'AAPL':1}),dict(base,prices={'AAPL':None,'GOOG':1,'NVDA':1}),dict(base,sequence=None),dict(base,marketTime='99:99')]:
            assert call('POST','/api/quotes/batches',body)[0]==400,body
        for raw in [b'',b'null',b'{broken']:
            assert call('POST','/api/quotes/batches',raw=raw)[0]==400,raw
        assert call('POST','/api/quotes/batches',dict(base,sequence=390))[0]==409
        assert call('GET','/inspection/state')[1]==state
        path='/statlite/metrics' if variant=='coilbase' else '/actuator/health'
        code,metrics=call('GET',path);assert code==200
        if variant=='coilbase':assert metrics['metrics']['runtime_heap_used_bytes']>0
        else:assert metrics['components']['db']['status']=='UP'
    finally:stop(p)
    # Preload a conflict on the LAST symbol. The API must roll back its earlier two inserts.
    h2=next((bundle/('coilbase/lib' if variant=='coilbase' else 'spring/lib')).glob('h2-*.jar'))
    sql="INSERT INTO quotes(batch_seq,cycle,sample_index,market_time,symbol,price) VALUES(900,1,0,'09:30','NVDA',1)"
    result=subprocess.run(['java','-cp',str(h2),'org.h2.tools.Shell','-url',f'jdbc:h2:file:{db}/quotes','-user','sa','-password','','-sql',sql],check=True,capture_output=True,text=True)
    assert 'Error' not in result.stdout,result.stdout
    p=start('reopened')
    try:
        before=call('GET','/inspection/state')[1]
        assert before['rows']==state['rows']+1 and before['maxSequence']==900,before
        assert call('POST','/api/quotes/batches',dict(base,sequence=900))[0]==409
        assert call('GET','/inspection/state')[1]==before,'partial transaction committed'
        assert call('POST','/api/quotes/batches',base)[0]==201,'failed transaction poisoned next write'
        assert call('GET','/inspection/state')[1]['rows']==before['rows']+3
    finally:stop(p)
    report={'variant':variant,'preparation_only':True,'initial':initial,'after_15_requests':state,'partial_rollback':True,'reopening':True,'recovery_write':True,'http':workload.summarize(events),'monitoring':metrics,'command':command}
    (output/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(variant+': PASS')
    return state

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bundle',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--port',type=int,default=18088)
    args=parser.parse_args();states=[check(v,args.bundle.resolve(),args.output.resolve()/v,args.port) for v in ['coilbase','spring']]
    assert states[0]==states[1],states
