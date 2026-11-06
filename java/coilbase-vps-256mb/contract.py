"""Shared external Alpine preparation checks after the 15-request smoke workload."""
import http.client,json
import workload

def check(variant,local,port):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    def call(method,path,body=None):return workload.request(conn,method,path,body)
    try:
        status,state=call('GET','/inspection/state');assert status==200 and state['rows']==1179,state
        for symbol in ['AAPL','GOOG','NVDA']:
            status,rows=call('GET',f'/api/quotes/history?symbol={symbol}&limit=390')
            assert status==200 and len(rows)==390 and rows[-1]['sequence']==392
        for path in ['/api/quotes/history?symbol=INVALID','/api/quotes/history?symbol=AAPL&limit=0','/api/quotes/history?symbol=AAPL&limit=391']:
            assert call('GET',path)[0]==400,path
        base=dict(workload.fixture()[0],sequence=393,cycle=1,sampleIndex=0)
        for body in [{},dict(base,prices={'AAPL':1}),dict(base,sequence=None)]:
            assert call('POST','/api/quotes/batches',body)[0]==400,body
        assert call('POST','/api/quotes/batches',dict(base,sequence=390))[0]==409
        assert call('GET','/inspection/state')[1]==state
        if variant=='coilbase':
            status,metrics=call('GET','/statlite/metrics');assert status==200 and metrics['metrics']['runtime_heap_used_bytes']>0
            status,health=call('GET','/inspection/db');assert status==200 and health['healthy'],health
        else:
            status,health=call('GET','/actuator/health');assert status==200 and health['components']['db']['status']=='UP',health
        (local/'contract-checks.json').write_text(json.dumps({'state':state,'health':health,'passed':True},indent=2)+'\n')
    finally:conn.close()
