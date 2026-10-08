# Recorded paired result

Both variants started and completed all 1,500 requests correctly under the fixed
five-request/second workload. Both meet the original [METHOD.md](METHOD.md)
thresholds. Spring's sustained-paging pass must be read alongside its substantial
swap activity: successful operation here does not establish comfortable operation
with little memory pressure.

| Recorded metric | Javalin shaded JAR | Spring extracted layout |
|---|---:|---:|
| Startup to readiness | 2.46 s | 9.89 s |
| Successful workload requests | 1,500 / 1,500 | 1,500 / 1,500 |
| External request p95 | 6.09 ms | 8.39 ms |
| Workload median Java RSS | 106.43 MiB | 118.56 MiB |
| Minimum workload MemAvailable | 69.76 MiB | 45.28 MiB |
| Workload swap-in / swap-out | 0.32 / 0.00 MiB | 27.23 / 31.77 MiB |
| Maximum idle/load/recovery swap occupancy | 23.82 MiB | 100.02 MiB |

## Paging interpretation

Spring did not sustain more than 1 MiB/s paging for 30 seconds, so the predeclared
limited-paging criterion passes unchanged. Nevertheless, approximately 100 MiB
of swap occupancy on a guest exposing 214.89 MiB of RAM, plus repeated page-ins
and page-outs during traffic, is operationally significant. Startup also paged
substantially. Available-memory headroom and responsive requests coexist with
this pressure; resident RSS alone understates the memory demands of the run.
Swap occupancy and paging volume measure different things and should both be
reported. This workload did not demonstrate unacceptable latency from paging,
but it does not establish resilience to heavier traffic, different storage,
longer operation or less swap.

Javalin had much less workload paging in the observed run. This is a result for
the tested complete applications, JVM policy, monitoring and guest, rather than
a general framework ranking or minimum-memory comparison.

## Targeted follow-up before a strong comfort claim

Recommend one Spring-only repeat using the same frozen release, JVM flags,
fixture, monitor cadence and workload after the normal clean VM reset, zero-swap
preflight and fresh H2/SQLite storage. Compare startup, workload and recovery
paging/occupancy, headroom and latency with this original run. Preserve both runs
and record any environmental deviations. This tests whether the observed paging
recurs; one repeat still offers limited reproducibility evidence. No repeat has
been performed, and no strong low-pressure comfort claim is supported now.

## Evidence and limits

- [Javalin analysis](results/run-20261008T212522Z-javalin/analysis.json)
- [Spring analysis](results/run-20261008T221334Z-spring/analysis.json)
- [Spring screenshots and captions](results/run-20261008T221334Z-spring/screenshots/README.md)
- [Method and execution notes](METHOD.md)

One run per variant, fixed Javalin-then-Spring order and a short workload limit
interpretation. Paging totals are deltas between sampled endpoints within each
phase, rather than exact boundary counters. Original Javalin CPU samples lack
steal, so exact busy utilization remains unavailable; the corrected busy-plus-steal
upper bound is separate from I/O wait. Spring records steal explicitly. Current
screenshot cards and history after cutoff are inspection state, not measured
phase evidence. Raw archived inputs and criteria remain unchanged.
