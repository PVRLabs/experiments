#!/usr/bin/env python3
"""Host-only tests: no VM or PostgreSQL server needed."""
from concurrent.futures import Future
import threading
import time
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from common import CONFIGS, ORDER, TIMELINE, check_busy_window, latency, pool_metrics, save, summarize_session
from runner import Runner, bundle_files


class HarnessTest(unittest.TestCase):
    def test_bundle_fingerprint_ignores_bytecode_but_detects_source_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            source = bundle / 'scripts/common.py'
            source.parent.mkdir()
            source.write_text('source v1')
            before = bundle_files(bundle)
            cache = source.parent / '__pycache__'
            cache.mkdir()
            (cache / 'common.cpython-312.pyc').write_bytes(b'cache v1')
            loose = source.parent / 'runner.pyc'
            loose.write_bytes(b'cache v1')
            (source.parent / 'legacy.pyo').write_bytes(b'optimized cache')
            self.assertEqual(bundle_files(bundle), before)
            (cache / 'common.cpython-312.pyc').write_bytes(b'cache v2')
            loose.unlink()
            self.assertEqual(bundle_files(bundle), before)
            source.write_text('source v2')
            self.assertNotEqual(bundle_files(bundle), before)

    def test_samples_keep_pool_values_and_only_occasional_or_failed_full_scrapes(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = Runner.__new__(Runner)
            runner.run = Path(temporary)
            runner.lock = __import__('threading').Lock()
            runner.monitor = None
            runner.event = Mock()
            runner.processes = {name: Mock(pid=pid, poll=Mock(return_value=None))
                                for name, pid in [('A', 101), ('B', 102)]}
            runner.connections = Mock(return_value=dict(A=10, B=10, aggregate=20))
            proc = {'/proc/meminfo': 'SwapTotal: 0 kB\nMemAvailable: 100000 kB\n',
                    '/proc/101/status': 'VmRSS: 50000 kB\n',
                    '/proc/102/status': 'VmRSS: 60000 kB\n'}
            def scrape(url):
                name = 'A' if ':8081/' in url else 'B'
                return '\n'.join(f'hikaricp_connections{suffix}{{pool="pool-{name}"}} {value}'
                                 for suffix, value in [('', 10), ('_active', 0), ('_idle', 10)]).encode()
            with patch.object(Path, 'read_text', new=lambda path: proc[str(path)]), \
                    patch('runner.get', side_effect=scrape) as get:
                routine = runner.sample(1)
                snapshot = runner.sample(30, full_metrics=True)
                failed = Future()
                failed.set_exception(PermissionError('optional smaps unavailable'))
                runner.memory_job = dict(future=failed, run=runner.run)
                unsupported_memory = runner.sample(31)
                get.side_effect = None
                get.return_value = b'malformed exposition'
                failure = runner.sample(31)
            for name in ['A', 'B']:
                self.assertEqual(routine['apps'][name]['pool'], dict(total=10, active=0, idle=10))
                self.assertNotIn('metrics_raw', routine['apps'][name])
                self.assertIn('metrics_raw', snapshot['apps'][name])
                self.assertEqual(failure['apps'][name]['metrics_raw'], 'malformed exposition')
            self.assertEqual(len(failure['errors']), 2)
            self.assertEqual(unsupported_memory['errors'], [])
            self.assertNotIn('pg_memory', unsupported_memory)
            self.assertIn('Optional PG memory', unsupported_memory['warnings'][0])
            saved = [json.loads(line) for line in (runner.run / 'samples.jsonl').read_text().splitlines()]
            self.assertNotIn('metrics_raw', saved[0]['apps']['A'])
            self.assertIn('metrics_raw', saved[1]['apps']['A'])

    def test_slow_optional_memory_never_blocks_or_stacks_workers(self):
        runner = Runner.__new__(Runner)
        runner.run = Path('scenario-one')
        entered, release = threading.Event(), threading.Event()
        def slow_memory():
            entered.set()
            release.wait(5)
            return {'pss_kib': 123}
        runner.pg_memory = Mock(side_effect=slow_memory)
        runner.event = Mock()
        row = {'warnings': []}
        try:
            runner.optional_pg_memory(row, requested=True)
            self.assertTrue(entered.wait(1))
            started = time.monotonic()
            for _ in range(10):
                runner.optional_pg_memory(row, requested=True)
            self.assertLess(time.monotonic() - started, .5)
            self.assertEqual(runner.pg_memory.call_count, 1)
            release.set()
            runner.memory_job['future'].result(timeout=1)
            runner.optional_pg_memory(row)
            self.assertEqual(row['pg_memory']['pss_kib'], 123)
            self.assertIn('collection_start_monotonic', row['pg_memory'])
            # Late results from another scenario must not contaminate this one.
            future = Future()
            future.set_result({'pss_kib': 999})
            runner.memory_job = dict(future=future, run=Path('previous'))
            other = {'warnings': []}
            runner.optional_pg_memory(other)
            self.assertNotIn('pg_memory', other)
        finally:
            release.set()

    def test_memory_safety_omits_monitor_then_rechecks_without_relaxing_thresholds(self):
        for minimum in [32 * 1024, 64 * 1024]:
            for recovered in [True, False]:
                runner = Runner.__new__(Runner)
                runner.monitor = Mock(poll=Mock(return_value=None))
                runner.output = Path('/unused')
                runner.event = Mock()
                def raw(available):
                    return f'SwapTotal: 0 kB\nMemAvailable: {available} kB\n'
                with patch.object(Path, 'read_text', side_effect=[raw(minimum - 1),
                        raw(minimum + 1 if recovered else minimum - 1)]), \
                        patch('runner.stop') as stopped, patch('runner.save'):
                    if recovered:
                        _, values = runner.safe_memory(minimum)
                        self.assertGreaterEqual(values['MemAvailable'], minimum)
                    else:
                        with self.assertRaises(RuntimeError):
                            runner.safe_memory(minimum)
                    stopped.assert_called_once_with(runner.monitor)
        runner.monitor = None
        with patch.object(Path, 'read_text', return_value=raw(100000).replace('SwapTotal: 0', 'SwapTotal: 1')):
            with self.assertRaises(RuntimeError):
                runner.safe_memory(32 * 1024)

    def test_actual_default_state_is_checked_and_mismatch_preserved(self):
        for actual_minimum in [10, 9]:
            with self.subTest(actual_minimum=actual_minimum), tempfile.TemporaryDirectory() as temporary:
                runner = Runner.__new__(Runner)
                runner.run = Path(temporary) / 'default-1'
                runner.run.mkdir()
                runner.bundle = Path(temporary)
                runner.config = dict(java='/unused/java', port=5432, role='test', password='unused')
                runner.database = 'test'
                runner.processes = {}
                runner.tags = lambda: dict(A='test-A', B='test-B')
                runner.event = Mock()
                runner.launch = Mock(return_value=Mock(pid=123, poll=Mock(return_value=None)))
                state = dict(instance='pool-A', applicationName='test-A', poolName='pool-A',
                             minimumIdle=actual_minimum, maximumPoolSize=10, idleTimeoutMs=0,
                             maxLifetimeMs=0, keepaliveMs=0, connectionTimeoutMs=5000, holdMs=1000)
                runner.state = Mock(return_value=state)
                with patch('runner.get', return_value=b'{"status":"UP"}'), patch.dict(
                        'os.environ', {'SPRING_DATASOURCE_HIKARI_MINIMUMIDLE': '10',
                                       'SPRING_APPLICATION_JSON': '{}', 'POOL_MIN_IDLE': '10'}):
                    if actual_minimum == 10:
                        runner.app_start('A', 'default')
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'Wrong resolved profile'):
                            runner.app_start('A', 'default')
                env = runner.launch.call_args.args[3]
                self.assertEqual(env['SPRING_PROFILES_ACTIVE'], 'default')
                self.assertNotIn('POOL_MIN_IDLE', env)
                self.assertNotIn('SPRING_DATASOURCE_HIKARI_MINIMUMIDLE', env)
                self.assertNotIn('SPRING_APPLICATION_JSON', env)
                evidence = json.loads((runner.run / 'A/readiness-123.json').read_text())
                self.assertEqual(evidence['state']['minimumIdle'], actual_minimum)
                self.assertEqual(evidence['sizing_overrides'], {})
        self.assertEqual(CONFIGS['default']['sizing_overrides'], {})
        self.assertEqual(ORDER, ['default-1', 'no-reclaim-1', 'reclaim-1',
                                 'reclaim-2', 'no-reclaim-2', 'default-2'])

    def test_optional_warnings_do_not_trip_sampler_but_connection_errors_do(self):
        for errors, should_fail in [([], False), (['PG attribution unavailable'], True)]:
            runner = Runner.__new__(Runner)
            runner.origin = 0
            runner.sampler_error = None
            runner.sampler_stop = Mock()
            runner.sampler_stop.is_set.side_effect = [False, False, False, True]
            runner.sample = Mock(return_value={'errors': errors, 'warnings': ['Optional PG memory missing']})
            runner.event = Mock()
            runner.sample_loop()
            self.assertEqual(runner.sampler_error is not None, should_fail)

    def test_missing_monitor_is_best_effort_and_no_snapshots_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = Runner.__new__(Runner)
            runner.output = Path(temporary)
            runner.monitor = None
            runner.event = Mock()
            runner.monitor_start = Mock(side_effect=RuntimeError('StatLite unavailable'))
            runner.monitor_start_best_effort()
            status = json.loads((runner.output / 'statlite/status.json').read_text())
            self.assertEqual(status['status'], 'unavailable')
            runner.snapshots()
            runner.event.assert_called_with('optional-monitor-snapshots-unavailable')

    def test_execution_can_finish_without_statlite_or_manual_UI_checks(self):
        for mode in ['smoke', 'record']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                runner = Runner.__new__(Runner)
                runner.output = Path(temporary)
                preflight = runner.output / 'input-preflight.json'
                save(preflight, dict(automated_pass=True, environment_acknowledged=True,
                                     manual_ui_checked=False, fingerprint={}))
                runner.args = Mock(mode=mode, preflight=preflight)
                runner.monitor = None
                runner.monitor_status = {'status': 'unavailable'}
                runner.clean, runner.monitor_start_best_effort, runner.scenario, runner.event = Mock(), Mock(), Mock(), Mock()
                runner.environment = Mock(return_value={})
                runner.execute()
                self.assertEqual(runner.scenario.call_count, 3 if mode == 'smoke' else 6)
                self.assertTrue((runner.output / 'measurement-complete.txt').exists())
                if mode == 'smoke':
                    result = json.loads((runner.output / 'preflight.json').read_text())
                    self.assertTrue(result['automated_pass'])
                    self.assertEqual(result['statlite']['status'], 'unavailable')

    def test_preflight_acknowledgement_does_not_require_a_dashboard(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'preflight.json'
            save(path, dict(automated_pass=True, fingerprint={}))
            subprocess.run([sys.executable, str(Path(__file__).with_name('ack-preflight.py')),
                            str(path), '--checked-vm-clock-and-1gib-config'],
                           check=True, capture_output=True)
            result = json.loads(path.read_text())
            self.assertTrue(result['environment_acknowledged'])
            self.assertFalse(result['manual_ui_checked'])

    def test_pool_metrics_ignore_other_instance_and_require_all_series(self):
        raw = '\n'.join(f'hikaricp_connections{suffix}{{pool="pool-A"}} {value}'
                        for suffix, value in [('', 10), ('_active', 8), ('_idle', 2)])
        raw += '\nhikaricp_connections{pool="pool-B"} 1\n'
        self.assertEqual(pool_metrics(raw, 'pool-A'), dict(total=10, active=8, idle=2))
        with self.assertRaises(ValueError):
            pool_metrics(raw, 'pool-B')

    def test_pg_attribution_excludes_other_names_roles_and_databases(self):
        runner = Runner.__new__(Runner)
        runner.config = {'role': 'pool_reclaim'}
        runner.database = 'pool_reclaim'
        runner.tags = lambda: dict(A='exact-A', B='exact-B')
        runner.pg_rows = lambda: [dict(datname=db, usename=user, application_name=name, pid=i)
                                 for i, (db, user, name) in enumerate([
                                     ('pool_reclaim', 'pool_reclaim', 'exact-A'),
                                     ('pool_reclaim', 'pool_reclaim', 'exact-B'),
                                     ('pool_reclaim', 'pool_reclaim', 'exact-A-other'),
                                     ('pool_reclaim', 'postgres', 'exact-A'),
                                     ('pool_reclaim_smoke', 'pool_reclaim', 'exact-B'),
                                     ('pool_reclaim', 'postgres', 'pool-observer')])]
        self.assertEqual(runner.connections()['aggregate'], 2)
        self.assertEqual(runner.connections()['A'], 1)
        self.assertEqual(runner.connections()['B'], 1)

    def test_summary_uses_comparable_windows_and_keeps_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = Path(temporary)
            run = session / 'reclaim-1'
            run.mkdir()
            save(run / 'run.json', dict(configuration='reclaim', mode='record', status='valid'))
            rows = []
            for elapsed, a, b, available in [(-5, 1, 1, 100000), (18, 10, 10, 80000),
                                             (60, 1, 10, 90000), (120, 1, 1, 110000)]:
                rows.append(dict(elapsed=elapsed, host={'MemAvailable': available},
                                 pg=dict(A=a, B=b, aggregate=a + b),
                                 apps={name: dict(rss_kib=102400, pool=dict(active=0, idle=n, total=n))
                                       for name, n in [('A', a), ('B', b)]}, errors=[]))
            (run / 'samples.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
            with (run / 'requests.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['instance', 'stage', 'elapsed_ms', 'error', 'acquisition_ms'])
                writer.writeheader()
                writer.writerow(dict(instance='A', stage='burst', elapsed_ms=1001, error='', acquisition_ms=1))
                writer.writerow(dict(instance='B', stage='revisit', elapsed_ms=2000, error='timeout', acquisition_ms=99))
            summary = summarize_session(session)[0]
            self.assertEqual(summary['initial_pg_aggregate'], 2)
            self.assertEqual(summary['peak_aggregate_pg'], 20)
            self.assertEqual(summary['B_busy_A_idle_pg_aggregate'], 11)
            self.assertEqual(summary['both_quiet_pg_aggregate'], 2)
            self.assertEqual(summary['overall_errors'], 1)
            self.assertIsNone(summary['both_quiet_pg_pss_kib_mib'])
            self.assertNotIn('quiet_delta_available_mib', summary)
            self.assertEqual(summary['mechanism_status'], 'not-recorded')
            self.assertEqual(summary['overall_successes'], 1)
            self.assertEqual(summary['overall_max_ms'], 1001)
            self.assertEqual(summary['overall_failed_max_ms'], 2000)
            self.assertIsNone(summary['B_revisit_median_ms'])
            self.assertIsNone(summary['B_revisit_borrow_max_ms'])
            self.assertTrue((session / 'summary.csv').exists())

    def test_latency_excludes_failures_and_handles_all_failed(self):
        rows = [dict(elapsed_ms=10, error=''), dict(elapsed_ms=20, error=''),
                dict(elapsed_ms=15000, error='timeout')]
        result = latency(rows)
        self.assertEqual((result['n'], result['successes'], result['errors']), (3, 2, 1))
        self.assertEqual((result['median_ms'], result['p95_ms'], result['max_ms']), (15, 20, 20))
        self.assertEqual(result['failed_max_ms'], 15000)
        self.assertIsNone(latency(rows[2:])['max_ms'])
        self.assertEqual(latency([])['n'], 0)

    @staticmethod
    def busy_samples(a=1, b=10, b_active=10):
        return [dict(elapsed=offset, pg=dict(A=a, B=b, aggregate=a + b),
                     apps=dict(A=dict(pool=dict(total=a, active=0, idle=a)),
                               B=dict(pool=dict(total=b, active=b_active, idle=b - b_active))))
                for offset in range(58, 68)]

    def test_mechanism_requires_reclaim_while_B_still_expanded(self):
        self.assertEqual(check_busy_window(self.busy_samples(), 'reclaim')['status'], 'passed')
        for configuration in ['default', 'no-reclaim']:
            self.assertEqual(check_busy_window(self.busy_samples(a=10), configuration)['status'], 'passed')
            self.assertEqual(check_busy_window(self.busy_samples(), configuration)['status'], 'failed')
        for samples in [self.busy_samples(a=10), self.busy_samples(b=1, b_active=1),
                        self.busy_samples(b_active=0), self.busy_samples()[:4], []]:
            self.assertEqual(check_busy_window(samples, 'reclaim')['status'], 'failed')
        samples = self.busy_samples(a=10)
        samples += [dict(elapsed=120, pg=dict(A=1, B=1, aggregate=2))]
        self.assertEqual(check_busy_window(samples, 'reclaim')['status'], 'failed')
        samples = self.busy_samples()
        del samples[0]['apps']['A']['pool']
        self.assertEqual(check_busy_window(samples, 'reclaim')['status'], 'failed')
        samples = self.busy_samples()
        samples[0]['pg']['A'] = 10
        self.assertEqual(check_busy_window(samples, 'reclaim')['status'], 'failed')

    def test_runner_records_failed_mechanism_before_rejecting_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = Runner.__new__(Runner)
            runner.run = Path(temporary)
            runner.lock = __import__('threading').Lock()
            runner.event = Mock()
            (runner.run / 'samples.jsonl').write_text(''.join(
                json.dumps(row) + '\n' for row in self.busy_samples(a=10)))
            with self.assertRaisesRegex(RuntimeError, 'mechanism check failed'):
                runner.verify_busy_window('reclaim')
            check = json.loads((runner.run / 'mechanism-check.json').read_text())
            self.assertEqual(check['status'], 'failed')
            self.assertEqual(check['complete_samples'], 10)
            self.assertEqual(runner.event.call_args.kwargs['status'], 'failed')

    def test_reclaim_smoke_checks_same_post_A_idle_timing_and_rejects_late_reclaim(self):
        for a, expected in [(1, 'passed'), (10, 'failed')]:
            with self.subTest(a=a), tempfile.TemporaryDirectory() as temporary:
                runner = Runner.__new__(Runner)
                runner.run = Path(temporary)
                runner.lock = __import__('threading').Lock()
                runner.event = Mock()
                runner.burst = Mock()
                samples = self.busy_samples(a=a)
                for sample in samples:
                    sample['elapsed'] -= 8
                # Eventual both-idle shrink cannot rescue a failed B-busy check.
                samples.append(dict(elapsed=100, pg=dict(A=1, B=1, aggregate=2)))
                (runner.run / 'samples.jsonl').write_text(''.join(
                    json.dumps(row) + '\n' for row in samples))
                if expected == 'failed':
                    with self.assertRaisesRegex(RuntimeError, 'mechanism check failed'):
                        runner.smoke_bursts('reclaim')
                else:
                    runner.smoke_bursts('reclaim')
                runner.burst.assert_any_call('A', 0, 8)
                runner.burst.assert_any_call('B', 6, 60)
                self.assertEqual(runner.burst.call_count, 2)
                check = json.loads((runner.run / 'mechanism-check.json').read_text())
                self.assertEqual(check['status'], expected)
                self.assertEqual(check['window'], [50, 60])
                self.assertEqual(check['complete_samples'], 10)
                self.assertEqual([t - 8 for t in check['window']],
                                 [t - TIMELINE['A_end'] for t in [58, 68]])

    def test_control_smoke_keeps_short_bursts(self):
        for configuration in ['default', 'no-reclaim']:
            runner = Runner.__new__(Runner)
            runner.event, runner.burst, runner.verify_busy_window = Mock(), Mock(), Mock()
            runner.smoke_bursts(configuration)
            runner.burst.assert_any_call('A', 0, 8)
            runner.burst.assert_any_call('B', 6, 10)
            runner.verify_busy_window.assert_not_called()

    def test_overlap_requires_elevated_actual_occupancy(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = Runner.__new__(Runner)
            runner.run = Path(temporary)
            runner.event = Mock()
            path = runner.run / 'acquisition.jsonl'
            rows = [dict(instance=name, stage='burst', payload=dict(acquiredMs=start, returnedMs=end))
                    for name, start, end in [('A', 0, 1000), ('B', 500, 1500)] for _ in range(10)]
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            runner.verify_overlap()
            self.assertEqual(runner.event.call_args.kwargs['peak_holders'], 20)
            for row in rows:
                if row['instance'] == 'B':
                    row['payload']['acquiredMs'] = 1100
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            with self.assertRaises(RuntimeError):
                runner.verify_overlap()

    def test_early_launch_failure_keeps_invalid_summary_and_original_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = Runner.__new__(Runner)
            runner.output = Path(temporary)
            runner.args = Mock(mode='record')
            runner.args.session = 'test'
            runner.clean = Mock()
            runner.event = Mock()
            runner.processes = {}
            runner.sampler_stop = __import__('threading').Event()
            runner.scenario_abort = __import__('threading').Event()
            runner.app_start = Mock(side_effect=RuntimeError('application launch failed'))
            with self.assertRaisesRegex(RuntimeError, 'application launch failed'):
                runner.scenario('default-1')
            metadata = json.loads((runner.output / 'default-1' / 'run.json').read_text())
            self.assertEqual(metadata['status'], 'invalid')
            self.assertEqual(metadata['error'], 'application launch failed')
            self.assertTrue((runner.output / 'summary.csv').exists())

    def test_timeline_has_small_overlap_and_reclaim_margin(self):
        self.assertEqual(TIMELINE['A_end'] - TIMELINE['B_start'], 4)
        self.assertGreaterEqual(TIMELINE['B_end'] - TIMELINE['A_end'], 50)
        self.assertEqual(TIMELINE['quiet_end'] - TIMELINE['B_end'], 60)


if __name__ == '__main__':
    unittest.main()
