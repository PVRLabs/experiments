"""Evidence checks for the fixed 512 MiB protocol; partial runs remain inspectable."""
from decimal import Decimal
import math
import statistics

PHASES = ['baseline', 'startup', 'idle', 'workload', 'recovery', 'measurement-cutoff']


def sampling_coverage(meta, phases, samples):
    expected = list(PHASES)
    if meta.get('monitored'):
        expected.insert(1, 'monitor-only')
    issues = []
    if [p['phase'] for p in phases] != expected:
        issues.append('Missing, repeated, or out-of-order protocol phases')
    times = [s['epoch'] for s in samples]
    if any(not math.isfinite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        issues.append('OS sample timestamps must be finite and strictly increasing')
    reports = {}
    def cadence_for(name):
        return 1 if name == 'startup' or (meta['smoke'] and name not in ('baseline', 'monitor-only')) else 5
    for index, (left, right) in enumerate(zip(phases, phases[1:])):
        name = left['phase']
        begin, end = left['epoch'], right['epoch']
        duration = end - begin
        cadence = cadence_for(name)
        # Allow scheduling jitter, but reject a missed regular interval.
        limit = cadence * 1.5 + 0.5
        inside = [s['epoch'] for s in samples if begin <= s['epoch'] < end]
        before = [s['epoch'] for s in samples if s['epoch'] < begin]
        after = [s['epoch'] for s in samples if s['epoch'] >= end]
        phase_issues = []
        # A cross-boundary gap can include time spent at the old cadence.
        # Check only within-phase intervals; bound each boundary separately.
        gaps = [b-a for a,b in zip(inside,inside[1:])]
        start_gap = max(0, (inside or after or [end])[0] - begin)
        end_gap = max(0, end - (inside or before or [begin])[-1])
        minimum = max(1, math.floor(max(0, duration) / cadence * 0.8))
        if duration <= 0:
            phase_issues.append('Nonpositive phase duration')
        previous_cadence=cadence_for(phases[index-1]['phase']) if index else cadence
        next_cadence=cadence_for(right['phase']) if right['phase'] != 'measurement-cutoff' else cadence
        bracketed = (duration < cadence and before and after
                     and begin-before[-1] <= previous_cadence*1.5+0.5
                     and after[0]-end <= next_cadence*1.5+0.5)
        if not bracketed and (start_gap > limit or end_gap > limit):
            phase_issues.append('Missing samples near a phase boundary')
        inside_gaps=[b-a for a,b in zip(inside,inside[1:])]
        if duration >= cadence*3 and inside_gaps and statistics.median(inside_gaps) < cadence*0.75:
            phase_issues.append('OS sampling cadence is faster than the protocol')
        if gaps and max(gaps) > limit:
            phase_issues.append('OS sampling gap exceeds cadence tolerance')
        # Very short startup may lie between adjacent samples; require a close bracket.
        if len(inside) < minimum and not bracketed:
            phase_issues.append('Insufficient OS sample count')
        if not meta['smoke']:
            required = {'baseline':30, 'idle':30, 'recovery':30, 'workload':299.8, 'monitor-only':90}.get(name)
            if required and duration < required - 0.5:
                phase_issues.append('Phase shorter than required protocol duration')
        reports[name] = dict(valid=not phase_issues, issues=phase_issues, sample_count=len(inside),
                             expected_cadence_seconds=cadence, maximum_allowed_gap_seconds=limit,
                             maximum_observed_gap_seconds=max(gaps, default=None),
                             start_gap_seconds=start_gap, end_gap_seconds=end_gap)
        issues.extend(f'{name}: {reason}' for reason in phase_issues)
    return dict(valid=not issues, issues=issues, phases=reports)


def workload_and_state(meta, events, state, fixture):
    count = 15 if meta['smoke'] else 1500
    indexes = [e.get('index') for e in events]
    completed = sum('completed_epoch' in e and 'latency_ms' in e for e in events)
    errors = sum(not e.get('ok', False) for e in events)
    workload_valid = (len(events) == count and completed == count and errors == 0
                      and sorted(i for i in indexes if isinstance(i, int)) == list(range(count)))
    price_sum = sum((Decimal(str(v)) for batch in fixture for v in batch['prices'].values()), Decimal(0))
    def expected(batches):
        return dict(rows=1170+3*len(batches), maxSequence=389+max((i+1 for i in batches), default=0),
                    priceSum=price_sum+sum((Decimal(str(v)) for i in batches for v in fixture[i]['prices'].values()), Decimal(0)))
    fixed = expected(list(range(count//5)))
    if not meta['smoke']:
        fixed = dict(rows=2070, maxSequence=689, priceSum=Decimal('630374.22'))
    acknowledged = sorted({e['index']//5 for e in events if e.get('ok') and e.get('route') == 'batch'
                           and isinstance(e.get('index'), int) and 0 <= e['index']//5 < len(fixture)})
    partial = expected(acknowledged)
    def matches(target):
        return state is not None and all(Decimal(str(state.get(k))) == Decimal(str(v)) for k, v in target.items() if k in state) and all(k in state for k in target)
    def serial(values):
        return {k:str(v) if isinstance(v, Decimal) else v for k,v in values.items()}
    persistence = dict(actual=serial(state) if state is not None else None,
                       expected_rows=fixed['rows'], expected_max_sequence=fixed['maxSequence'],
                       expected_price_sum=str(fixed['priceSum']), matches=matches(fixed),
                       acknowledged_writes_expected=serial(partial),
                       matches_acknowledged_writes=matches(partial),
                       diagnostic_note='Acknowledged writes use actual batch indexes; a failed HTTP response may still have committed. Partial consistency does not establish experiment success.')
    return dict(valid=workload_valid, expected_requests=count, recorded_requests=len(events),
                completed_requests=completed, errors=errors), persistence
