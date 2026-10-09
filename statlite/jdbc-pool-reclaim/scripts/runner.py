#!/usr/bin/env python3
"""Guest-only smoke or six recorded scenarios; independent raw evidence, no UI automation."""
import argparse
from concurrent.futures import Future, ThreadPoolExecutor
import csv
import datetime
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from common import (CONFIGS, FLAGS, ORDER, TIMELINE, WINDOWS, check_busy_window, digest,
                    jsonlines, meminfo, pool_metrics, save, summarize_session)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def available_port(port):
    with socket.socket() as listener:
        # Match server restart semantics: TIME_WAIT is not a live listener.
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', port))


def bundle_files(bundle):
    """Freeze durable release inputs, excluding generated Python caches."""
    return {str(p.relative_to(bundle)): digest(p) for p in sorted(bundle.rglob('*'))
            if p.is_file() and p.name not in ['SHA256SUMS', '.deploy-complete']
            and '__pycache__' not in p.relative_to(bundle).parts
            and p.suffix not in ['.pyc', '.pyo']}


def stop(process):
    process.terminate()
    try:
        process.wait(10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(5)
        raise RuntimeError('Forced shutdown; inspect process/application logs')
    if process.returncode not in (0, -signal.SIGTERM, 143):
        raise RuntimeError(f'Unexpected exit {process.returncode}')


class Runner:
    def __init__(self, args):
        self.args = args
        self.bundle, self.output = args.bundle.resolve(), args.output.resolve()
        self.config = json.loads(args.config.read_text())
        for key in ['role', 'database', 'smoke_database']:
            if not re.fullmatch('[a-z][a-z0-9_]{0,40}', self.config[key]):
                raise ValueError(f'Invalid database identifier: {key}')
        self.database = self.config['smoke_database' if args.mode == 'smoke' else 'database']
        self.user = pwd.getpwnam(self.config['guest_user'])
        if self.user.pw_uid == 0:
            raise ValueError('Configure a non-root guest user for Java and StatLite')
        self.output.mkdir(parents=True, exist_ok=False)
        self.events = (self.output / 'experiment.log').open('a', buffering=1)
        self.processes, self.logs = {}, []
        self.lock = threading.Lock()
        self.sampler_stop = threading.Event()
        self.sampler_error = None
        self.scenario_abort = threading.Event()
        self.run = None
        self.monitor = None
        self.monitor_status = {'status': 'not-started'}
        self.origin = time.monotonic()

    def event(self, event, **data):
        with self.lock:
            value = dict(time=now(), monotonic=time.monotonic(), event=event, **data)
            line = json.dumps(value)
            self.events.write(line + '\n')
            print(line, flush=True)
            if self.run is not None:
                with (self.run / 'events.jsonl').open('a') as stream:
                    stream.write(line + '\n')

    def sql(self, query):
        env = dict(os.environ, PGAPPNAME='pool-observer', PGCONNECT_TIMEOUT='3',
                   PGOPTIONS='-c statement_timeout=3000')
        # A short observer connection each sample, excluded from A/B counts.
        return subprocess.check_output(['runuser', '-u', 'postgres', '--', 'psql', '-X', '-qAt',
                                        '-p', str(self.config['port']), '-d', self.database,
                                        '-v', 'ON_ERROR_STOP=1', '-c', query], env=env, text=True, timeout=5).strip()

    def pg_rows(self):
        return json.loads(self.sql("SELECT coalesce(json_agg(t),'[]'::json)::text FROM "
                                   "(SELECT pid,application_name,usename,datname,state FROM pg_stat_activity "
                                   "WHERE backend_type='client backend' AND pid <> pg_backend_pid()) t"))

    def tags(self):
        return {name: f'pr-{self.args.session}-{self.run.name}-{name}' for name in ['A', 'B']}

    def connections(self):
        tags = self.tags()
        rows = self.pg_rows()
        selected = [row for row in rows if row['datname'] == self.database
                    and row['usename'] == self.config['role'] and row['application_name'] in tags.values()]
        counts = {name: sum(row['application_name'] == tag for row in selected) for name, tag in tags.items()}
        return dict(counts, aggregate=sum(counts.values()), rows=selected)

    def clean(self):
        if self.processes:
            raise RuntimeError('Managed processes still present')
        stale = []
        for proc in Path('/proc').glob('[0-9]*'):
            try:
                command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
                comm = (proc / 'comm').read_text().strip()
                if comm == 'java' or (int(proc.name) != os.getpid() and
                                     ((comm.startswith('python') and ('runner.py' in command or '/fixture/server.py' in command)))):
                    # This runner's deliberately persistent monitor is allowed.
                    if self.monitor is None or int(proc.name) != self.monitor.pid:
                        stale.append(dict(pid=int(proc.name), comm=comm))
            except (FileNotFoundError, ProcessLookupError):
                pass
        if stale:
            raise RuntimeError(f'Stale benchmark processes; inspect/stop identified units: {stale}')
        for port in [8081, 8082]:
            available_port(port)
        unexpected = [r for r in self.pg_rows() if r['usename'] != 'postgres' or r['application_name'] != 'pool-observer']
        if unexpected:
            raise RuntimeError(f'Unexpected DB clients; inspect before recording: {unexpected}')
        self.event('clean-state')

    def environment(self):
        raw = Path('/proc/meminfo').read_text()
        memory = meminfo(raw)
        if not 900 * 1024 <= memory['MemTotal'] <= 1100 * 1024 or memory['SwapTotal'] != 0:
            raise RuntimeError('Expected approximately 1 GiB and no swap')
        if len(Path('/proc/swaps').read_text().splitlines()) != 1:
            raise RuntimeError('Swap device enabled')
        if shutil.disk_usage(self.output).free < 200 * 1024 * 1024:
            raise RuntimeError('Need at least 200 MiB free for results')
        self.pg_settings = json.loads(self.sql("SELECT json_object_agg(name,setting)::text FROM pg_settings WHERE name IN "
                                               "('server_version','shared_buffers','work_mem','max_connections','port',"
                                               "'idle_session_timeout','idle_in_transaction_session_timeout','ssl','data_directory')"))
        if int(self.pg_settings['idle_session_timeout']) or int(self.pg_settings['idle_in_transaction_session_timeout']):
            raise RuntimeError('Disable server-side idle retirement before this experiment')
        self.postmaster, self.cgroup = None, None
        try:
            self.postmaster = int((Path(self.pg_settings['data_directory']) / 'postmaster.pid').read_text().splitlines()[0])
            for line in Path(f'/proc/{self.postmaster}/cgroup').read_text().splitlines():
                if line.startswith('0::'):
                    candidate = Path('/sys/fs/cgroup') / line[3:].lstrip('/')
                    if (candidate / 'memory.current').exists():
                        self.cgroup = candidate
        except (OSError, ValueError, IndexError, KeyError, TypeError) as error:
            self.event('optional-pg-memory-discovery-warning', error=str(error))
        save(self.output / 'environment.json', dict(time=now(), host_meminfo=raw,
             uname=list(os.uname()), postgres_settings=self.pg_settings,
             postmaster_pid=self.postmaster, cgroup=str(self.cgroup) if self.cgroup else None,
             jvm_flags=FLAGS, java=self.config['java'], guest_user=self.user.pw_name))
        return {'files': bundle_files(self.bundle),
                'config_sha256': digest(self.args.config), 'jvm_flags': FLAGS, 'timeline': TIMELINE,
                'postgres_settings': self.pg_settings,
                'java_sha256': digest(self.config['java']),
                'java_version': subprocess.check_output([self.config['java'], '-version'], stderr=subprocess.STDOUT,
                                                        text=True, timeout=5)}

    def launch(self, key, args, directory, env=None):
        log = (directory / f'{key}.log').open('a')
        self.logs.append(log)
        process = subprocess.Popen(args, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   user=self.user.pw_uid, group=self.user.pw_gid, extra_groups=[])
        self.event('launch', name=key, pid=process.pid)
        return process

    def monitor_start(self):
        available_port(9090)
        directory = self.output / 'statlite'
        directory.mkdir()
        os.chown(directory, self.user.pw_uid, self.user.pw_gid)
        config = f'''server:
  listen: "127.0.0.1:9090"
storage:
  sqlite_path: "{directory}/statlite.sqlite"
polling:
  interval: "2s"
  timeout: "2s"
targets:
  - name: pool-A
    type: spring
    url: "http://127.0.0.1:8081/actuator"
    collect_host_metrics: true
  - name: pool-B
    type: spring
    url: "http://127.0.0.1:8082/actuator"
  - name: statlite-self
    type: statlite-metrics
    url: "http://127.0.0.1:9090/statlite/metrics"
'''
        save(directory / 'identity.json', dict(A=8081, B=8082, statlite=9090))
        (directory / 'statlite.yaml').write_text(config)
        self.monitor = self.launch('statlite', [str(self.bundle / 'statlite'), '--config', str(directory / 'statlite.yaml')], directory)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.monitor.poll() is not None:
                raise RuntimeError('StatLite exited; inspect statlite/statlite.log')
            try:
                get('http://127.0.0.1:9090/healthz')
                return
            except OSError:
                time.sleep(.2)
        raise RuntimeError('StatLite readiness timeout')

    def monitor_start_best_effort(self):
        try:
            self.monitor_start()
            self.monitor_status = {'status': 'running', 'pid': self.monitor.pid}
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            self.monitor_status = {'status': 'unavailable', 'error': str(error)}
            self.event('optional-statlite-warning', **self.monitor_status)
            if self.monitor and self.monitor.poll() is None:
                try:
                    stop(self.monitor)
                except (OSError, RuntimeError, subprocess.SubprocessError) as cleanup:
                    self.event('optional-statlite-stop-warning', error=str(cleanup))
        directory = self.output / 'statlite'
        directory.mkdir(exist_ok=True)
        save(directory / 'status.json', self.monitor_status)

    def state(self, name):
        port = 8081 if name == 'A' else 8082
        return json.loads(get(f'http://127.0.0.1:{port}/experiment/state'))

    def app_start(self, name, configuration):
        profile = CONFIGS[configuration]
        minimum, idle = profile['expected_minimum'], profile['idle_ms']
        port = 8081 if name == 'A' else 8082
        directory = self.run / name
        directory.mkdir(exist_ok=True)
        # Prevent inherited external Spring config/sizing from masquerading as defaults.
        inherited = {k: v for k, v in os.environ.items()
                     if not k.startswith(('SPRING_DATASOURCE_HIKARI_', 'SPRING_CONFIG_', 'POOL_MIN_', 'POOL_MAX_'))
                     and k not in ['SPRING_APPLICATION_JSON', 'POOL_IDLE_TIMEOUT_MS']}
        env = dict(inherited, SPRING_PROFILES_ACTIVE=configuration, INSTANCE_NAME=f'pool-{name}', SERVER_PORT=str(port),
                   PG_APP_NAME=self.tags()[name], POOL_DB_URL=f"jdbc:postgresql://127.0.0.1:{self.config['port']}/{self.database}",
                   POOL_DB_USER=self.config['role'], POOL_DB_PASSWORD=self.config['password'],
                   HOLD_MS='1000')
        process = self.launch('application', [self.config['java'], *FLAGS, '-jar', str(self.bundle / 'app.jar'),
                                              '--spring.config.location=classpath:/'], directory, env)
        self.processes[name] = process
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'App {name} exited before readiness')
            try:
                health = json.loads(get(f'http://127.0.0.1:{port}/actuator/health/readiness'))
                state = self.state(name)
                if health.get('status') == 'UP':
                    expected = {'instance': f'pool-{name}', 'applicationName': self.tags()[name],
                                'poolName': f'pool-{name}', 'minimumIdle': minimum, 'maximumPoolSize': profile['expected_maximum'],
                                'idleTimeoutMs': idle, 'maxLifetimeMs': 0, 'keepaliveMs': 0,
                                'connectionTimeoutMs': 5000, 'holdMs': 1000}
                    save(directory / f'readiness-{process.pid}.json', dict(time=now(), pid=process.pid,
                         configuration=configuration, sizing_overrides=profile['sizing_overrides'], state=state, health=health))
                    if any(state.get(k) != v for k, v in expected.items()):
                        self.event('resolved-profile-mismatch', configuration=configuration, actual=state, expected=expected)
                        raise RuntimeError(f'Wrong resolved profile/identity: {state}')
                    self.event('ready', instance=name, pid=process.pid, state=state)
                    return
            except (OSError, ValueError):
                pass
            time.sleep(.2)
        raise RuntimeError(f'App {name} readiness timeout')

    def app_stop(self, name):
        process = self.processes.pop(name)
        stop(process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.connections()[name] == 0:
                self.event('stopped', instance=name, exit=process.returncode)
                return
            time.sleep(.2)
        raise RuntimeError(f'App {name} sessions remain after shutdown')

    def pg_memory(self):
        # The actual cluster cgroup includes postmaster, auxiliary processes and backends.
        if self.cgroup:
            pids = [int(p) for p in (self.cgroup / 'cgroup.procs').read_text().split()]
        else:
            # Descendants of this cluster's postmaster, not all clusters on the VM.
            pairs = subprocess.check_output(['ps', '-eo', 'pid=,ppid='], text=True, timeout=3)
            mapping = [tuple(map(int, line.split())) for line in pairs.splitlines()]
            pids = [self.postmaster]
            for _ in range(10):
                additional = [pid for pid, parent in mapping if parent in pids and pid not in pids]
                if not additional:
                    break
                pids.extend(additional)
        rows, races = [], []
        for pid in pids:
            try:
                # Exclude transient observer client process when it happens to be in scope.
                if Path(f'/proc/{pid}/comm').read_text().strip() != 'postgres':
                    continue
                raw = Path(f'/proc/{pid}/smaps_rollup').read_text()
                data = meminfo(raw)
                rows.append(dict(pid=pid, raw=raw, pss_kib=data['Pss'],
                                 private_kib=data.get('Private_Clean', 0) + data.get('Private_Dirty', 0)))
            except (FileNotFoundError, ProcessLookupError):
                races.append(pid)
        if not rows:
            raise RuntimeError('No readable PostgreSQL process memory')
        result = dict(processes=rows, disappeared_pids=races,
                      pss_kib=sum(r['pss_kib'] for r in rows) if not races else None,
                      private_kib=sum(r['private_kib'] for r in rows) if not races else None)
        if self.cgroup:
            result.update(cgroup=str(self.cgroup), cgroup_bytes=int((self.cgroup / 'memory.current').read_text()),
                          memory_stat=(self.cgroup / 'memory.stat').read_text(),
                          memory_events=(self.cgroup / 'memory.events').read_text())
        return result

    def optional_pg_memory(self, row, requested=False):
        # One daemon worker, never waited on by primary sampling or shutdown.
        # Timestamp the accounting interval rather than pretending it is current.
        job = getattr(self, 'memory_job', None)
        if job and job['future'].done():
            if job['run'] == self.run:
                try:
                    row['pg_memory'] = job['future'].result()
                except Exception as error:
                    row['warnings'].append(f'Optional PG memory: {error}')
                    self.event('optional-pg-memory-warning', error=str(error))
            self.memory_job = None
            job = None
        if requested and job is None:
            future = Future()
            owner = self.run
            def collect():
                started = time.monotonic()
                try:
                    result = self.pg_memory()
                    result.update(collection_start_monotonic=started,
                                  collection_end_monotonic=time.monotonic())
                    future.set_result(result)
                except Exception as error:
                    future.set_exception(error)
            self.memory_job = dict(future=future, run=owner)
            threading.Thread(target=collect, name='optional-pg-memory', daemon=True).start()
        elif requested and job:
            row['warnings'].append('Optional PG memory still running; skipped new collection')

    def safe_memory(self, minimum_kib):
        raw = Path('/proc/meminfo').read_text()
        values = meminfo(raw)
        if values['SwapTotal'] != 0:
            raise RuntimeError('Swap changed')
        if values['MemAvailable'] < minimum_kib and self.monitor and self.monitor.poll() is None:
            self.event('optional-statlite-stopped-for-memory', minimum_kib=minimum_kib,
                       available_kib=values['MemAvailable'])
            try:
                stop(self.monitor)
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                self.event('optional-statlite-stop-warning', error=str(error))
            self.monitor_status = {'status': 'stopped-for-memory'}
            save(self.output / 'statlite' / 'status.json', self.monitor_status)
            raw = Path('/proc/meminfo').read_text()
            values = meminfo(raw)
        if values['SwapTotal'] != 0 or values['MemAvailable'] < minimum_kib:
            raise RuntimeError(f'Swap changed or available RAM fell below {minimum_kib // 1024} MiB')
        return raw, values

    def sample(self, elapsed, memory=False, full_metrics=False):
        row = dict(time=now(), monotonic=time.monotonic(), elapsed=elapsed, apps={}, errors=[], warnings=[])
        row['host_raw'], row['host'] = self.safe_memory(32 * 1024)
        for name, process in self.processes.items():
            if process.poll() is not None:
                raise RuntimeError(f'App {name} exited during observation')
            port = 8081 if name == 'A' else 8082
            app = dict(pid=process.pid)
            row['apps'][name] = app
            try:
                status = Path(f'/proc/{process.pid}/status').read_text()
                app['status_raw'] = status
                rss = meminfo(status).get('VmRSS')
                if rss is not None:
                    app['rss_kib'] = rss
                else:
                    row['warnings'].append(f'Optional {name} RSS missing')
            except OSError as error:
                if process.poll() is not None:
                    raise RuntimeError(f'App {name} exited during observation') from error
                row['warnings'].append(f'Optional {name} RSS: {error}')
            raw = None
            try:
                raw = get(f'http://127.0.0.1:{port}/actuator/prometheus').decode()
                app['pool'] = pool_metrics(raw, f'pool-{name}')
                if full_metrics:
                    app['metrics_raw'] = raw
            except (OSError, ValueError) as error:
                # Preserve malformed exposition for diagnosis, not every healthy scrape.
                if raw is not None:
                    app['metrics_raw'] = raw
                row['errors'].append(f'{name} metrics: {error}')
        try:
            row['pg'] = self.connections()
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            row['errors'].append(f'PG: {error}')
        self.optional_pg_memory(row, requested=memory)
        if self.monitor:
            if self.monitor.poll() is not None:
                self.event('monitor-exit', exit=self.monitor.returncode)
            else:
                try:
                    row['monitor_rss_kib'] = meminfo(Path(f'/proc/{self.monitor.pid}/status').read_text()).get('VmRSS')
                except OSError as error:
                    row['warnings'].append(f'Optional StatLite RSS: {error}')
        row['collection_end_monotonic'] = time.monotonic()
        with self.lock:
            with (self.run / 'samples.jsonl').open('a') as stream:
                stream.write(json.dumps(row) + '\n')
        return row

    def sample_loop(self):
        index, consecutive = 0, 0
        tick = time.monotonic()
        try:
            while not self.sampler_stop.is_set():
                row = self.sample(time.monotonic() - self.origin, memory=index % 5 == 0,
                                  full_metrics=index % 30 == 0)
                consecutive = consecutive + 1 if row['errors'] else 0
                if consecutive >= 3:
                    raise RuntimeError('Essential collection failed for three consecutive samples')
                index += 1
                tick += 1
                self.sampler_stop.wait(max(0, tick - time.monotonic()))
        except Exception as error:
            self.sampler_error = error
            self.event('sampler-failed', error=str(error))

    def wait_until(self, deadline):
        while time.monotonic() < deadline:
            if self.sampler_error:
                raise self.sampler_error
            if self.scenario_abort.is_set():
                raise RuntimeError('Other workload worker failed; abort remaining traffic')
            time.sleep(min(.2, max(0, deadline - time.monotonic())))

    def request(self, name, wave, request, participants, stage, scheduled):
        port = 8081 if name == 'A' else 8082
        started = time.monotonic()
        row = dict(instance=name, stage=stage, wave=wave, request=request,
                   time=now(), scheduled=scheduled - self.origin, start=started - self.origin,
                   elapsed_ms=None, status=0, error='', acquisition_ms='')
        payload = None
        try:
            query = urllib.parse.urlencode(dict(wave=wave, request=request, participants=participants))
            payload = json.loads(get(f'http://127.0.0.1:{port}/experiment/work?{query}', timeout=15))
            row['status'] = 200
            if (payload.get('value') != 1 or payload.get('instance') != f'pool-{name}'
                    or payload.get('wave') != wave or payload.get('request') != request):
                raise ValueError('Workload response assertion failed')
            row['acquisition_ms'] = payload['acquisitionMs']
        except Exception as error:
            if isinstance(error, urllib.error.HTTPError):
                row['status'] = error.code
            row['error'] = str(error)
        row['elapsed_ms'] = (time.monotonic() - started) * 1000
        with self.lock:
            self.request_writer.writerow(row)
            self.request_file.flush()
            if payload:
                with (self.run / 'acquisition.jsonl').open('a') as stream:
                    stream.write(json.dumps(dict(instance=name, stage=stage, **{'payload': payload})) + '\n')
        return row, payload

    def wave(self, name, stage, index, scheduled, participants=10):
        wave = f'{name}-{stage}-{index}'
        self.wait_until(scheduled)
        self.event('wave-start', instance=name, stage=stage, wave=wave, lateness_s=time.monotonic() - scheduled)
        with ThreadPoolExecutor(max_workers=participants) as pool:
            results = list(pool.map(lambda i: self.request(name, wave, i, participants, stage, scheduled), range(participants)))
        payloads = [p for row, p in results if not row['error'] and p]
        if participants == 10:
            if len(payloads) != 10 or len({p['backendPid'] for p in payloads}) != 10 or max(p['activeAtGate'] for p in payloads) != 10:
                self.event('wave-incomplete', instance=name, wave=wave, successful=len(payloads))
                if self.args.mode == 'smoke' or (stage == 'burst' and index == 0):
                    raise RuntimeError(f'{name}/{wave}: failed to prove ten concurrent JDBC connections; retained request errors')
        elif not payloads:
            raise RuntimeError(f'{name} serial warm-up failed')
        self.event('wave-end', instance=name, wave=wave)
        return payloads

    def burst(self, name, start, end):
        try:
            for index, offset in enumerate(range(start, end, TIMELINE['wave_interval'])):
                scheduled = self.origin + offset
                if time.monotonic() > scheduled + 2:
                    raise RuntimeError(f'{name} missed workload wave at {offset}s; no catch-up traffic')
                self.wave(name, 'burst', index, scheduled)
            self.wait_until(self.origin + end)
        except Exception:
            self.scenario_abort.set()
            raise

    def verify_counts(self, configuration, initial=False):
        expected = 10 if configuration != 'reclaim' and not initial else (10 if configuration == 'default' else 1)
        deadline = time.monotonic() + (5 if initial else 0)
        while True:
            states = {name: self.state(name) for name in ['A', 'B']}
            pg = self.connections()
            lower, upper = (expected, expected) if expected == 10 else (1, 2)
            if all(lower <= states[n]['total'] <= upper and lower <= pg[n] <= upper
                   and states[n]['active'] == 0 for n in ['A', 'B']):
                self.event('counts-verified', initial=initial, states=states, pg=pg)
                return
            if time.monotonic() >= deadline:
                raise RuntimeError(f'Unexpected pool/PG counts: states={states}, pg={pg}')
            time.sleep(.2)

    def verify_busy_window(self, configuration, window=None):
        with self.lock:
            samples = jsonlines(self.run / 'samples.jsonl')
        check = check_busy_window(samples, configuration, window=window)
        save(self.run / 'mechanism-check.json', check)
        self.event('busy-window-mechanism-check', status=check['status'],
                   window=check['window'],
                   complete_samples=check['complete_samples'], B_active_samples=check['B_active_samples'],
                   artifact='mechanism-check.json', violations=check['violations'])
        if check['status'] != 'passed':
            raise RuntimeError(f"Late B-busy/A-idle mechanism check failed: {check['violations']}")

    def smoke_bursts(self, configuration):
        a_end, b_start, b_end = 8, 6, 10
        window = None
        if configuration == 'reclaim':
            # Match recording's elapsed time since A stopped, while keeping B busy.
            shift = a_end - TIMELINE['A_end']
            window = tuple(bound + shift for bound in WINDOWS['B_busy_A_idle'])
            b_end = window[1]
        self.event('smoke-burst-schedule', A=[0, a_end], B=[b_start, b_end],
                   mechanism_window=window)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.burst, 'A', 0, a_end),
                       pool.submit(self.burst, 'B', b_start, b_end)]
            for future in futures:
                future.result()
        if window is not None:
            self.verify_busy_window(configuration, window=window)

    def monitor_check(self):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            ok = True
            for name in ['A', 'B']:
                try:
                    status = json.loads(get(f'http://127.0.0.1:9090/api/v1/status?target=pool-{name}'))
                    points = json.loads(get(f'http://127.0.0.1:9090/api/v1/metrics?target=pool-{name}'))['points']
                    ok &= status['collection_status'] == 'ok' and any(p.get('runtime_memory_bytes') is not None for p in points)
                except (OSError, ValueError, KeyError):
                    ok = False
            if ok:
                self.event('monitor-both-targets-ok')
                return
            time.sleep(1)
        raise RuntimeError('StatLite did not collect both targets')

    def snapshots(self):
        if not self.monitor or self.monitor.poll() is not None:
            self.event('optional-monitor-snapshots-unavailable')
            return
        directory = self.run / 'statlite'
        directory.mkdir(exist_ok=True)
        for name in ['pool-A', 'pool-B', 'statlite-self']:
            for kind in ['status', 'metrics', 'events']:
                try:
                    (directory / f'{name}-{kind}.json').write_bytes(get(f'http://127.0.0.1:9090/api/v1/{kind}?target={name}'))
                except OSError as error:
                    self.event('monitor-snapshot-missing', target=name, kind=kind, error=str(error))

    def scenario(self, run_name, smoke=False):
        self.clean()
        configuration = run_name.rsplit('-', 1)[0]
        self.run = self.output / run_name
        self.run.mkdir()
        metadata = dict(configuration=configuration, mode=self.args.mode, status='partial',
                        start_utc=now(), timeline=TIMELINE, tags=self.tags(), jvm_flags=FLAGS)
        save(self.run / 'run.json', metadata)
        for filename in ['samples.jsonl', 'acquisition.jsonl', 'events.jsonl']:
            (self.run / filename).touch()
        self.request_file = (self.run / 'requests.csv').open('w', newline='')
        columns = ['instance', 'stage', 'wave', 'request', 'time', 'scheduled', 'start', 'elapsed_ms', 'status', 'error', 'acquisition_ms']
        self.request_writer = csv.DictWriter(self.request_file, fieldnames=columns)
        self.request_writer.writeheader()
        self.sampler_stop.clear()
        self.scenario_abort.clear()
        self.sampler_error = None
        sampler = None
        try:
            self.app_start('A', configuration)
            if smoke:
                self.wave('A', 'independent', 0, time.monotonic())
                self.app_stop('A')
                self.app_start('B', configuration)
                self.wave('B', 'independent', 0, time.monotonic())
                self.app_stop('B')
                self.app_start('A', configuration)
            self.app_start('B', configuration)
            self.verify_counts(configuration, initial=True)
            for name in ['A', 'B']:
                self.wave(name, 'warmup', 0, time.monotonic(), participants=1)
            if smoke:
                if self.monitor and self.monitor.poll() is None:
                    try:
                        self.monitor_check()
                    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
                        self.event('optional-statlite-collection-warning', error=str(error))
                try:
                    get('http://127.0.0.1:8081/experiment/work?wave=bad&request=0&participants=2')
                    raise RuntimeError('Invalid workload request was accepted')
                except urllib.error.HTTPError as error:
                    if error.code != 400:
                        raise
            self.safe_memory(64 * 1024)
            self.origin = time.monotonic() + (3 if smoke else 15)
            metadata.update(origin_monotonic=self.origin, origin_utc=datetime.datetime.fromtimestamp(
                time.time() + self.origin - time.monotonic(), datetime.timezone.utc).isoformat(), pids={n: p.pid for n, p in self.processes.items()})
            sampler = threading.Thread(target=self.sample_loop, name='raw-sampler')
            sampler.start()
            self.wait_until(self.origin)
            if smoke:
                self.safe_memory(64 * 1024)
            if smoke:
                self.smoke_bursts(configuration)
                self.wait_until(time.monotonic() + (60 if configuration == 'reclaim' else 3))
            else:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(self.burst, 'A', TIMELINE['A_start'], TIMELINE['A_end']),
                               pool.submit(self.burst, 'B', TIMELINE['B_start'], TIMELINE['B_end'])]
                    for future in futures:
                        future.result()
                self.verify_busy_window(configuration)
                self.event('both-bursts-ended')
                self.wait_until(self.origin + TIMELINE['quiet_end'])
            self.verify_counts(configuration)
            self.sample(time.monotonic() - self.origin, memory=True, full_metrics=True)
            self.wave('A', 'revisit', 0, time.monotonic() if smoke else self.origin + TIMELINE['A_revisit'])
            self.wave('B', 'revisit', 0, time.monotonic() if smoke else self.origin + TIMELINE['B_revisit'])
            if not smoke:
                self.wait_until(self.origin + TIMELINE['final_end'])
            self.sample(time.monotonic() - self.origin, memory=True, full_metrics=True)
            self.snapshots()
            if self.sampler_error:
                raise self.sampler_error
            self.verify_overlap()
            metadata['status'] = 'valid'
        except Exception as error:
            metadata.update(status='invalid', error=str(error))
            self.event('scenario-failed', error=str(error))
            raise
        finally:
            self.sampler_stop.set()
            if sampler:
                sampler.join(timeout=15)
                if sampler.is_alive():
                    metadata.update(status='invalid', error='Sampler did not stop')
            self.request_file.close()
            cleanup_errors = []
            for name in list(self.processes):
                try:
                    self.app_stop(name)
                except Exception as error:
                    cleanup_errors.append(str(error))
            metadata.update(end_utc=now(), cleanup_errors=cleanup_errors)
            if cleanup_errors:
                metadata.update(status='invalid', error='; '.join(cleanup_errors))
            save(self.run / 'run.json', metadata)
            summarize_session(self.output)
            self.run = None
            if cleanup_errors or (sampler and sampler.is_alive()):
                raise RuntimeError('Cleanup failed; stop sequence and inspect retained evidence')

    def verify_overlap(self):
        from common import jsonlines
        rows = [r for r in jsonlines(self.run / 'acquisition.jsonl') if r['stage'] == 'burst']
        intervals = {name: [(r['payload']['acquiredMs'], r['payload']['returnedMs']) for r in rows if r['instance'] == name]
                     for name in ['A', 'B']}
        events = sorted((stamp, name, delta) for name, values in intervals.items()
                        for start, end in values for stamp, delta in [(start, 1), (end, -1)])
        counts, simultaneous, peak = {'A': 0, 'B': 0}, 0, 0
        for stamp, name, delta in events:
            counts[name] += delta
            simultaneous = max(simultaneous, min(counts.values()))
            peak = max(peak, sum(counts.values()))
        if simultaneous < 8:
            raise RuntimeError('No brief elevated JDBC occupancy overlap (at least eight holders on each instance)')
        self.event('jdbc-overlap-verified', peak_holders=peak, simultaneous_per_instance=simultaneous)

    def execute(self):
        self.clean()
        fingerprint = self.environment()
        if self.args.mode == 'record':
            if self.args.preflight is None:
                raise RuntimeError('Recorded execution requires a successful smoke manifest')
            preflight = json.loads(self.args.preflight.read_text())
            if not preflight.get('automated_pass') or not preflight.get('environment_acknowledged'):
                raise RuntimeError('Smoke or explicit VM configuration/clock acknowledgement missing')
            if preflight['fingerprint'] != fingerprint:
                raise RuntimeError('Inputs changed since smoke; repeat affected preparation before recording')
        save(self.output / 'manifest.json', dict(fingerprint=fingerprint, mode=self.args.mode, time=now()))
        self.monitor_start_best_effort()
        runs = ['default-1', 'no-reclaim-1', 'reclaim-1'] if self.args.mode == 'smoke' else ORDER
        for name in runs:
            self.scenario(name, smoke=self.args.mode == 'smoke')
        if self.args.mode == 'smoke':
            save(self.output / 'preflight.json', dict(automated_pass=True, environment_acknowledged=False,
                                                     statlite=self.monitor_status,
                                                     fingerprint=fingerprint, time=now()))
        (self.output / 'measurement-complete.txt').write_text(now() + '\n')
        self.event('inspection-ready', mode=self.args.mode,
                   statlite_available=bool(self.monitor and self.monitor.poll() is None),
                   url='http://127.0.0.1:18090/' if self.monitor and self.monitor.poll() is None else None)
        # Inspection lifecycle only: no application or workload is running here.
        # Explicit service stop closes monitor/storage; Ctrl-C works for foreground smoke.
        if self.monitor and self.monitor.poll() is None:
            while self.monitor.poll() is None:
                time.sleep(1)
            self.event('optional-statlite-exited-during-inspection', exit=self.monitor.returncode)
        # Without a monitor there is no inspection service to keep alive; evidence stays valid.

    def close(self):
        self.sampler_stop.set()
        for process in self.processes.values():
            if process.poll() is None:
                try:
                    stop(process)
                except Exception as error:
                    self.event('cleanup-error', error=str(error))
        if self.monitor and self.monitor.poll() is None:
            try:
                stop(self.monitor)
            except Exception as error:
                self.event('cleanup-error', error=str(error))
        directory = self.output / 'closeout'
        directory.mkdir(exist_ok=True)
        for filename, command in [('kernel.log', ['journalctl', '-k', '--since', self.started_utc, '--no-pager']),
                                  ('processes.txt', ['ps', '-eo', 'pid,comm,rss'])]:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            (directory / filename).write_text(result.stdout + result.stderr)
        for stream in self.logs:
            stream.close()
        self.events.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['smoke', 'record'], required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('/etc/pool-reclaim.json'))
    parser.add_argument('--session', required=True)
    parser.add_argument('--preflight', type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[a-zA-Z0-9_-]{1,20}', args.session):
        parser.error('Session must be 1–20 alphanumeric, underscore or hyphen characters')
    if os.geteuid() != 0:
        parser.error('Guest root required for PG/proc collection; Java and StatLite drop to configured guest user')
    if args.config.stat().st_mode & 0o077:
        parser.error('Secret guest configuration must be mode 0600')
    runner = Runner(args)
    runner.started_utc = now()
    def terminate(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    try:
        runner.execute()
    except KeyboardInterrupt:
        runner.event('operator-stop')
    except Exception as error:
        runner.event('fatal', error=str(error))
        raise
    finally:
        runner.close()


if __name__ == '__main__':
    main()
