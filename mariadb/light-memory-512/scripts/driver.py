#!/usr/bin/python3
"""Four persistent clients. Run as root in the guest so process memory is readable."""
import argparse
import csv
import pwd
import random
import subprocess
import threading
import time
from pathlib import Path
import pymysql

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--idle', type=float, default=5)
parser.add_argument('--warmup', type=float, default=20)
parser.add_argument('--duration', type=float, default=50)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
connect = dict(host='127.0.0.1', user='experiment', password='experiment', database='experiment', connect_timeout=10, autocommit=True)
conns = [pymysql.connect(**connect) for _ in range(4)]
stop = threading.Event()
state_lock = threading.Condition()
phase = 'idle'
measured_in_flight = 0
rows = []
errors = []
queries = {
    'point': 'SELECT payload FROM items WHERE id = %s',
    'range': 'SELECT COUNT(*) FROM items WHERE id BETWEEN %s AND %s',
    'aggregate': 'SELECT SUM(bucket) FROM (SELECT bucket FROM items WHERE id <= 12000 ORDER BY payload LIMIT 1 OFFSET 4000) s',
}
mysql_uid = pwd.getpwnam('mysql').pw_uid
rows_in_fixture = 520000

def disk_sectors():
    read = write = 0
    for line in Path('/proc/diskstats').read_text().splitlines():
        parts = line.split()
        if len(parts) < 14:
            continue
        name = parts[2]
        whole = (name.startswith(('sd', 'vd', 'xvd')) and len(name) == 3) or (name.startswith('nvme') and 'p' not in name)
        if whole:
            read += int(parts[5])
            write += int(parts[9])
    return read, write

def sample():
    with (args.output / 'memory.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['timestamp', 'phase', 'pss_kib', 'rss_kib', 'mem_available_kib', 'swap_free_kib', 'pswpin', 'pswpout', 'oom_kill', 'disk_read_sectors', 'disk_write_sectors', 'gap_seconds'])
        previous = None
        while not stop.is_set():
            pss = rss = 0
            for proc in Path('/proc').iterdir():
                if not proc.name.isdigit():
                    continue
                try:
                    if int(proc.joinpath('status').read_text().split('Uid:')[1].split()[0]) != mysql_uid:
                        continue
                    for line in proc.joinpath('smaps_rollup').read_text().splitlines():
                        if line.startswith('Pss:'):
                            pss += int(line.split()[1])
                        elif line.startswith('Rss:'):
                            rss += int(line.split()[1])
                except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
                    continue
            meminfo = {}
            for line in Path('/proc/meminfo').read_text().splitlines():
                if line.startswith(('MemAvailable:', 'SwapFree:')):
                    meminfo[line.split(':')[0]] = int(line.split()[1])
            vmstat = {}
            for line in Path('/proc/vmstat').read_text().splitlines():
                key, value = line.split()
                if key in ('pswpin', 'pswpout', 'oom_kill'):
                    vmstat[key] = value
            sectors = disk_sectors()
            now = time.time()
            gap = '' if previous is None else f'{now - previous:.3f}'
            previous = now
            writer.writerow([now, phase, pss, rss, meminfo['MemAvailable'], meminfo['SwapFree'], vmstat['pswpin'], vmstat['pswpout'], vmstat['oom_kill'], sectors[0], sectors[1], gap])
            handle.flush()
            stop.wait(1)

def capture(label, handle):
    connection = pymysql.connect(**connect)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW GLOBAL STATUS WHERE Variable_name IN ('Innodb_buffer_pool_reads','Innodb_buffer_pool_read_requests','Aria_pagecache_reads','Aria_pagecache_read_requests')")
            values = {name: int(value) for name, value in cursor.fetchall()}
        handle.writerow([label, values['Innodb_buffer_pool_reads'], values['Innodb_buffer_pool_read_requests'], values['Aria_pagecache_reads'], values['Aria_pagecache_read_requests']])
    finally:
        connection.close()

def worker(conn, index):
    global measured_in_flight
    rng = random.Random(1234 + index)
    try:
        with conn.cursor() as cursor:
            while not stop.is_set():
                with state_lock:
                    current = phase
                    if current in ('idle', 'done', 'draining'):
                        current = None
                    elif current == 'measured':
                        measured_in_flight += 1
                if current is None:
                    time.sleep(0.05)
                    continue
                try:
                    choice = rng.choices(['point', 'range', 'aggregate'], [75, 20, 5])[0]
                    item = rng.randint(1, rows_in_fixture - 100)
                    params = (item,) if choice == 'point' else (item, item + 99) if choice == 'range' else None
                    start = time.monotonic()
                    cursor.execute(queries[choice], params)
                    cursor.fetchall()
                    elapsed = time.monotonic() - start
                    if current == 'measured':
                        rows.append((choice, elapsed))
                finally:
                    if current == 'measured':
                        with state_lock:
                            measured_in_flight -= 1
                            state_lock.notify_all()
    except Exception as exc:
        errors.append(repr(exc))
        stop.set()

with (args.output / 'processes.txt').open('w') as handle:
    subprocess.run(['ps', '-u', 'mysql', '-o', 'pid,ppid,rss,args'], stdout=handle, check=True)
status_file = (args.output / 'status.csv').open('w', newline='')
status = csv.writer(status_file)
status.writerow(['label', 'innodb_buffer_pool_reads', 'innodb_buffer_pool_read_requests', 'aria_pagecache_reads', 'aria_pagecache_read_requests'])
threads = [threading.Thread(target=sample)] + [threading.Thread(target=worker, args=(conn, index)) for index, conn in enumerate(conns)]
for thread in threads:
    thread.start()
measured_started = None
measured_seconds = 0
for next_phase, duration in [('idle', args.idle), ('warmup', args.warmup), ('measured', args.duration)]:
    if next_phase == 'measured':
        try:
            capture('measured_start', status)
            status_file.flush()
        except Exception as exc:
            errors.append(repr(exc))
            stop.set()
        measured_started = time.monotonic()
    with state_lock:
        phase = next_phase
    if stop.wait(duration):
        break
if measured_started is not None:
    measured_seconds = time.monotonic() - measured_started
    with state_lock:
        phase = 'draining'
        while measured_in_flight:
            state_lock.wait()
        phase = 'done'
    try:
        capture('measured_end', status)
        status_file.flush()
    except Exception as exc:
        errors.append('status_end=' + repr(exc))
stop.set()
for thread in threads:
    thread.join()
status_file.close()
for conn in conns:
    conn.close()
with (args.output / 'latencies.csv').open('w', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['type', 'seconds'])
    writer.writerows(rows)
(args.output / 'run.txt').write_text(
    f'configured_measured_seconds={args.duration}\nmeasured_seconds={measured_seconds:.3f}\ncompleted={len(rows)}\n'
    f'measured_initiation_window_seconds={measured_seconds:.3f}\n'
    f'latency_rule=queries initiated during measured initiation window; in-flight queries drained before final counters\n'
    f'throughput_rule=completed measured-window queries divided by measured_initiation_window_seconds; drain completions are not extra window time\nerrors={errors}\n'
)
if errors:
    raise SystemExit(1)
