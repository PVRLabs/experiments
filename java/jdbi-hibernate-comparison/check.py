#!/usr/bin/env python3
"""Check the published accepted-run evidence and reproduce its phase summaries."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from benchmark import verify_state
from analyze import analyze

variants = {'spring-jpa', 'coilbase-jdbi', 'coilbase-hibernate'}
for mode in ('original', 'extended'):
    folders = sorted((ROOT / 'results' / mode).glob('*/metadata.json'))
    assert len(folders) == 6, f'{mode}: expected six accepted runs'
    counts = {v: 0 for v in variants}
    for path in folders:
        d = json.loads(path.read_text())
        samples = json.loads((path.parent / 'samples.json').read_text())
        requests = json.loads((path.parent / 'requests.json').read_text())
        state = json.loads((path.parent / 'database-state.json').read_text())
        assert d['mode'] == mode and d['variant'] in variants
        counts[d['variant']] += 1
        assert d['source'] == '912c7bdf8ef6009d2dba3679d3ddafa34646e5bb'
        assert d['acceptance'] == {'accepted': True, 'reasons': []}
        assert d['completed'] and d['application_exit_before_shutdown'] is None
        assert d['persistence_verification']['passed']
        assert not verify_state(state, d['expected_generations'], d['refresh_windows'])
        assert d['oom_kill_before'] == d['oom_kill_after']
        assert d['kernel_log_access_exit_code'] == 0 and d['jstat_failures'] == 0
        assert d['sql_and_heap']['queries']
        assert samples and all('VmRSS_kib' in s and 'Pss_kib' in s and 'VmSwap_kib' in s for s in samples)
        assert all(s['VmSwap_kib'] == 0 for s in samples)
        assert requests and all(r['status'] == 200 for r in requests)
        required = {'startup', 'warmup', 'sample'} if mode == 'original' else {'startup', 'idle', 'warmup', 'mixed', 'recovery'}
        assert required <= {s['phase'] for s in samples}
        summary = analyze(path.parent)
        phase = 'sample' if mode == 'original' else 'mixed'
        dash = summary['phases'][phase]['requests']['/']
        assert dash['count'] == (12 if mode == 'original' else 300)
        print(f"{mode:8} {path.parent.name:32} RSS={summary['phases'][phase]['VmRSS_kib']['median']/1024:.1f} MiB dashboard p50/p95={dash['p50_ms']:.1f}/{dash['p95_ms']:.1f} ms")
    assert all(n == 2 for n in counts.values()), counts
print('PASS: 12 accepted runs, sample coverage, SQL, OOM counters and committed state')
