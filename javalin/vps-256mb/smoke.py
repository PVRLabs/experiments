"""Preparation assertions for semantics, invalid writes, atomicity and metrics."""
import http.client,json
import workload
def check(variant,local,port=18080):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
    def call(method,path,body=None):return workload.request(c,method,path,body)
    status,state=call('GET','/inspection/state');assert status==200 and state['rows']==1179
    results={'initial':state}
    data=workload.fixture()
    latest=call('GET','/api/quotes/latest')[1]
    assert workload.valid('latest',latest,0,data)
    results['latest']=latest
    for symbol in ['AAPL','GOOG','NVDA']:
        status,rows=call('GET','/api/quotes/history?symbol='+symbol+'&limit=390')
        assert status==200 and len(rows)==390 and rows[-1]['sequence']==392
        status,recent=call('GET','/api/quotes/history?symbol='+symbol+'&limit=60')
        assert status==200 and workload.valid('history',recent,1+['AAPL','GOOG','NVDA'].index(symbol),data)
    for path in ['/api/quotes/history?symbol=INVALID&limit=60','/api/quotes/history?symbol=AAPL&limit=391','/api/quotes/history?symbol=AAPL&limit=0']:
        assert call('GET',path)[0]==400
    base=dict(workload.fixture()[0],sequence=393,cycle=1,sampleIndex=3)
    for change in [dict(prices={'AAPL':1}),dict(prices={'AAPL':-1,'GOOG':1,'NVDA':1}),dict(sampleIndex=390),dict(sequence=None),dict(marketTime='99:99')]:
        assert call('POST','/api/quotes/batches',dict(base,**change))[0]==400
        assert call('GET','/inspection/state')[1]==state
    duplicate=dict(base,sequence=390,sampleIndex=0)
    assert call('POST','/api/quotes/batches',duplicate)[0]==409
    assert call('GET','/inspection/state')[1]==state
    if variant=='javalin':
        status,before=call('GET','/statlite/metrics');assert status==200
        for _ in range(3):assert call('GET','/ready')[0]==200
        after=call('GET','/statlite/metrics')[1]
        assert before['metrics']['requests_total']==after['metrics']['requests_total']
        assert after['metrics']['runtime_heap_used_bytes']>0
        results['adapter']=after
    else:
        status,health=call('GET','/actuator/health');assert status==200 and health['components']['db']['status']=='UP';results['health']=health
    c.close();(local/'contract-checks.json').write_text(json.dumps(results,indent=2))
