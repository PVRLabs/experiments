#!/usr/bin/env python3
"""Linux-only measured runner. Invoke only after separate benchmark authorization."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ['-Xms16m', '-Xmx80m', '-Xss256k', '-XX:+UseSerialGC',
         '-XX:TieredStopAtLevel=1', '-XX:ReservedCodeCacheSize=32m',
         '-XX:+UseCompactObjectHeaders']
VARIANTS = ('spring-jpa', 'coilbase-jdbi', 'coilbase-hibernate')


def request(path, method='GET', port=8080):
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f'http://127.0.0.1:{port}{path}', method=method), timeout=10) as response:
            response.read()
            return time.perf_counter() - start, response.status, None
    except Exception as error:
        return time.perf_counter() - start, 0, str(error)


def capture(command):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {'command': command, 'exit_code': result.returncode, 'output': result.stdout}


def verify_state(state, generations, refresh_windows=None):
    """Compare committed data with every commanded fixture generation, including seed."""
    failures = []
    if refresh_windows is not None and len(refresh_windows) != len(generations):
        failures.append('Refresh window count does not match generations')
    expected = {}
    for path in (ROOT / 'fixture/responses').glob('*.json'):
        payload = json.loads(path.read_text())
        expected[path.stem.replace('__', '/')] = payload
    projects = state['projects']
    history = state['star_history']
    if len(projects) != len(expected): failures.append('Unexpected project count')
    if len(history) != len(expected) * len(generations): failures.append('Unexpected history count')
    if {p['repo_name'] for p in projects} != set(expected): failures.append('Unexpected repositories')
    for project in projects:
        payload = expected.get(project['repo_name'])
        if payload is None: continue
        for column, field in [('current_stars','stargazers_count'), ('current_forks','forks_count'), ('current_watchers','subscribers_count')]:
            target = payload[field] + (generations[-1] if column == 'current_stars' else 0)
            if project[column] != target: failures.append(f"{project['repo_name']}: wrong {column}")
        if project['last_pushed_at'] != payload['pushed_at']: failures.append('Wrong push timestamp')
        if not project['last_polled_at']: failures.append('Missing poll timestamp')
        rows = [h for h in history if h['project_id'] == project['id']]
        if [h['star_count'] for h in rows] != [payload['stargazers_count'] + g for g in generations]:
            failures.append(f"{project['repo_name']}: missing or duplicate history generations")
        try:
            recorded = [parse_timestamp(row['recorded_at']) for row in rows]
            last_polled = parse_timestamp(project['last_polled_at'])
        except (ValueError, TypeError) as error:
            failures.append(f"{project['repo_name']}: invalid persistence timestamp: {error}")
            continue
        if any(later <= earlier for earlier, later in zip(recorded, recorded[1:])):
            failures.append(f"{project['repo_name']}: history timestamps do not progress")
        if recorded and last_polled < recorded[-1]:
            failures.append(f"{project['repo_name']}: stale final poll timestamp")
        if refresh_windows:
            # H2 stores microseconds; allow one microsecond for boundary rounding.
            for timestamp, (started, finished) in zip(recorded, refresh_windows):
                if not started - 0.000001 <= timestamp <= finished + 0.000001:
                    failures.append(f"{project['repo_name']}: history timestamp outside refresh window")
            started, finished = refresh_windows[-1]
            if not started - 0.000001 <= last_polled <= finished + 0.000001:
                failures.append(f"{project['repo_name']}: final poll timestamp outside latest refresh")
    return failures


def parse_timestamp(value):
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return timestamp.timestamp()


def run(variant, mode, output):
    output.mkdir(parents=True, exist_ok=False)
    env = dict({key: os.environ[key] for key in ('PATH','JAVA_HOME','HOME','TMPDIR','LANG','LC_ALL') if key in os.environ}, TZ='UTC', PORT='8080',
               DB_URL=f'jdbc:h2:file:{output}/database;QUERY_STATISTICS=TRUE;QUERY_STATISTICS_MAX_ENTRIES=1000',
               SPRING_DATASOURCE_URL=f'jdbc:h2:file:{output}/database;QUERY_STATISTICS=TRUE;QUERY_STATISTICS_MAX_ENTRIES=1000',
               APP_GITHUB_API_BASE_URL='http://127.0.0.1:18080',
               APP_GITHUB_REPOS='PVRLabs/statlite,PVRLabs/aibadger,scriptella/scriptella-etl', GITHUB_TOKEN='',
               APP_GITHUB_INITIAL_DELAY_MS='86400000', APP_GITHUB_POLL_INTERVAL_MS='300000')
    jar = (ROOT / variant / 'target' / 'extracted' / 'stars-0.0.1-SNAPSHOT.jar'
           if variant == 'spring-jpa' else ROOT / variant / 'target' / f'{variant}-1.0-SNAPSHOT.jar')
    command = ['java', *FLAGS, '-jar', str(jar)]
    if variant == 'spring-jpa':
        command += ['--app.github.initial-delay-ms=' + env['APP_GITHUB_INITIAL_DELAY_MS'], '--app.github.poll-interval-ms=' + env['APP_GITHUB_POLL_INTERVAL_MS']]
    metadata = {'completed': False, 'variant': variant, 'mode': mode, 'command': command,
                'started_at': time.time(), 'source': (ROOT / 'source-revision.txt').read_text().strip() if (ROOT / 'source-revision.txt').exists() else capture(['git', 'rev-parse', 'HEAD']),
                'java': capture(['java', '-version']), 'uname': platform.uname()._asdict(),
                'memory_before': Path('/proc/meminfo').read_text(),
                'vmstat_before': Path('/proc/vmstat').read_text(),
                'artifact_bytes': sum(p.stat().st_size for p in jar.parent.rglob('*.jar')),
                'runtime_dependencies': (ROOT / variant / 'target/runtime-dependencies.txt').read_text(),
                'artifacts': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in jar.parent.rglob('*.jar')},
                'effective_flags': capture(['java', *FLAGS, '-XX:+PrintFlagsFinal', '-version'])}
    fixture_log = (output / 'fixture.log').open('w')
    fixture = subprocess.Popen(['python3', str(ROOT / 'fixture/server.py')], stdout=fixture_log, stderr=fixture_log)
    process = None
    stop = threading.Event()
    samples = []
    phase = ['startup']
    def sample():
        while not stop.wait(1):
            try:
                status = Path(f'/proc/{process.pid}/status').read_text()
                smaps = Path(f'/proc/{process.pid}/smaps_rollup').read_text()
                mem = Path('/proc/meminfo').read_text()
                fields = {}
                for text, keys in [(status, ('VmRSS', 'VmSwap')), (smaps, ('Pss',)), (mem, ('MemAvailable', 'SwapTotal', 'SwapFree'))]:
                    for line in text.splitlines():
                        key, _, value = line.partition(':')
                        if key in keys:
                            fields[key + '_kib'] = int(value.split()[0])
                samples.append({'time': time.time(), 'phase': phase[0], **fields})
            except (FileNotFoundError, ProcessLookupError):
                break
    requests = []
    heap_failures = []
    generations = [0]
    refresh_windows = []
    persistence_failures = []
    try:
        for _ in range(100):
            if request('/healthz', port=18080)[1] == 200: break
            time.sleep(.05)
        else: raise RuntimeError('Fixture failed readiness')
        with (output / 'application.log').open('w') as log:
            start = time.perf_counter()
            process = subprocess.Popen(command, env=env, cwd=output, stdout=log, stderr=log)
            sampler = threading.Thread(target=sample); sampler.start()
            ready = '/ready' if mode == 'extended' else '/'
            readiness_deadline = time.monotonic() + 60
            while time.monotonic() < readiness_deadline:
                if process.poll() is not None: raise RuntimeError('Application exited before ready')
                if request(ready)[1] == 200: break
                time.sleep(.05)
            else: raise RuntimeError('Readiness timeout')
            metadata['readiness_seconds'] = time.perf_counter() - start
            refresh_started = time.time()
            elapsed, status, error = request('/refresh', 'POST')
            refresh_windows.append((refresh_started, time.time()))
            requests.append({'time': time.time(), 'phase': 'initial', 'path': '/refresh', 'seconds': elapsed, 'status': status, 'error': error})
            if status != 200: raise RuntimeError('Initial refresh failed')
            phases = [('warmup', 30), ('sample', 60)] if mode == 'original' else [('idle', 60), ('warmup', 120), ('mixed', 300), ('recovery', 60)]
            for name, seconds in phases:
                phase[0] = name
                deadline = time.monotonic() + seconds
                tick = 0
                while time.monotonic() < deadline:
                    before = time.monotonic()
                    if name in ('warmup', 'sample', 'mixed'):
                        if name == 'mixed' and tick % 10 == 0:
                            elapsed, status, error = request('/advance', 'POST', port=18080)
                            requests.append({'time': time.time(), 'phase': name, 'path': 'fixture:/advance', 'seconds': elapsed, 'status': status, 'error': error})
                            if status != 200: raise RuntimeError('Fixture advance failed')
                            generations.append(generations[-1] + 1)
                            refresh_started = time.time()
                            elapsed, status, error = request('/refresh', 'POST')
                            refresh_windows.append((refresh_started, time.time()))
                            requests.append({'time': time.time(), 'phase': name, 'path': '/refresh', 'seconds': elapsed, 'status': status, 'error': error})
                        for path in (['/', '/actuator/health', '/actuator/metrics', '/actuator/prometheus'] if variant == 'spring-jpa' and mode == 'original' else ['/', '/ready', '/diagnostics', '/diagnostics'] if mode == 'original' else ['/', '/ready']):
                            elapsed, status, error = request(path)
                            requests.append({'time': time.time(), 'phase': name, 'path': path, 'seconds': elapsed, 'status': status, 'error': error})
                    if tick % 10 == 0:
                        with (output / 'heap.jsonl').open('a') as heap:
                            observation = capture(['jstat', '-gc', str(process.pid)])
                            if observation['exit_code'] != 0: heap_failures.append(observation)
                            heap.write(json.dumps({'time': time.time(), 'phase': name, **observation}) + '\n')
                    tick += 1
                    time.sleep(max(0, (5 if mode == 'original' else 1) - (time.monotonic() - before)))
            metadata['sql_and_heap'] = json.loads(urllib.request.urlopen('http://127.0.0.1:8080/diagnostics', timeout=10).read())
            metadata['application_exit_before_shutdown'] = process.poll()
            metadata['completed'] = True
    finally:
        stop.set()
        if 'sampler' in locals(): sampler.join(timeout=5)
        if process:
            process.terminate()
            try: process.wait(timeout=20)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        fixture.terminate(); fixture.wait(); fixture_log.close()
        try:
            dump = capture(['java', '-cp', str(ROOT / 'coilbase-jdbi/target/lib/*'), 'pvrlabs.stargazer.StateDump', f'jdbc:h2:file:{output}/database;IFEXISTS=TRUE'])
            metadata['database_verification_command'] = dump
            if dump['exit_code'] != 0: raise ValueError('Offline database dump failed')
            state = json.loads(dump['output'])
            (output / 'database-state.json').write_text(json.dumps(state, indent=2))
            persistence_failures = verify_state(state, generations, refresh_windows)
        except Exception as error:
            persistence_failures = [str(error)]
        metadata['refresh_windows'] = refresh_windows
        metadata['expected_generations'] = generations
        metadata['persistence_verification'] = {'passed': not persistence_failures, 'failures': persistence_failures}
        metadata['memory_after'] = Path('/proc/meminfo').read_text()
        metadata['vmstat_after'] = Path('/proc/vmstat').read_text()
        metadata['kernel_oom_evidence'] = capture(['dmesg', '--ctime'])
        def counter(text, key):
            return int(next(line.split()[1] for line in text.splitlines() if line.startswith(key + ' ')))
        reasons = list(persistence_failures)
        if not metadata['completed']: reasons.append('Incomplete workload')
        if metadata.get('application_exit_before_shutdown') is not None: reasons.append('Application exited during workload')
        if any(r['status'] != 200 for r in requests): reasons.append('HTTP errors')
        if not samples: reasons.append('Missing memory samples')
        if heap_failures: reasons.append('Heap collector failures')
        if any(s.get('VmSwap_kib', 0) for s in samples): reasons.append('Process swap observed')
        if counter(metadata['vmstat_after'], 'oom_kill') != counter(metadata['vmstat_before'], 'oom_kill'): reasons.append('Guest OOM kill counter increased')
        if not metadata.get('sql_and_heap', {}).get('queries'): reasons.append('Missing SQL statistics')
        metadata['acceptance'] = {'accepted': not reasons, 'reasons': reasons}
        (output / 'metadata.json').write_text(json.dumps(metadata, indent=2))
        (output / 'samples.json').write_text(json.dumps(samples))
        (output / 'requests.json').write_text(json.dumps(requests))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['original', 'extended'], required=True)
    parser.add_argument('--order', nargs='+', choices=VARIANTS, default=list(VARIANTS))
    parser.add_argument('--runs', type=int, default=2)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='Run measured workloads; requires separate authorization')
    args = parser.parse_args()
    if args.runs < 2: parser.error('At least two runs per variant are required')
    if not args.execute:
        print(json.dumps({'mode': args.mode, 'order': args.order, 'runs': args.runs, 'flags': FLAGS, 'execution': False}, indent=2)); return
    if set(args.order) != set(VARIANTS) or len(args.order) != 3: parser.error('Order must contain each variant exactly once')
    if shutil.which('jstat') is None: parser.error('A full JDK with jstat is required')
    if platform.system() != 'Linux': parser.error('Measurements require Linux')
    if int(Path('/proc/meminfo').read_text().split('SwapTotal:')[1].split()[0]) != 0: parser.error('Guest swap must be disabled')
    if 'version "25.' not in capture(['java', '-version'])['output']: parser.error('JDK 25 is required')
    if os.cpu_count() != 1: parser.error('Target guest must have one vCPU')
    total_kib = int(Path('/proc/meminfo').read_text().split('MemTotal:')[1].split()[0])
    if not 400000 <= total_kib <= 524288: parser.error('Target guest must have 512 MiB allocated RAM; verify VM capture')
    for repeat in range(args.runs):
        order = args.order if repeat % 2 == 0 else list(reversed(args.order))
        for variant in order: run(variant, args.mode, args.output.resolve() / f'{repeat+1:02}-{variant}')

if __name__ == '__main__': main()
