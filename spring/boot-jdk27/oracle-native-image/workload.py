#!/usr/bin/env python3
"""Fixed-rate Market Replay reads; run outside the measured VM through a tunnel."""
import argparse
import concurrent.futures
import datetime
import json
import math
from pathlib import Path
import threading
import time
import urllib.request

SYMBOLS = ['AAPL', 'GOOG', 'NVDA']
FIELDS = {'id', 'fetchedAt', 'cycle', 'sampleIndex', 'marketTime', 'symbol', 'price'}

def validate(rows, latest=False):
    if not isinstance(rows, list) or not rows or len(rows) > 1170:
        raise ValueError('empty/oversized quote payload')
    if latest and [r['symbol'] for r in rows] != SYMBOLS:
        raise ValueError('latest symbol contract')
    ids = []
    for row in rows:
        if set(row) != FIELDS or row['symbol'] not in SYMBOLS:
            raise ValueError('quote fields/symbol')
        if row['cycle'] < 0 or not 0 <= row['sampleIndex'] < 390 or row['price'] <= 0:
            raise ValueError('quote metadata/price')
        expected = (datetime.datetime(2000, 1, 1, 9, 30) + datetime.timedelta(minutes=row['sampleIndex'])).strftime('%H:%M')
        if row['marketTime'] != expected:
            raise ValueError('quote market time')
        datetime.datetime.fromisoformat(row['fetchedAt'].replace('Z', '+00:00'))
        ids.append(row['id'])
    if not latest and ids != sorted(set(ids)):
        raise ValueError('history ordering')
    if any(sum(r['symbol'] == symbol for r in rows) > 390 for symbol in SYMBOLS):
        raise ValueError('history bound')

def run(base, seconds, rate, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    count = round(seconds * rate)
    capacity = threading.BoundedSemaphore(4)
    events = []
    start = time.monotonic()
    def request(index, due):
        path = '/api/quotes/latest' if index % 2 == 0 else '/api/quotes/history'
        sent = time.monotonic()
        event = dict(index=index, path=path, lag_ms=(sent-due)*1000, epoch=time.time())
        try:
            with urllib.request.urlopen(base + path, timeout=5) as r:
                event['status'] = r.status
                validate(json.load(r), latest=index % 2 == 0)
                event['ok'] = r.status == 200
        except Exception as exc:
            event.update(ok=False, error=str(exc))
        finally:
            event['latency_ms'] = (time.monotonic()-sent)*1000
            capacity.release()
        return event
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for i in range(count):
            due = start + i/rate
            time.sleep(max(0, due-time.monotonic()))
            if time.monotonic()-due > 1/rate or not capacity.acquire(blocking=False):
                events.append(dict(index=i, ok=False, error='missed offered slot'))
            else:
                futures.append(executor.submit(request, i, due))
        events.extend(f.result() for f in futures)
        time.sleep(max(0, start+seconds-time.monotonic()))
    elapsed = time.monotonic()-start
    events.sort(key=lambda e: e['index'])
    (output / 'requests.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    good = [e for e in events if e['ok']]
    values = sorted(e['latency_ms'] for e in good)
    def percentile(p):
        return values[math.ceil(len(values)*p)-1] if values else None
    summary = dict(offered=count, successful=len(good), errors=count-len(good),
        duration_seconds=seconds, actual_seconds=elapsed, offered_rps=rate,
        successful_rps=len(good)/elapsed, p50_ms=percentile(.5), p95_ms=percentile(.95),
        max_dispatch_lag_ms=max((e.get('lag_ms', 0) for e in events), default=0),
        concurrency_limit=4, retries=0)
    summary['routes'] = {}
    for path in ['/api/quotes/latest', '/api/quotes/history']:
        route = sorted(e['latency_ms'] for e in good if e['path'] == path)
        summary['routes'][path] = dict(successful=len(route), p50_ms=route[math.ceil(len(route)*.5)-1] if route else None,
            p95_ms=route[math.ceil(len(route)*.95)-1] if route else None)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))
    if summary['errors']:
        raise RuntimeError('workload errors; preserve raw requests')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', default='http://127.0.0.1:18080')
    p.add_argument('--seconds', type=float, default=3)
    p.add_argument('--rate', type=float, default=5)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    if a.seconds <= 0 or a.rate <= 0:
        p.error('seconds and rate must be positive')
    run(a.base.rstrip('/'), a.seconds, a.rate, a.output)
