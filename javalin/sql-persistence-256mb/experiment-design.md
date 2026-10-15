# Experiment design and execution record

## Question and method

How do Jdbi Core, MyBatis Core and jOOQ OSE differ in application responsibilities,
startup, memory, paging and package size for this small Javalin service?
This is a practical single-run comparison, not a throughput benchmark.

Environment: local Intel macOS host with Lima/VZ; x86_64 Alpine 3.24.2 guest,
one vCPU, 256 MiB configured (214.89 MiB MemTotal), 512 MiB disk swap,
swappiness 60, OpenJDK 25.0.4. JVM: `-Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k`.
HikariCP 7.0.2: one minimum idle, two maximum connections. H2 2.4.240:
file-backed database and CACHE_SIZE=4096. Javalin 7.2.3, Jackson 2.22.1,
Micrometer instrumentation and StatLite 0.6.0, polling every 30 seconds.
The recorded [input manifests](evidence/) identify versions and artifacts.
The [original method](../vps-256mb/METHOD.md) supplies the shared contract.

Preparation built each variant on the host, verified shared inputs and resolved
runtime dependencies, and exercised the application inside Alpine with separate
storage. Checks covered fixture loading, mapping, history order, decimal values,
partial-batch rollback, error translation, HTTP responses, metrics exclusions and
persistence after reopening. Preparation traffic is excluded from measured runs. Saved successful smoke
outputs: [Jdbi](evidence/smoke-20261008T234736Z-javalin-jdbi3/contract-checks.json),
[MyBatis](evidence/smoke-20261009T010230Z-javalin-mybatis/contract-checks.json), and
[jOOQ](evidence/smoke-20261009T015154Z-javalin-jooq/contract-checks.json).
Adjacent persistence records show the checked state after reopening.

Each measured variant used fresh H2/StatLite storage after VM stop/start and a
preflight checking the clock, prior processes, deployment and near-zero swap.
Preflight can warm filesystem pages; this is not a universally cold-cache test.
Held constant: runtime/heap/collector, fixture, successful HTTP semantics, external
workload, controller/repository contract, pool, monitoring and sampling method.
Phases: 60s baseline, 90s monitor-only, Java startup/readiness, 180s idle,
300s workload, 120s recovery. OS samples are about 1s during startup, 5s otherwise.
The host generator schedules 1,500 requests at 5/s, 80% reads and 20% three-row
writes, maximum four outstanding, no retries. Latencies include the SSH tunnel.

## Recorded runs

| Variant | Run directory | Result |
|---|---|---|
| Jdbi Core 3.55.0 | [20261008T235523Z](results/run-20261008T235523Z-javalin-jdbi3/analysis.json) | 1,500 correct requests |
| MyBatis Core 3.5.19 | [20261009T011153Z](results/run-20261009T011153Z-javalin-mybatis/analysis.json) | 1,500 correct requests |
| jOOQ OSE 3.21.9 | [20261009T015612Z](results/run-20261009T015612Z-javalin-jooq/analysis.json) | 1,500 correct requests |

All final states: 2,070 rows, maximum sequence 689, price sum 630374.22.
Interpretation considers readiness, validated responses, available memory, RSS,
paging volumes/occupancy and recovery together. Similar RSS does not imply equal
memory pressure; swap occupancy differs from paging volume. No run was averaged.

## Implementation and operational observations

Jdbi uses Core handles and transaction callbacks. MyBatis uses an annotated mapper,
statement-local caching, repository-owned sessions, and explicit batch flush/commit.
jOOQ uses a generated H2 schema model and transaction-scoped request batches.
All use constructor wiring without a DI container and portable repository errors.
Error responses intentionally fix historical JDBC-baseline defects; JDBC is not a
fourth candidate. Jdbi also includes restructuring relative to that older baseline.

Jdbi's first preparation smoke exposed an empty-body parsing exception producing
HTTP 500. The parser handling was fixed before the measured artifact was frozen.
The Jdbi dashboard pause was explicitly waived; no Jdbi screenshot is claimed.
jOOQ's first preparation checker requested aggregate state before fixture creation;
H2 returned null for MAX/SUM on an empty table. Initialization was changed to test
row count directly. Another preparation attempt lacked the host tunnels required
by the plain VM. Both attempts were stopped and retained privately; the final
smoke passed with fresh storage and verified tunnels. The operator also waived
visual dashboard inspection for the jOOQ run; numerical measurements were retained.

The successful jOOQ run used a nontransactional fixture loader. Review later found
that failure partway through initialization could leave a partial fixture. The
[correction](jooq-correction.md) passed a host rollback/recovery check but was not
VM-measured. The [original repository](historical/jooq-release-002/JooqQuoteRepository.java)
and checker match their recorded input hashes. Historical rebuilding matched
all shaded-JAR entry contents, with only ZIP timestamps differing; the checker
compiled to identical classes. [Verification](historical/jooq-release-002/rebuild-verification.json).

jOOQ paging and early latency were both higher early in its single workload.
This timing is consistent with several explanations and does not establish
causation or intrinsic library cost. No rerun is necessary for factual reporting
of these original applications. Corrected-source startup remains unknown.

## Limits

One run each in a fixed sequence, short deterministic traffic, a local VPS-sized
VM, and complete applications with different persistence implementations.
Package sizes include application classes and ZIP metadata. Handwritten line
counts are nonblank/noncomment physical Java lines, excluding the shared 83-line
StatLite adapter; generated Java is counted separately. Counts are not a
maintainability score. Original private raw archives remain separate.
