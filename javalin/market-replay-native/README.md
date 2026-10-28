# Javalin on GraalVM Native Image

Selected best-observed configuration: `native-001` with quick-build `-Ob`.
It had the lowest observed application RSS of these four deployments with
comparable performance at 5 offered requests/s. Accepted `native-o2-001` retains
the production-default `-O2` comparison.

| Accepted measurement | Native `-Ob` | Native `-O2` | Javalin HotSpot | Spring Boot F |
| --- | ---: | ---: | ---: | ---: |
| Startup (s) | 0.112 | 0.113 | 2.724 | 3.789 |
| Median workload app RSS (MiB) | 59.41 | 65.50 | 159.08 | 186.89 |
| HTTP p95 (ms) | 4.03 | 4.34 | 5.59 | 5.54 |
| Successful workload requests | 1,500/1,500 | 1,500/1,500 | 1,500/1,500 | 1,500/1,500 |
| OOM / swap | None | None | None | None |

O2 showed no clear runtime improvement under this workload. Its app RSS was
6.10 MiB higher; sampled app CPU fell 0.11 s while p95 rose 0.31 ms. These are
single observations, not repeatable effects. Startup was unchanged at collection
resolution. **This does not establish `-Ob` as generally superior to GraalVM's
production-default `-O2`.** Other applications and workloads may benefit from it.

| Compiler-reported build cost | `-Ob` | `-O2` |
| --- | ---: | ---: |
| Duration | 3m 39s | 6m 18s |
| Peak compiler RSS | 2.70 GB | 4.34 GB |
| Executable bytes | 45,222,152 | 56,953,096 |
| Companion library bytes | 33,000 | 33,000 |

Build costs are separate from runtime RSS. Both builds used a two-vCPU, 6 GiB
builder with no active swap; timings are single observations on separate builder
boots. GB above retains compiler reporting units. See [build data](results/builds.json)
and selected [Ob output](evidence/build-ob.txt), [O2 output](evidence/build-o2.txt).

## Stack and method

The application/persistence stack and workload match the independent
[HotSpot Javalin experiment](../market-replay-jdk27/README.md): Javalin 7.2.4,
Jetty, Jackson 2.21.5, HikariCP 7.0.2 min/max 1/4, MariaDB JDBC 3.5.10,
SLF4J Simple 2.0.20, and the lightweight `java-repository-poc` 0.1.0-SNAPSHOT
repository/transaction abstraction using Jdbi Core 3.55.0. Repositories compose
a shared context for SQL/dialect selection and Jdbi handles, queries and explicit
transaction callbacks; a rollback-only marker delegates lifecycle to Jdbi.
It is not an ORM or an automatic interceptor. Three quotes are ingested in one
transaction each minute, with latest/history JSON and UI assets.

Runtime VM: Ubuntu 24.04 x86_64, 512 MiB RAM, one vCPU, no swap, shared by app,
MariaDB and deterministic Python quote fixture. Same MariaDB configuration and
workload as HotSpot/F: 64 MiB InnoDB buffer pool, 8 MiB key buffer, 16 MiB Aria
cache, pool 1/4, UTC, loopback and normal durability. The existing
[Spring configuration](../../spring/boot-jdk27/mariadb-small.cnf) remains the reference.
The release does not pin all OS packages.

Native uses Oracle GraalVM 25.0.4+7.1, Serial GC and `-Xmx80m`; JVM references
use HotSpot JDK 27+35-2325, G1, `-Xmx80m` and JDK AOT caches. Equal heap caps
do not equate collectors or memory layouts. Native has no HotSpot AOT cache.
Both native builds use the same accepted MariaDB application JAR, dependencies,
reachability metadata and explicit `static/.*` resource inclusion. Only the
optimization option changed: `-Ob` versus `-O2`. Compilation uses `-J-Xmx4g`,
`--no-fallback`, Serial and `x86-64-v3`. O2 reports built-in `PGO: ML-inferred`
(static inference); no supplied or instrumented workload PGO was used. Metadata
was collected by exercising the behavior contract under the tracing agent.
Keep emitted companion libraries with the executable. Further code paths may
require metadata and the CPU target limits portability.

Preparation used an isolated MariaDB schema and checked polling, payloads,
assets, health/metrics, failure/recovery and restart persistence. Both native
[Ob](evidence/contract-ob.txt) and [O2](evidence/contract-o2.txt) contracts passed.
Accepted runtime runs used a reset measured schema on separate VM boots; setup
warmed storage. Builder was stopped. Health UP and three stored quotes define
startup, checked about every 50 ms. Then 60/120/300/60-second idle/warm-up/
workload/recovery phases, at 5 offered requests/s during warm-up and workload,
alternating latest/history, four maximum in flight, no retries. Host HTTP timing
includes SSH forwarding. OS samples are about one second, metrics every ten
seconds; transition samples are excluded. No StatLite process or periodic
DB-health probe runs. JSON metrics differ from Spring Prometheus collection.

## Evidence, provenance and interpretation

[Four-configuration comparison](results/comparison.json) preserves the accepted
curated numbers and differences. [Ob detail](results/native-comparison.json),
[O2 detail](results/native-o2-comparison.json) and [metadata](results/experiment.json)
preserve phase summaries, validation and provenance. The HotSpot values come
from `javalin-002`; F is `optimized-F-001`, reused from the existing public
[Spring release](../../spring/boot-jdk27/README.md) and
[baseline JSON](../../spring/boot-jdk27/results/comparison.json) at `/runs/F`.
No baseline evidence files are duplicated. Native runs are `native-001` and
`native-o2-001`, both October 28, 2026 UTC. Selected evidence in
[Ob](evidence/native-001/) and [O2](evidence/native-o2-001/) includes projected
samples, request records, readiness, history and validation observations.
Both passed 600/600 warm-up requests, ten ordered ingestion batches, ten rows
per symbol, CPU continuity and no OOM/swap checks.

These are complete application deployment comparisons, not universal framework
rankings. They support exploring a potential “Spring Boot Lite” stack, not a
complete Spring Boot replacement or proof that Javalin is the lightest Java
framework. Single measurements on separate boots/dates do not establish
variability. There is no throughput-capacity or saturation test. App RSS is not
whole-host consumption; database residency varied (O2's higher app RSS coincided
with lower database RSS). Sampled peaks can miss spikes.

Startup values have about 50 ms polling resolution, irrespective of displayed
decimals. The O2 kernel reported HPET/TSC watchdog read-back delays of
253,663/210,990 ns and a skipped clock-skew check during workload; HotSpot
Javalin also recorded warnings. Ob had no recorded kernel entries. These do not
prove clock drift; cause and timing effects remain unknown. No intervals were
removed. Small latency/CPU differences should not be overinterpreted.

Run `python3 analyze.py` here using Python 3 alone. The
[reanalysis guide](reproduction-guide.md) explains the evidence projection and
limits; the [journal](journal.md) records curation. This is a curated data release,
not a complete application rebuild or benchmark rerun package. It excludes
private runners, raw databases, binaries, large sampling archives and failed
preparation attempts.
