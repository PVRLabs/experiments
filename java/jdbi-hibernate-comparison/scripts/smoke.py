#!/usr/bin/env python3
"""Short functional packaged launch checks. No measured workloads or timings."""
from benchmark import verify_state
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ['-Xms16m', '-Xmx80m', '-Xss256k', '-XX:+UseSerialGC', '-XX:TieredStopAtLevel=1', '-XX:ReservedCodeCacheSize=32m', '-XX:+UseCompactObjectHeaders']

def get(path, method='GET', port=8080):
    with urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}{path}', method=method), timeout=2) as response:
        return response.read().decode()

def wait(path, process, port=8080):
    for _ in range(300):
        if process.poll() is not None: raise RuntimeError('Application exited; inspect preparation logs')
        try: return get(path, port=port)
        except Exception: time.sleep(.1)
    raise RuntimeError('Readiness timeout')

def stop(process):
    process.terminate()
    try: process.wait(timeout=15)
    except subprocess.TimeoutExpired: process.kill(); process.wait()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--variants",nargs="+",choices=["spring-jpa","coilbase-jdbi","coilbase-hibernate"],default=["spring-jpa","coilbase-jdbi","coilbase-hibernate"]);args=parser.parse_args()
    schemas=[]
    with tempfile.TemporaryDirectory(prefix='stargazer-smoke-') as temp:
        work=Path(temp)
        with (work/'fixture.log').open('w') as fixture_log:
            fixture=subprocess.Popen(['python3',str(ROOT/'fixture/server.py')],stdout=fixture_log,stderr=fixture_log)
            try:
                wait('/healthz',fixture,18080)
                for variant in args.variants:
                    folder=work/variant;folder.mkdir()
                    jar=ROOT/variant/'target'/('extracted/stars-0.0.1-SNAPSHOT.jar' if variant=='spring-jpa' else f'{variant}-1.0-SNAPSHOT.jar')
                    env=dict(os.environ,TZ='UTC',PORT='8080',DB_URL=f'jdbc:h2:file:{folder}/db',SPRING_DATASOURCE_URL=f'jdbc:h2:file:{folder}/db',APP_GITHUB_API_BASE_URL='http://127.0.0.1:18080',APP_GITHUB_INITIAL_DELAY_MS='3600000')
                    get('/clear-error','POST',18080)
                    for restart in range(2):
                        with (folder/f'app-{restart}.log').open('w') as log:
                            app=subprocess.Popen(['java',*FLAGS,'-jar',str(jar)],cwd=folder,env=env,stdout=log,stderr=log)
                            try:
                                html=wait('/',app)
                                if restart==0:
                                    html=get('/refresh','POST')
                                    for count in ('142','87','63'): assert count in html,(variant,count)
                                    get('/refresh','POST')
                                    get('/advance','POST',18080)
                                    get('/refresh','POST')
                                    get('/error/PVRLabs/statlite','POST',18080)
                                    get('/advance','POST',18080)
                                    get('/refresh','POST')
                                    get('/clear-error','POST',18080)
                                else:
                                    for count in ('143','89','65'): assert count in html,(variant,count)
                                assert 'star-chart' in html
                                if variant=='coilbase-hibernate':
                                    assert json.loads(get('/persistence-context')) == {'coilbase_repository_context_initialized': False}
                                assert 'UP' in get('/actuator/health' if variant=='spring-jpa' else '/ready')
                                if restart==1: get('/refresh','POST')  # Recover the deliberately failed repository before acceptance verification.
                            except Exception:
                                print(locals().get("html", "")); print((folder/f'app-{restart}.log').read_text());raise
                            finally:stop(app)

                    h2=ROOT/'coilbase-jdbi/target/lib/h2-2.4.240.jar'
                    sql="select case when (select count(*) from projects)=3 and (select count(*) from star_history)=9 and (select current_stars from projects where repo_name='PVRLabs/statlite')=144 and (select current_stars from projects where repo_name='PVRLabs/aibadger')=89 and (select count(*) from information_schema.table_constraints where table_schema='PUBLIC' and constraint_type='PRIMARY KEY')=2 and (select count(*) from information_schema.table_constraints where table_schema='PUBLIC' and constraint_type='UNIQUE')=1 and (select count(*) from information_schema.table_constraints where table_schema='PUBLIC' and constraint_type='FOREIGN KEY')=1 then 'CONTRACT_PASS' else 'CONTRACT_FAIL' end"
                    check=subprocess.check_output(['java','-cp',str(h2),'org.h2.tools.Shell','-url',f'jdbc:h2:file:{folder}/db','-user','sa','-password','','-sql',sql],text=True)
                    assert 'CONTRACT_PASS' in check,check
                    state=json.loads(subprocess.check_output(['java','-cp',str(ROOT/'coilbase-jdbi/target/lib/*'),'pvrlabs.stargazer.StateDump',f'jdbc:h2:file:{folder}/db;IFEXISTS=TRUE'],text=True))
                    assert verify_state(state,[0,1,2])==[],state
                    schema=subprocess.check_output(['java','-cp',str(h2),'org.h2.tools.Shell','-url',f'jdbc:h2:file:{folder}/db','-user','sa','-password','','-sql',"select table_name,column_name,data_type,is_nullable,character_maximum_length,datetime_precision from information_schema.columns where table_schema='PUBLIC' order by table_name,column_name"],text=True)
                    schemas.append('\n'.join(schema.splitlines()[:-1]))
                    fixture_log.flush()
                    fixture_evidence=(work/'fixture.log').read_text()
                    assert ' 304' in fixture_evidence and ' 500' in fixture_evidence,'Missing ETag or injected-error evidence'
                    # Fresh fixture state for the next application, including ETag generation.
                    get('/reset','POST',18080)
                    print(variant+': shared HTTP/DB contract, failure isolation and restart PASS')
                assert len(set(schemas))==1,'Schema column metadata differs between variants'
            finally:stop(fixture)
if __name__=='__main__':main()
