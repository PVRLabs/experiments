# Javalin + Jdbi 3 follow-up result

The isolated Jdbi Core 3.55.0 application completed all 1,500 requests correctly
and met the original method's comfort criteria. Relative to the earlier JDBC
run, startup took 1.67 s longer, workload RSS increased 6.41 MiB, and external
p95 increased 1.30 ms. Minimum settled headroom was 55.04 MiB. Workload paging
remained small. This is one later run of Jdbi **plus repository/controller
restructuring**, compared with a historical baseline; it does not isolate Jdbi's
intrinsic cost or establish a statistical estimate.

## Runtime comparison

| Metric | Javalin + JDBC | Javalin + Jdbi Core | Absolute difference |
|---|---:|---:|---:|
| Startup to readiness | 2.46 s | 4.13 s | +1.67 s |
| Idle median Java RSS | 90.03 MiB | 101.55 MiB | +11.52 MiB |
| Workload median Java RSS | 106.43 MiB | 112.83 MiB | +6.41 MiB |
| Recovery median Java RSS | 110.49 MiB | 116.80 MiB | +6.31 MiB |
| Minimum idle/load/recovery MemAvailable | 69.76 MiB | 55.04 MiB | -14.72 MiB |
| Workload swap-in | 0.32 MiB | 0.20 MiB | -0.12 MiB |
| Workload swap-out | 0.00 MiB | 0.05 MiB | +0.05 MiB |
| Maximum idle/load/recovery swap occupancy | 23.82 MiB | 16.81 MiB | -7.01 MiB |
| External request p95 | 6.09 ms | 7.39 ms | +1.30 ms |
| Correct workload requests | 1,500 / 1,500 | 1,500 / 1,500 | 0 |

Run: [run-20261008T235523Z-javalin-jdbi3](results/run-20261008T235523Z-javalin-jdbi3/analysis.json),
release-005-jdbi3. Baseline: [original JDBC analysis](../vps-256mb/results/run-20261008T212522Z-javalin/analysis.json).
[Historical JDBC analysis](../vps-256mb/results/run-20261008T212522Z-javalin/analysis.json)
retain unrounded values and absolute differences. Spring evidence is unchanged.

## Method and acceptance

Same Alpine guest, one vCPU, 256 MiB allocation (214.89 MiB MemTotal), 512 MiB
swap, swappiness 60, OpenJDK 25.0.4 and
`-Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k`. All original external dependency
versions remain unchanged. Fixture and StatLite adapter are byte-identical;
StatLite v0.6.0 polls the same application/self targets every 30 s. No additional
DB-health checks, SQL Object plugins, DI container, AOT or cache training.

Host build, verified deployment and separate Alpine preparation preceded VM
stop/start. Preflight verified runtime, clock, empty swap, absent prior services
and artifact hashes. Runtime inspection and checksum reads can warm filesystem
pages, as in the original runs; this is first application launch after reset,
not a universally cold page-cache measurement. Fresh H2/SQLite storage. Original
sampler, workload and analyzer stayed unchanged in this follow-up; the sampler
has the already-recorded steal-field revision used for Spring.

Recorded UTC: baseline 2026-10-08 23:55:23; monitor-only 23:56:23; startup
23:57:53; idle 23:57:58; workload 2026-10-09 00:00:58–00:05:58; recovery ended
00:07:58. Standard durations: 60 s baseline, 90 s monitor-only, 180 s idle,
300 s traffic and 120 s recovery. Four outstanding maximum, five requests/s,
80% reads and 20% writes. Original [METHOD.md](../vps-256mb/METHOD.md) thresholds unchanged.

- Ready in 4.13 s, one Java PID, no OOM/crash/stack overflow.
- All 1,500 slots correct, zero errors/misses; exact final state: 2,070 rows,
  max sequence 689, price sum 630374.22.
- Minimum available RAM: startup 70.09 MiB; idle 74.47; load 55.04; recovery
  59.55. No settled dip below 24 MiB.
- Workload minute-three to minute-five RSS growth 3.30 MiB, below 8 MiB.
- No paging above 1 MiB/s sustained for 30 s in settled phases. Startup sampled
  endpoints: 7.88 MiB in / 17.93 MiB out, peak occupancy 17.20 MiB. Recovery
  paging: 0.04 MiB in / none out. Occupancy and paging are distinct; this was
  not swap-free operation. Lower occupancy than the earlier JDBC run does not
  establish a Jdbi memory saving.
- All route and minute p95 values below 200 ms; maximum request 85.15 ms,
  maximum scheduling lag 27.75 ms.
- Recovery RSS first/last samples 116.79/116.91 MiB; four 30 s interval medians
  116.79/116.79/116.80/116.81 MiB. Headroom medians stayed about 60 MiB, so
  memory settled without continuing headroom erosion. Late-recovery RSS remained
  14.97 MiB above late idle; returning to idle was not required. Final-minute
  host busy CPU 0.617%, late idle 0.617%, meeting the +5 percentage-point rule.
  Steal was zero; exact CPU comparison with JDBC remains unavailable.

