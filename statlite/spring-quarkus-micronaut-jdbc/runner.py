#!/usr/bin/env python3
"""Guest runner: isolated smoke state followed by the four measured phases."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

APPS = {'spring': (8081, '/actuator/health', '/actuator/prometheus', 'spring/app.jar'),
        'quarkus': (8082, '/q/health', '/q/metrics', 'quarkus/quarkus-run.jar'),
        'micronaut': (8083, '/health', '/prometheus', 'micronaut/app.jar')}
FLAGS = ['-Xms32m', '-Xmx192m', '-XX:+UseG1GC', '-XX:ActiveProcessorCount=2']


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get(url):
    with urllib.request.urlopen(url, timeout=3) as r:
        return r.read()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def stop(p):
    p.terminate()
    try:
        p.wait(10)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()


class Run:
    def __init__(self, bundle, output, java):
        self.bundle, self.output, self.java = bundle.resolve(), output.resolve(), java
        self.output.mkdir(parents=True, exist_ok=False)
        self.processes = {}
        self.logs = []
        self.fixture_exit = None
        self.fixture_available = None
        self.fixture_position = None
        self.fixture_pid = None
        self.events = (self.output / 'events.jsonl').open('a', buffering=1)
        self.samples = (self.output / 'process-samples.jsonl').open('a', buffering=1)
        self.fixture_observations = (self.output / 'fixture-observations.jsonl').open('a', buffering=1)

    def event(self, event, **data):
        value = dict(time=now(), monotonic=time.monotonic(), event=event, **data)
        self.events.write(json.dumps(value) + '\n')
        print(json.dumps(value), flush=True)

    def launch(self, name, args, directory, env=None):
        log = (directory / (name + '.log')).open('a')
        self.logs.append(log)
        p = subprocess.Popen(args, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
        self.processes[name] = p
        self.event('launch', name=name, pid=p.pid, args=args)
        return p

    def observe_fixture(self, phase):
        p = self.processes.get('fixture')
        pid, exit_code = (p.pid, p.poll()) if p else (None, None)
        if self.fixture_pid is not None and pid != self.fixture_pid:
            self.event('fixture-process-changed', phase=phase, previous_pid=self.fixture_pid, pid=pid)
        self.fixture_pid = pid
        if exit_code is not None and self.fixture_exit != (pid, exit_code):
            self.event('fixture-exited', phase=phase, pid=pid, exit_code=exit_code)
            self.fixture_exit = (pid, exit_code)
        observation = dict(time=now(), monotonic=time.monotonic(), phase=phase,
                           managed_pid=pid, managed_exit=exit_code)
        try:
            payload = json.loads(get('http://127.0.0.1:8090/quotes'))
            position = (payload['cycle'], payload['sampleIndex'])
            observation.update(available=True, cycle=position[0], sampleIndex=position[1],
                               marketTime=payload['marketTime'])
            if self.fixture_position is not None and position < self.fixture_position:
                # Replay regression suggests a reset; it does not prove a process restart.
                self.event('fixture-replay-regressed', phase=phase,
                           previous_position=self.fixture_position, position=position)
            self.fixture_position = position
        except (OSError, ValueError, KeyError, TypeError) as e:
            observation.update(available=False, error=str(e))
        if observation['available'] != self.fixture_available:
            self.event('fixture-availability', observation=observation)
            self.fixture_available = observation['available']
        self.fixture_observations.write(json.dumps(observation) + '\n')
        return observation

    def sample(self, phase):
        self.observe_fixture(phase)
        procs = {}
        for name, p in self.processes.items():
            try:
                status = Path(f'/proc/{p.pid}/status').read_text()
                procs[name] = dict(pid=p.pid, status=status, stat=Path(f'/proc/{p.pid}/stat').read_text())
            except FileNotFoundError:
                procs[name] = dict(pid=p.pid, exit=p.poll())
        value = dict(time=now(), monotonic=time.monotonic(), phase=phase,
                     processes=procs, meminfo=Path('/proc/meminfo').read_text(),
                     vmstat=Path('/proc/vmstat').read_text())
        self.samples.write(json.dumps(value) + '\n')

    def monitor(self, directory, interval):
        config = f'''server:\n  listen: "127.0.0.1:9090"\nstorage:\n  sqlite_path: "{directory}/statlite.sqlite"\npolling:\n  interval: "{interval}s"\n  timeout: "2s"\ntargets:\n'''
        for name, (port, _, _, _) in APPS.items():
            endpoint = {'spring': '/actuator', 'quarkus': '/q/metrics', 'micronaut': '/prometheus'}[name]
            config += f'  - name: {name}\n    type: {name}\n    url: "http://127.0.0.1:{port}{endpoint}"\n'
        config += '  - name: statlite-self\n    type: statlite-metrics\n    url: "http://127.0.0.1:9090/statlite/metrics"\n'
        path = directory / 'statlite.yaml'
        path.write_text(config)
        self.launch('statlite', [str(self.bundle / 'statlite'), '--config', str(path)], directory)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.processes['statlite'].poll() is not None:
                raise RuntimeError('StatLite exited; inspect statlite.log')
            try:
                get('http://127.0.0.1:9090/healthz')
                return
            except OSError:
                time.sleep(.1)
        raise RuntimeError('StatLite not ready')

    def app(self, name, directory):
        directory.mkdir()
        port, health, _, jar = APPS[name]
        env = dict(os.environ, SERVER_PORT=str(port), MARKET_DB_URL=f'jdbc:h2:file:{directory}/quotes;DB_CLOSE_ON_EXIT=FALSE')
        started = time.monotonic()
        p = self.launch(name, [self.java, *FLAGS, '-jar', str(self.bundle / jar)], directory, env)
        base = f'http://127.0.0.1:{port}'
        deadline = started + 30
        while time.monotonic() < deadline:
            if p.poll() is not None:
                raise RuntimeError(f'{name} exited: {p.returncode}')
            try:
                h = json.loads(get(base + health))
                latest = json.loads(get(base + '/api/quotes/latest'))
                if h.get('status') == 'UP' and len(latest) == 3:
                    elapsed = time.monotonic() - started
                    save(directory / 'readiness.json', dict(time=now(), pid=p.pid, seconds=elapsed, health=h, latest=latest))
                    self.event('ready', name=name, seconds=elapsed, latest=latest)
                    self.sample('readiness-' + name)
                    return
            except (OSError, ValueError):
                pass
            time.sleep(.05)
        raise RuntimeError(f'{name} readiness timeout')

    def snapshot(self, directory, names, label):
        destination = directory / label
        destination.mkdir()
        for name in names:
            port, health, metrics, _ = APPS[name]
            for key, path in [('health', health), ('metrics', metrics), ('latest', '/api/quotes/latest'), ('history', '/api/quotes/history')]:
                (destination / f'{name}-{key}.txt').write_bytes(get(f'http://127.0.0.1:{port}' + path))
        for name in [*APPS, 'statlite-self']:
            for kind in ['status', 'metrics', 'events']:
                (destination / f'statlite-{name}-{kind}.json').write_bytes(get(f'http://127.0.0.1:9090/api/v1/{kind}?target={name}'))
        self.sample(label)

    def smoke(self):
        directory = self.output / 'preparation'
        directory.mkdir()
        self.monitor(directory, 2)
        for name, (port, _, metrics, _) in APPS.items():
            appdir = directory / name
            self.app(name, appdir)
            get(f'http://127.0.0.1:{port}/api/quotes/history')
            exposition = get(f'http://127.0.0.1:{port}{metrics}').decode()
            for family in ['jvm_memory_used_bytes', 'http_server_requests_seconds_count']:
                if family not in exposition:
                    raise RuntimeError(f'{name} missing {family}')
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                status = json.loads(get(f'http://127.0.0.1:9090/api/v1/status?target={name}'))
                points = json.loads(get(f'http://127.0.0.1:9090/api/v1/metrics?target={name}'))['points']
                if status['collection_status'] == 'ok' and any(p['runtime_memory_bytes'] is not None for p in points):
                    break
                time.sleep(.5)
            else:
                raise RuntimeError(f'{name} collection failed: {status}')
            self.snapshot(appdir, [name], 'smoke-end')
            stop(self.processes.pop(name))
            self.event('smoke-passed', name=name)
        stop(self.processes.pop('statlite'))
        self.event('preparation-complete')

    def window(self, directory, names, duration, traffic):
        replay = self.observe_fixture(directory.name + '-start')
        # Read already captured readiness data; shared observation adds no app traffic.
        starting_batches = {}
        for name in names:
            appdir = directory / name if len(names) > 1 else directory
            starting_batches[name] = json.loads((appdir / 'readiness.json').read_text())['latest']
        save(directory / 'replay-start.json', dict(fixture=replay, first_persisted_batches=starting_batches))
        begin = time.monotonic()
        next_pair, next_sample, next_status = begin, begin, begin
        counts = dict(requests=0, errors=0)
        requests = (directory / 'requests.jsonl').open('a', buffering=1)
        states = (directory / 'monitor-status.jsonl').open('a', buffering=1)
        self.event('window-start', names=names, duration=duration, traffic=traffic, fixture=replay)
        while time.monotonic() - begin < duration:
            t = time.monotonic()
            elapsed = t - begin
            if t >= next_sample:
                self.sample(directory.name)
                next_sample += 5
                for name in names:
                    if self.processes[name].poll() is not None:
                        raise RuntimeError(f'{name} died during measurement')
            if t >= next_status:
                for name in [*APPS, 'statlite-self']:
                    states.write(json.dumps(dict(time=now(), target=name, status=json.loads(get(f'http://127.0.0.1:9090/api/v1/status?target={name}')))) + '\n')
                next_status += 10
            if traffic and t >= next_pair:
                port = APPS[names[0]][0]
                for path in ['/api/quotes/latest', '/api/quotes/history']:
                    request_start = time.monotonic()
                    try:
                        body = get(f'http://127.0.0.1:{port}' + path)
                        result = dict(bytes=len(body), ok=True)
                    except Exception as e:
                        counts['errors'] += 1
                        result = dict(ok=False, error=str(e))
                    counts['requests'] += 1
                    requests.write(json.dumps(dict(time=now(), elapsed=elapsed, path=path, seconds=time.monotonic()-request_start, **result)) + '\n')
                next_pair = t + (1 if 420 <= elapsed < 600 else 5)
            time.sleep(.05)
        requests.close()
        states.close()
        self.sample('window-end-' + directory.name)
        self.snapshot(directory, names, 'phase-end')
        save(directory / 'window.json', dict(start_monotonic=begin, end_monotonic=time.monotonic(), duration=duration, traffic=traffic, **counts))
        self.event('window-complete', names=names, **counts)

    def execute(self, duration):
        save(self.output / 'profile.json', dict(java=self.java, jvm_flags=FLAGS, polling_seconds=10, rss_sample_seconds=5, phase_seconds=duration, time=now()))
        self.launch('fixture', ['python3', '-u', str(self.bundle / 'fixture/server.py')], self.output)
        time.sleep(.5)
        (self.output / 'fixture-start.json').write_bytes(get('http://127.0.0.1:8090/quotes'))
        self.observe_fixture('fixture-start')
        self.smoke()
        measured = self.output / 'measurement'
        measured.mkdir()
        self.monitor(measured, 10)
        for name in APPS:
            directory = measured / name
            self.app(name, directory)
            self.window(directory, [name], duration, True)
            stop(self.processes.pop(name))
            self.event('stopped', name=name)
        shared = measured / 'shared'
        shared.mkdir()
        for name in APPS:
            self.app(name, shared / name)
        self.window(shared, list(APPS), duration, False)
        self.event('inspection-ready')
        (self.output / 'inspection-ready.txt').write_text(now() + '\n')
        # Keep children alive for operator inspection; collect final DB after shutdown.
        while True:
            self.sample('operator-inspection')
            time.sleep(10)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--java', default='/opt/jdbc-jdk/bin/java')
    p.add_argument('--duration', type=int, default=900, help='Use a shorter value only for rehearsal')
    a = p.parse_args()
    run = Run(a.bundle, a.output, a.java)
    try:
        run.execute(a.duration)
    except BaseException as e:
        run.event('runner-exit', error=repr(e))
        for proc in list(run.processes.values()):
            stop(proc)
        raise


if __name__ == '__main__':
    main()
