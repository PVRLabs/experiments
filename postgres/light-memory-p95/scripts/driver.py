#!/usr/bin/python3
"""Four persistent clients, idle and measured sampling; run as root in the guest."""
import argparse
import csv
import os
import random
import subprocess
import threading
import time
from pathlib import Path
import psycopg2

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--idle', type=float, default=5)
parser.add_argument('--warmup', type=float, default=20)
parser.add_argument('--duration', type=float, default=50)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
connection = dict(host='127.0.0.1', dbname='experiment', user='experiment', password='experiment', connect_timeout=10)
conns = [psycopg2.connect(**connection) for _ in range(4)]
for conn in conns:
    conn.autocommit = True
stop = threading.Event()
phase = 'idle'
rows = []
errors = []
queries = {
    'point': 'SELECT payload FROM items WHERE id = %s',
    'range': 'SELECT count(*) FROM items WHERE id BETWEEN %s AND %s',
    'aggregate': 'SELECT sum(bucket) FROM (SELECT bucket FROM items WHERE id <= 12000 ORDER BY payload OFFSET 4000 LIMIT 1) s',
}

def sample():
    with (args.output / 'memory.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'phase', 'pss_kib', 'rss_kib', 'mem_available_kib', 'swap_free_kib', 'pswpin', 'pswpout'])
        while not stop.is_set():
            pss = rss = 0
            for proc in Path('/proc').iterdir():
                if not proc.name.isdigit():
                    continue
                try:
                    if int(proc.joinpath('status').read_text().split('Uid:')[1].split()[0]) != postgres_uid:
                        continue
                    values = proc.joinpath('smaps_rollup').read_text().splitlines()
                    for line in values:
                        if line.startswith('Pss:'): pss += int(line.split()[1])
                        if line.startswith('Rss:'): rss += int(line.split()[1])
                except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError):
                    continue
            mem = dict((line.split(':')[0], int(line.split()[1])) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:', 'SwapFree:')))
            vm = dict(line.split() for line in Path('/proc/vmstat').read_text().splitlines() if line.startswith(('pswpin ', 'pswpout ')))
            writer.writerow([time.time(), phase, pss, rss, mem['MemAvailable'], mem['SwapFree'], vm['pswpin'], vm['pswpout']]); f.flush()
            stop.wait(1)

def worker(conn, index):
    rng = random.Random(1234 + index)
    try:
        with conn.cursor() as cur:
            while not stop.is_set():
                if phase == 'idle':
                    time.sleep(0.05); continue
                current = phase
                choice = rng.choices(['point', 'range', 'aggregate'], [75, 20, 5])[0]
                item = rng.randint(1, 699900)
                params = (item,) if choice == 'point' else (item, item + 99) if choice == 'range' else None
                start = time.monotonic()
                cur.execute(queries[choice], params)
                cur.fetchall()
                elapsed = time.monotonic() - start
                if current == 'measured' and phase == 'measured':
                    rows.append((choice, elapsed))
    except Exception as exc:
        errors.append(repr(exc)); stop.set()

import pwd
postgres_uid = pwd.getpwnam('postgres').pw_uid
with (args.output / 'processes.txt').open('w') as f:
    subprocess.run(['ps', '-u', 'postgres', '-o', 'pid,ppid,rss,args'], stdout=f, check=True)
threads = [threading.Thread(target=sample)] + [threading.Thread(target=worker, args=(c, i)) for i, c in enumerate(conns)]
for thread in threads: thread.start()
for next_phase, duration in [('idle', args.idle), ('warmup', args.warmup), ('measured', args.duration)]:
    phase = next_phase
    if stop.wait(duration): break
phase = 'done'
stop.set()
for thread in threads: thread.join()
for conn in conns: conn.close()
with (args.output / 'latencies.csv').open('w', newline='') as f:
    writer = csv.writer(f); writer.writerow(['type', 'seconds']); writer.writerows(rows)
(args.output / 'run.txt').write_text(f'configured_measured_seconds={args.duration}\ncompleted={len(rows)}\nerrors={errors}\n')
if errors: raise SystemExit(1)
