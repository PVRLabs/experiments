#!/usr/bin/env python3
"""Host preparation checks only. Does not launch a VM or measured workload."""
import argparse
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {
    'jdbi3': ('RepositoryCheck.java', 'RepositoryCheck'),
    'mybatis': ('MyBatisRepositoryCheck.java', 'lab.MyBatisRepositoryCheck'),
    'jooq': ('JooqRepositoryCheck.java', 'lab.JooqRepositoryCheck'),
}
FLAGS = ['-Xms16m', '-Xmx80m', '-XX:+UseSerialGC', '-Xss512k']


def command(args, log, **kwargs):
    with log.open('w') as output:
        result = subprocess.run(args, stdout=output, stderr=subprocess.STDOUT, **kwargs)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}); see {log}')


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise RuntimeError('Application required forced shutdown')


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def check_http(variant, jar, result, workload, smoke):
    port = free_port()
    database = result/'http-db'
    database.mkdir()

    def fetch(path):
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
        try:
            return workload.request(connection, 'GET', path)
        finally:
            connection.close()

    def launch(log):
        process = subprocess.Popen(
            ['java', *FLAGS, f'-Drun.dir={database}', f'-Dapp.port={port}', '-jar', str(jar)],
            stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and process.poll() is None:
            try:
                if fetch('/ready') == (200, {'status': 'UP'}):
                    return process
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(.1)
        stop(process)
        raise RuntimeError(f'{variant}: readiness failed; inspect app log')

    with (result/'http.log').open('w') as log:
        process = launch(log)
        try:
            status, initial = fetch('/inspection/state')
            assert status == 200 and initial['rows'] == 1170, initial
            events = workload.run(port, result/'smoke-http.jsonl', 15)
            summary = workload.summarize(events)
            assert summary['overall']['errors'] == 0, summary
            # Existing contract checks include validation, duplicates, metrics
            # exclusions, mapping and ordering. This is preparation traffic.
            smoke.check('javalin-' + variant, result, port=port)
            status, state = fetch('/inspection/state')
            assert status == 200 and state['rows'] == 1179, state
        finally:
            stop(process)
    with (result/'reopen.log').open('w') as log:
        process = launch(log)
        try:
            assert fetch('/inspection/state') == (200, state), 'Reopened state changed'
        finally:
            stop(process)

    # A startup bind failure must release the pool and exit without hanging.
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        occupied = listener.getsockname()[1]
        with (result/'startup-failure.log').open('w') as log:
            process = subprocess.Popen(
                ['java', *FLAGS, f'-Drun.dir={database}', f'-Dapp.port={occupied}', '-jar', str(jar)],
                stdout=log, stderr=subprocess.STDOUT)
            try:
                code = process.wait(timeout=40)
                assert code != 0, 'Occupied listener should fail startup'
            finally:
                stop(process)
        assert 'Shutdown completed' in (result/'startup-failure.log').read_text(), 'Pool did not close'
    return {'smoke_requests': 15, 'request_errors': 0, 'restart_persistence': True,
            'startup_failure_cleanup': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=ROOT,
                        help='Directory containing workload.py, smoke.py and the common fixture')
    parser.add_argument('--variant', choices=VARIANTS, action='append')
    args = parser.parse_args()
    sys.path.insert(0, str(args.reference.resolve()))
    import workload
    import smoke
    summary = {}
    for variant in args.variant or VARIANTS:
        module = ROOT/('javalin-' + variant)
        jar = (module/'target'/f'javalin-{variant}-1.0.jar').resolve()
        if not jar.is_file():
            raise FileNotFoundError(f'Build first: {jar}')
        # Never reuse test databases; retain every check attempt separately.
        import tempfile
        result = Path(tempfile.mkdtemp(prefix='preparation-', dir=module/'target'))
        classes = result/'classes'
        classes.mkdir()
        source, main_class = VARIANTS[variant]
        command(['javac', '-cp', str(jar), '-d', str(classes), str(ROOT/'checks'/source),
                 str(ROOT/'checks'/variant/'FixtureRecoveryCheck.java')], result/'compile.log')
        classpath = str(classes) + os.pathsep + str(jar)
        command(['java', *FLAGS, '-cp', classpath, main_class, str(result/'repository-db')],
                result/'repository.log', timeout=60)
        command(['java', *FLAGS, '-cp', classpath, 'lab.FixtureRecoveryCheck', str(result/'fixture-db')],
                result/'fixture.log', timeout=60)
        details = check_http(variant, jar, result, workload, smoke)
        details.update(repository_checks=True, fixture_failure_recovery=True)
        (result/'summary.json').write_text(json.dumps(details, indent=2) + '\n')
        summary[variant] = details
        print(f'PASS {variant}: repositories, fixture failures, HTTP contract, restart, startup cleanup', flush=True)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
