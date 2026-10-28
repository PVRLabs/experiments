# Adapted from ../boot-jdk27/serve.py; historical source remains unchanged.
#!/usr/bin/env python3
"""Launch one variant and sample raw process/host data until a stop file appears.

Use a fresh output directory. Orchestration stays explicit: workload runs on host,
phase labels come from OUTPUT/phase, and OUTPUT/stop requests exact cleanup.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request


HERE = Path(__file__).resolve().parent

def get(base, path):
    with urllib.request.urlopen(base + path, timeout=2) as r:
        return r.read()

def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--variant', choices=['native'], default='native')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-seconds', type=int, default=120)
    p.add_argument('--database', choices=['mariadb'], default='mariadb')
    p.add_argument('--monitor-pid', type=int, help='optional StatLite PID to sample')
    a = p.parse_args()
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS')):
        raise RuntimeError('clear ambient JVM options')
    if Path('/proc/swaps').read_text().splitlines()[1:]:
        raise RuntimeError('swap must be disabled')
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    args = [str(a.bundle.resolve() / 'market-replay-spring'), '-Xmx80m']
    env = dict(os.environ, TZ='UTC', SERVER_PORT='8080',
        MARKET_DB_URL='jdbc:mariadb://127.0.0.1:3306/market_replay',
        MARKET_FIXTURE_URL='http://127.0.0.1:8090/quotes',
        MARKET_POLL_INTERVAL_MS='60000', MARKET_POLL_INITIAL_DELAY_MS='0')
    app = fixture = None
    base = 'http://127.0.0.1:8080'
    (out / 'clock-ticks.txt').write_text(str(os.sysconf('SC_CLK_TCK'))+'\n')
    (out / 'boot-id.txt').write_text(Path('/proc/sys/kernel/random/boot_id').read_text())
    dbpid = None
    if a.database == 'mariadb':
        dbpid = int(subprocess.check_output(['systemctl', 'show', 'mariadb', '--property=MainPID', '--value'], text=True))
        if dbpid <= 0:
            raise RuntimeError('MariaDB is not running')
    begun = time.monotonic()
    kernel_start = subprocess.check_output(['sudo', 'journalctl', '-k', '-n', '0', '--show-cursor'], text=True)
    (out / 'kernel-cursor.txt').write_text(kernel_start)
    with (out / 'app.log').open('w') as log, (out / 'fixture.log').open('w') as flog, (out / 'samples.jsonl').open('w', buffering=1) as samples:
        def sample(phase):
            processes = {}
            for name, pid in [('app', app.pid if app else None),
                              ('mariadb', dbpid),
                              ('fixture', fixture.pid if fixture else None),
                              ('statlite', a.monitor_pid)]:
                if pid:
                    d = Path('/proc') / str(pid)
                    processes[name] = dict(pid=pid, status=(d/'status').read_text(), stat=(d/'stat').read_text())
            cgroup = Path('/sys/fs/cgroup/system.slice/mariadb.service')
            db_memory = {name: (cgroup/name).read_text() for name in ['memory.current', 'memory.peak', 'memory.events'] if dbpid and (cgroup/name).exists()}
            samples.write(json.dumps(dict(epoch=time.time(), monotonic=time.monotonic(), phase=phase,
                processes=processes, database_cgroup=db_memory, meminfo=Path('/proc/meminfo').read_text(),
                vmstat=Path('/proc/vmstat').read_text(),
                memory_psi=Path('/proc/pressure/memory').read_text(), host_cpu=Path('/proc/stat').read_text().splitlines()[0]))+'\n')
        try:
            fixture = subprocess.Popen(['python3', str(HERE/'fixture/server.py')], stdout=flog, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+10
            while True:
                if fixture.poll() is not None:
                    raise RuntimeError('fixture exited')
                try:
                    get('http://127.0.0.1:8090', '/quotes')
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(.05)
            sample('before-launch')
            started = time.monotonic()
            app = subprocess.Popen(args, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
            deadline = started+90
            while True:
                if app.poll() is not None:
                    raise RuntimeError('application exited; see app.log')
                sample('startup')
                try:
                    health = json.loads(get(base, '/actuator/health'))
                    latest = json.loads(get(base, '/api/quotes/latest'))
                    if health.get('status') == 'UP' and len(latest) == 3:
                        break
                except (OSError, ValueError):
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError('HTTP/persistence readiness timed out')
                time.sleep(.05)
            (out / 'ready.json').write_text(json.dumps(dict(seconds=time.monotonic()-started,
                epoch=time.time(), command=args, latest=latest), indent=2)+'\n')
            next_metrics = 0
            last_phase = None
            while not (out/'stop').exists() and time.monotonic()-begun < a.max_seconds:
                if app.poll() is not None or fixture.poll() is not None:
                    raise RuntimeError('application or fixture exited')
                phase = (out/'phase').read_text().strip() if (out/'phase').exists() else 'preparation-idle'
                transition = phase != last_phase
                sample('transition-to-'+phase if transition else phase)
                if time.monotonic() >= next_metrics:
                    if not transition:
                        with (out/'metrics.jsonl').open('a') as m:
                            m.write(json.dumps(dict(epoch=time.time(), phase=phase,
                                prometheus=get(base, '/actuator/prometheus').decode()))+'\n')
                    next_metrics = time.monotonic()+10
                last_phase = phase
                time.sleep(1)
            if not (out/'stop').exists():
                raise RuntimeError('collector safety deadline expired before host stop')
            for name, path in [('latest', '/api/quotes/latest'), ('history', '/api/quotes/history')]:
                (out/(name+'.json')).write_bytes(get(base, path))
        finally:
            (out/'host-final.json').write_text(json.dumps(dict(meminfo=Path('/proc/meminfo').read_text(),
                vmstat=Path('/proc/vmstat').read_text(), memory_psi=Path('/proc/pressure/memory').read_text()))+'\n')
            stop(app)
            stop(fixture)
            cursor = kernel_start.split('-- cursor: ')[-1].strip()
            subprocess.run(['sudo', 'journalctl', '-k', '--after-cursor='+cursor, '--no-pager'],
                stdout=(out/'kernel-after.log').open('w'), check=True)
    print(out)

if __name__ == '__main__':
    main()
