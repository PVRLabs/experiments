# Spring JDBC and CoilBase/Jex on a 256 MiB Alpine VM

A focused follow-up to the [original Javalin/Spring experiment](https://github.com/PVRLabs/experiments/tree/main/javalin/vps-256mb), recorded on 2026-11-06.
Both completed 1,500 correct requests. CoilBase/Jex used about 31 MiB less median
application RSS and retained about 36 MiB more minimum system headroom. Both
paged; this is one run per stack under a modest quote-API workload.

Spring Boot 4.1.1 uses Spring MVC, Spring JDBC (NamedParameterJdbcTemplate),
Spring-managed service transactions and Actuator. CoilBase 0.1.0-preview3 uses
Avaje Jex 3.6, generated annotated-controller routes, Jdbi 3.55.0 through
RepositoryContext and explicit service transactions. Both use matching
controller/service/repository organization, SQL, domain records and validation.
This is a complete-stack comparison; it does not isolate any library's overhead.

| Metric | Spring JDBC | Jex + CoilBase/Jdbi |
|---|---:|---:|
| Startup to readiness (s) | 9.35 | 2.42 |
| Median workload application RSS (MiB) | 125.97 | 94.81 |
| Peak workload application RSS (MiB) | 130.76 | 101.03 |
| Minimum idle/load/recovery MemAvailable (MiB) | 43.22 | 79.15 |
| Maximum idle/load/recovery swap occupancy (MiB) | 104.14 | 22.93 |
| Workload swap-in (MiB) | 26.36 | 7.83 |
| Workload swap-out (MiB) | 26.78 | 10.28 |
| External HTTP p95 (ms) | 9.45 | 6.12 |
| Maximum request latency (ms) | 187.24 | 422.82 |
| Maximum dispatch lag (ms) | 54.28 | 10.24 |
| Workload host busy CPU (%) | 4.28 | 2.85 |
| Correct requests | 1500 / 1,500 | 1500 / 1,500 |

Paging volumes are VM-wide `/proc/vmstat` counters; they do not attribute all
traffic to the application.

RSS is resident process memory, including embedded H2, rather than heap or a
framework minimum. Paging volume and swap occupancy are different measurements.
Low RSS while swapped is not evidence of a small required memory footprint.
HTTP latency includes the local SSH tunnel. These observations are one run each.

## Method

Alpine 3.24.2 x86-64 on an Intel macOS Lima/VZ local VM, one vCPU, 256 MiB
allocated RAM (214.89 MiB guest MemTotal), 4 GiB disk, 512 MiB disk swap,
swappiness 60. OpenJDK 25.0.4+7-alpine-r0 with explicit Serial GC,
`-Xms16m -Xmx80m -Xss512k`; GC logs confirm Serial. No AOT/native compilation,
CDS training or workload-specific tuning. Spring uses official tools-mode
extraction performed on the host; CoilBase uses a manifest-classpath JAR plus
libraries. H2 2.4.240 is file-backed with 4 MiB cache and default 500ms write delay;
HikariCP 7.0.2 has one minimum idle/two maximum connections. H2 memory is part of
application RSS. Commit checks do not certify crash durability.

Both apps expose latest/history reads and atomic three-symbol quote batch writes.
The checked-in CSV has 390 one-minute samples for each of AAPL, GOOG and NVDA,
retained from the original experiment. No external service is called at runtime.
Each run uses fresh DB/monitor storage after rebooting the same guest. Preflight
hash verification reads application files, so startup is not cold-disk startup.
No business workload warmup is carried into measurement. Baseline 60s,
StatLite-only 90s, startup probes every 100ms, idle 180s, traffic 300s,
recovery 120s. Original StatLite 0.6.0 polls every 30s. OS samples are one second
at startup and five seconds otherwise, including CPU steal and paging counters.

Traffic schedules 1,500 slots at 200ms intervals: 80% GET latest/history
(60 rows), 20% POST three-symbol batches. Persistent HTTP/1.1, at most four
outstanding, no retries; statuses and payloads are validated. Correct final state
is 2,070 rows, maximum sequence 689 and price sum 630374.22. Preparation checked
invalid inputs, conflict rollback after earlier inserts, subsequent transaction
recovery and persistence reopening. Preparation is separate from result data.

Spring ran first, CoilBase second. Monitoring and application writers were stopped
before collecting their storage. Operator dashboard inspection was explicitly
skipped. Public evidence contains OS/HTTP/phase/probe/state/GC records and analysis;
private captures, databases, generated binaries and agent logs are excluded.

## Predeclared numeric checks

These retain the original experiment's thresholds. Passing them does not by
itself establish comfortable, low-pressure operation; report paging independently.
Recovery memory/headroom trends remain visible in the per-phase analyses.

| Check | Spring JDBC | Jex + CoilBase/Jdbi |
|---|---|---|
| Ready within 60s | Pass | Pass |
| All 1,500 requests and persisted state correct | Pass | Pass |
| At least 24 MiB settled headroom | Pass | Pass |
| Inherited 8 MiB minute-3-to-5 growth cutoff | Within cutoff | Exceeded cutoff |
| No >1 MiB/s paging sustained for 30s | Pass | Pass |
| Overall/route/minute p95 <=200ms; max <=1s | Pass | Pass |
| Recovery late CPU <=late idle +5 percentage points | Pass | Pass |

CoilBase's minute-3-to-5 median RSS increased from
92.65 to
100.70 MiB (8.05 MiB),
while median headroom fell from
92.44 to
84.83 MiB.
This crosses the inherited 8 MiB cutoff, an arbitrary heuristic rather than a validated health limit.
The numerical check is retained as method history, not an operational failure.
Growth during warm-up is acceptable when memory settles and headroom remains;
continued growth without settling would warrant investigation. A smaller initial
footprint followed by warm-up is a plausible interpretation, not an established
cause.
Its GC log records a metadata-threshold full collection at JVM uptime 353.622s,
with logged heap capacity expanding from 15 to 22 MiB. Application swap also
fell from a 7.50 MiB minute-3 median to 2.95 MiB in minute 5, so residency changed
as well. These observations do not fully explain RSS or establish a leak.
Recovery RSS settled around 101 MiB (minute medians 101.07 and 101.04 MiB).
Long-term memory stability remains unestablished.

CoilBase's maximum HTTP latency, 422.82ms, was the first business request
(index 0, latest quotes). Both completed all requests correctly; the lower p95
does not remove this slower first request. Neither stack was swap-free.

## Scope and continuity

This is a small persistent API at 5 requests/s, not Market Replay Portfolio, a
saturation benchmark, a production-capacity estimate or proof of long-term leak
freedom. One run per stack in fixed order on a local swap-enabled VM limits
generalization and does not establish a provider VPS result. Heap/collector/pool
policy, database and framework-specific instrumentation are part of these results.

The historical Spring app used raw JDBC and manual commit/rollback, although its
starter already bundled Spring JDBC and Spring TX. The new Spring version uses
the idiomatic Spring APIs. Both new repositories issue per-symbol parameterized
updates inside one service transaction; the original used a JDBC batch. Latest
reads now borrow per query rather than sharing one raw connection across symbols.
The Spring dependency inventory matches the original except for the revised
shared fixture JAR. Keep the historical result as context rather than treating
the revised implementation as an exact repeat of the old binary.

CoilBase's built-in metrics omit database status; a manual preparation probe
checks DB health. Spring Actuator includes active DB health checks. These are
framework-specific monitoring integrations with different costs, and current
health is not proof of historical DB health. Sampling, startup probes and
monitoring affect the processes being measured. Further workload-specific tuning
may change results; this experiment uses straightforward constrained settings.

## Historical Spring context

The original raw-JDBC Spring run reported 9.89s startup, 118.56 MiB median
workload RSS, 8.39ms HTTP p95 and 27.23/31.77 MiB workload swap-in/out.
The new Spring JDBC run measured 9.35s,
125.97 MiB,
9.45ms and
26.36/26.78 MiB,
respectively. This shows broad continuity with the earlier result, including
substantial paging. These historical observations are context, not an additional
paired run; modest differences cannot be attributed to Spring JDBC from one run.

## Evidence and reproduction

- [spring analysis](results/run-20261106T202442Z-spring/analysis.json), [raw OS](results/run-20261106T202442Z-spring/guest/os.csv), [HTTP requests](results/run-20261106T202442Z-spring/http.jsonl), [final state](results/run-20261106T202442Z-spring/db-state.json).
- [coilbase analysis](results/run-20261106T203817Z-coilbase/analysis.json), [raw OS](results/run-20261106T203817Z-coilbase/guest/os.csv), [HTTP requests](results/run-20261106T203817Z-coilbase/http.jsonl), [final state](results/run-20261106T203817Z-coilbase/db-state.json).
- [Reproduction guide](reproduction-guide.md) and [measured runtime packages](evidence/runtime-inputs.json).