Both monitoring targets collected successfully at cutoff. The recorded operator
waiver applies to this variant: no screenshot/inspection pause. Services stopped
before database collection, then exact tunnels and sleep inhibitor closed and
VM stopped. Archived app/monitor/sampler logs contain no unexpected errors.

## Code and dependency costs

The controller accepts a plain `QuoteRepository` and domain records. H2-specific
SQL, result mapping, initialization and database-error translation belong to
`JdbiQuoteRepository`; startup explicitly wires Hikari, Jdbi, repository and
controller. A future repository can replace H2 without changing the controller.
No extra service layer or dependency-injection framework is added.

Jdbi removes manual connection acquisition, statement lifecycle, positional
setter calls and explicit autocommit/commit/rollback handling. Named bindings,
row mapping, validation, fixture loading and SQL remain. Latest still issues
three queries on one handle; JDBC reused one prepared statement, while the
Jdbi implementation constructs a query for each symbol. This implementation
choice is part of the measured change.

The transaction difference is visible in the three-row write. The JDBC baseline
manually establishes and restores autocommit and handles rollback:

```java
connection.setAutoCommit(false);
try (var statement = connection.prepareStatement(INSERT)) {
    // Bind and batch the three symbol rows.
    statement.executeBatch();
    connection.commit();
} catch (SQLException e) {
    connection.rollback();
    throw e;
} finally {
    connection.setAutoCommit(true);
}
```

Jdbi expresses the same atomic write with a transaction callback and named
bindings:

```java
jdbi.useTransaction(handle -> {
    try (var insert = handle.prepareBatch(INSERT)) {
        for (var symbol : QuoteBatch.SYMBOLS)
            bind(insert, batch.sequence(), batch.cycle(), batch.sampleIndex(),
                 batch.marketTime(), symbol, batch.prices().get(symbol));
        insert.execute();
    }
});
```

| Literal code count | JDBC baseline | Jdbi variant |
|---|---:|---:|
| Persistence-containing implementation | 75 lines (`Quotes`) | 105 lines (`JdbiQuoteRepository`) |
| App code excluding unchanged monitoring adapter | 102 | 207 |
| App code including unchanged 83-line adapter | 185 | 290 |

Physical nonblank/noncomment lines include imports, DTOs, validation, mapping,
setup, controller, wiring, interface and error contract. Baseline code is densely
formatted and mixes responsibilities. These are literal counts, not evidence
that code doubled in complexity or that moving code removed it. The new variant
has fewer manual JDBC responsibilities and more total application structure.
Its maintainability is an architectural judgment, not a runtime measurement.

Added runtime artifacts: `jdbi3-core:3.55.0` and `geantyref:2.0.1`, totaling
2,605,198 uncompressed bytes (resources/metadata included). Shaded JARs:
13,656,948 bytes JDBC; 14,818,339 bytes Jdbi, +1,161,391 bytes (1.11 MiB).
JAR differences include new application classes, compression, timestamps and
build metadata. [Machine-readable costs](evidence/jdbi3/code-cost.json)
and [dependency verification](evidence/jdbi3/dependency-verification.json)
include artifact hashes and manual JDBC call-site counts. No result-mapping
elimination is claimed.

## Error-contract changes and preparation deviation

Successful HTTP behavior is unchanged. Invalid/missing history input and invalid,
empty/null/malformed batches return the planned descriptive 400 JSON. Repository
conflicts return `409 {"error":"conflict"}`; unexpected/null-state/unclassified
persistence failures return `500 {"error":"persistence_error"}`. The controller
uses portable categories, while only the repository interprets wrapped SQLState.
These error-only differences intentionally address known baseline defects;
neither original implementation nor its deferred patch was changed.

Separate Alpine checks passed partial-batch rollback after a preceding successful
insert, wrapped/null SQLState and exact 409/500 controller responses. Corrected
complete smoke passed 15/15, exact negative cases, unchanged state on rejected
writes, monitoring exclusion and persistence reopening. The first smoke exposed
Jackson's checked empty-body parser exception passing through Kotlin and yielding
plain-text 500. Its logs/storage remain archived; a parse-specific catch was
corrected before the frozen measured run. Preparation data is separate evidence.
See the [curated execution record](experiment-design.md) and [check instructions](checks/jdbi3/README.md).

## Interpretation and limits

For this useful small workload, Jdbi and explicit repository/controller structure
fit with headroom and predictable responses. The observed cost was additional
startup time and RSS, with little workload paging. One historical JDBC run and
one later Jdbi run cannot isolate abstraction overhead from restructuring, host
activity, cache state or ordinary run variation. No Spring repeat was needed for these single-run observations. Original input/source/artifact/evidence hashes match
before and after; raw stopped databases and machine-specific captures stay private.
