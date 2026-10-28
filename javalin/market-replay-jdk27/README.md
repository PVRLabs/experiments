# Javalin on HotSpot JDK 27 versus optimized Spring Boot F

A Market Replay application assembled from Javalin and a lightweight Jdbi Core
repository layer started sooner and used less application RSS than the existing
optimized Spring Boot F deployment in these single measurements.

| Accepted measurement | Javalin `javalin-002` | Spring F `optimized-F-001` |
| --- | ---: | ---: |
| Startup to health and persisted quotes | 2.724 s | 3.789 s |
| Median workload app RSS | 159.08 MiB | 186.89 MiB |
| HTTP p95 | 5.59 ms | 5.54 ms |
| Successful workload requests | 1,500/1,500 | 1,500/1,500 |
| OOM / swap | None | None |

Javalin's startup was 28.1% shorter and median application RSS 14.9% lower
(27.8 MiB). Request p95 was similar at the offered load. These compare complete
application deployments; they do not isolate framework costs or rank frameworks.
Database and fixture residency also varied, so app RSS savings do not translate
one-for-one into host headroom.

The baseline is the existing [Spring Boot JDK 27 release](../../spring/boot-jdk27/README.md),
with [accepted F data](../../spring/boot-jdk27/results/comparison.json) at `/runs/F`.
Its evidence is reused in place, not exported again. The independent
[Native Image experiment](../market-replay-native/README.md) compares both native
optimization settings with these two deployments.

## Stack, environment and method

Ubuntu 24.04 x86_64, 512 MiB RAM, one vCPU, no swap. Application, MariaDB and a
deterministic Python HTTP fixture share the VM budget. These are local VM
observations, not measurements from a commercial VPS. MariaDB uses the same
[configuration](../../spring/boot-jdk27/mariadb-small.cnf) as F: 64 MiB InnoDB,
8 MiB key buffer, 16 MiB Aria cache, loopback access, UTC and normal durability.
MariaDB package versions are not fully pinned by this curated release.

Javalin 7.2.4/Jetty, Jackson 2.21.5, HikariCP 7.0.2 (min/max 1/4), MariaDB JDBC
3.5.10 and SLF4J Simple 2.0.20 accompany `java-repository-poc` 0.1.0-SNAPSHOT on
Jdbi Core 3.55.0. A JDK scheduler polls once a minute and atomically stores three
quotes; latest/history JSON and a browser UI provide the reduced Market Replay
behavior. There is no portfolio editing.

The repository layer composes a shared `RepositoryContext` into SQL repositories.
It selects optional dialect-specific SQL and exposes Jdbi handle/query callbacks
and explicit transaction callbacks that join an existing managed transaction or
start one. A small rollback-only marker delegates transaction lifecycle and
cleanup to Jdbi's local transaction handler. This is explicit JDBC persistence,
not an ORM or automatic Spring-style interception. It supports exploring a
potential “Spring Boot Lite” stack; this experiment neither establishes a
complete Spring Boot replacement nor proves Javalin is the lightest Java framework.

Both JVM deployments use HotSpot 27+35-2325, G1 and `-Xmx80m`. Javalin ships a
thin `app.jar` with `lib/`. Startup-only cache training on a separate builder uses
`MARKET_TRAINING=true java -Xmx80m -XX:AOTCacheOutput=app.aot -jar app.jar`;
the training path exits before a database connection and does not train request
paths. Runtime uses `java -Xmx80m -XX:AOTCache=app.aot -jar app.jar`.
Timestamp-preserving transfer and successful cache opening without rejection
were checked. There is no Javalin build-time framework AOT step. F combines
extracted layout, Spring AOT and a trained JDK AOT cache; see its
[method](../../spring/boot-jdk27/experiment-method.md) for the MVC/Tomcat,
Spring JDBC, Actuator/Micrometer and Logback stack.

Preparation checked behavior before measurement. Each accepted run followed a
separate VM boot, database restart and empty-schema setup outside startup timing;
setup warmed storage. Startup ends at health UP plus three persisted quotes,
polled about every 50 ms. Then 60/120/300/60 seconds of idle/warm-up/workload/
recovery. Warm-up and workload offer 5 requests/s, alternating latest/history,
maximum four in flight, no retries, from the host through SSH forwarding.
OS resources are sampled about once a second; transition samples are excluded.
HTTP percentiles use nearest rank over successful requests.

Javalin JSON metrics and F Prometheus metrics are scraped every ten seconds with
transition skips. No StatLite process or periodic DB-health probe runs. Scrape
implementations and payloads differ, so monitoring overhead is not controlled.

## Evidence and limits

[Accepted comparison](results/comparison.json) preserves the private curated
numbers and calculated differences; baseline detail is replaced with its public
reference. [Experiment metadata](results/experiment.json) records versions,
method, provenance and limitations. [Selected evidence](evidence/javalin-002/)
contains projected memory samples, request records, readiness, history and
validation observations. Ten ordered batches, ten rows per symbol, 600/600
warm-up requests, CPU continuity, cache acceptance and no OOM/swap passed.

The HotSpot Javalin run logged HPET/TSC watchdog read-back delays of
875,460/153,301 ns and a skipped clock-skew check during workload. Cause and
any timing effect are unknown; this is not proof of clock drift. All requests
succeeded, but those checks do not certify clock accuracy. Startup's displayed
precision exceeds its roughly 50 ms polling resolution; RSS peaks are sampled.

One run per configuration on separate boots/dates (Javalin October 28 UTC,
F October 23, 2026), package state, logging, training coverage and host activity
limit attribution. This is no throughput-capacity or saturation test. Recovery
RSS does not establish long-term safety or a leak. Heap/collector policy affects
RSS; it is not a framework minimum.

Run `python3 analyze.py` here with Python 3 and no third-party packages. See the
[reanalysis guide](reproduction-guide.md) and [curation journal](journal.md).
This curated data release supports verification, not a complete application
rebuild or benchmark rerun. It excludes binaries, databases, private runners,
large raw captures and preparation failures.
