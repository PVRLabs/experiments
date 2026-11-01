import http.server, json, pathlib, sqlite3, statistics, subprocess, sys, tempfile, threading, time
if len(sys.argv) != 2:
    raise SystemExit('Usage: python3 run.py /path/to/statlite')
root = pathlib.Path(tempfile.mkdtemp(prefix='statlite-rss-spike-'))
binary = str(pathlib.Path(sys.argv[1]).resolve())
print(f'Artifacts: {root}', flush=True)
start = time.monotonic()
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in [f'/metrics/{i}' for i in range(1, 13)]:
            self.send_error(404); return
        t = int(time.monotonic() - start)
        body = json.dumps({'schema':'statlite-metrics/v1','integration':'fixture','status':'UP','started_at':'2026-01-01T00:00:00Z','metrics':{'requests_total':1000 + t * 3,'responses_404_total':t // 30,'responses_4xx_total':t // 20,'responses_5xx_total':t // 60,'request_duration_seconds_total':100 + t * 0.3 + (t // 30) * 0.5}}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 18765), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    for n in (1, 6, 12):
        db = root / f'{n}.sqlite'
        config = f'server:\n  listen: "127.0.0.1:18766"\nstorage:\n  sqlite_path: "{db}"\npolling:\n  interval: "30s"\n  timeout: "5s"\ntargets:\n'
        config += ''.join(f'  - name: "target-{i}"\n    type: "statlite-metrics"\n    url: "http://127.0.0.1:18765/metrics/{i}"\n' for i in range(1, n+1))
        path = root / f'{n}.yaml'; path.write_text(config)
        with open(root / f'{n}.log','w') as log:
            p = subprocess.Popen([binary, '--config', str(path)], stdout=log, stderr=subprocess.STDOUT)
            values=[]; deadline=time.monotonic()+122
            try:
                while time.monotonic() < deadline:
                    if p.poll() is not None: raise RuntimeError(f'StatLite exited {p.returncode}; see {n}.log')
                    out=subprocess.check_output(['ps','-o','rss=','-p',str(p.pid)], text=True).strip()
                    if out and int(out)>0: values.append(int(out))
                    time.sleep(1)
            finally:
                p.terminate(); p.wait(timeout=10)
        with sqlite3.connect(db) as con:
            polls=con.execute('select status, count(*) from polls group by status').fetchall()
            targets=con.execute("select count(distinct target_id) from polls where status='ok'").fetchone()[0]
            metrics=con.execute('select count(*) from metric_samples').fetchone()[0]
        result={'targets':n,'baseline_kib':values[0], 'median_kib':statistics.median(values), 'peak_kib':max(values), 'samples':len(values),'polls':polls,'successful_targets':targets,'metric_samples':metrics}
        print(json.dumps(result), flush=True)
        with open(root/'results.jsonl','a') as f: f.write(json.dumps(result)+'\n')
finally:
    server.shutdown()
