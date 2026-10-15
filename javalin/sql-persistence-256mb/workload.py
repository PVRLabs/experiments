#!/usr/bin/env python3
"""External fixed-rate HTTP/1.1 load; no retries, at most four in flight."""
import argparse, concurrent.futures, csv, http.client, json, math, queue, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def fixture():
    rows = list(csv.DictReader((ROOT / 'common/src/main/resources/quotes.csv').open()))
    return [{'marketTime': rows[i]['market_time'], 'prices': {r['symbol']: float(r['price']) for r in rows[i:i+3]}} for i in range(0, len(rows), 3)]

def request(conn, method, path, body=None):
    conn.request(method, path, json.dumps(body) if body is not None else None,
                 {'Content-Type': 'application/json'} if body is not None else {})
    response = conn.getresponse()
    payload = response.read()
    return response.status, json.loads(payload)

def valid(kind, body, index, data):
    if kind == 'batch': return body == {'sequence': 390+index//5}
    expected = 3 if kind == 'latest' else 60
    if not isinstance(body, list) or len(body) != expected: return False
    if kind == 'latest' and [r.get('symbol') for r in body] != ['AAPL','GOOG','NVDA']: return False
    if kind == 'history':
        symbol = ['AAPL','GOOG','NVDA'][index%5-1]
        if any(r.get('symbol') != symbol for r in body): return False
        sequences=[r['sequence'] for r in body]
        if sequences != list(range(sequences[0],sequences[0]+60)): return False
    for r in body:
        if set(r) != {'sequence','cycle','sampleIndex','marketTime','symbol','price'}:return False
        sample=r['sequence'] if r['sequence']<390 else r['sequence']-390
        if not 0<=sample<390 or r['sampleIndex']!=sample or r['cycle']!=(0 if r['sequence']<390 else 1):return False
        if r['marketTime']!=data[sample]['marketTime'] or r['price']!=data[sample]['prices'].get(r['symbol']):return False
    return True

def run(port, output, count=1500):
    data=fixture(); pool=queue.Queue(); events=[]
    for _ in range(4): pool.put(http.client.HTTPConnection('127.0.0.1', port, timeout=2))
    start=time.monotonic(); wall=time.time()
    def send(i, scheduled, conn):
        dispatched=time.monotonic(); event={'index':i,'scheduled_epoch':wall+i*.2,'lag_ms':(dispatched-scheduled)*1000}
        slot=i%5; kind='latest' if slot==0 else 'batch' if slot==4 else 'history'
        method='POST' if slot==4 else 'GET'
        path='/api/quotes/latest' if slot==0 else '/api/quotes/batches' if slot==4 else '/api/quotes/history?symbol='+['AAPL','GOOG','NVDA'][slot-1]+'&limit=60'
        body=None if slot!=4 else dict(data[i//5],sequence=390+i//5,cycle=1,sampleIndex=i//5)
        event.update(route=kind, dispatched_epoch=time.time())
        try:
            status,payload=request(conn,method,path,body)
            event.update(status=status,ok=status==(201 if slot==4 else 200) and valid(kind,payload,i,data))
        except Exception as e:
            event.update(status=0,ok=False,error=str(e));conn.close()
        event.update(latency_ms=(time.monotonic()-dispatched)*1000,completed_epoch=time.time())
        pool.put(conn); return event
    futures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for i in range(count):
            due=start+i*.2
            delay=due-time.monotonic()
            if delay>0: time.sleep(delay)
            if time.monotonic()-due>.2 or pool.empty():
                events.append({'index':i,'route':'miss','scheduled_epoch':wall+i*.2,'ok':False,'error':'late slot or four outstanding'})
                continue
            futures.append(executor.submit(send,i,due,pool.get_nowait()))
        for future in futures: events.append(future.result())
    while not pool.empty(): pool.get().close()
    events.sort(key=lambda e:e['index'])
    Path(output).write_text(''.join(json.dumps(e)+'\n' for e in events))
    return events

def summarize(events):
    def stats(rows):
        values=sorted(r['latency_ms'] for r in rows if 'latency_ms' in r)
        return {'count':len(rows),'errors':sum(not r['ok'] for r in rows),
                'p50_ms':values[math.ceil(len(values)*.5)-1] if values else None,
                'p95_ms':values[math.ceil(len(values)*.95)-1] if values else None,
                'max_ms':max(values) if values else None}
    return {'overall':stats(events),'routes':{kind:stats([e for e in events if e['route']==kind]) for kind in ['latest','history','batch']},
            'minutes':{str(m+1):stats([e for e in events if m*300<=e['index']<(m+1)*300]) for m in range(5)},
            'max_dispatch_lag_ms':max((e.get('lag_ms',0) for e in events),default=0)}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18080);p.add_argument('--output',required=True);p.add_argument('--count',type=int,default=1500)
    a=p.parse_args();events=run(a.port,a.output,a.count);print(json.dumps(summarize(events),indent=2))
