# Experiment method

## Question and environment

Can straightforward build/deployment changes improve a useful Spring Boot
application's startup and memory footprint on a small single-server deployment?
Follow-ups asked whether a dependency-reduced persistence integration or an
embedded database improved the same deployment budget.

Measurements were collected on October 23–24, 2026 (UTC). The measured environment
was Ubuntu 24.04 x86_64, one vCPU, 512 MiB RAM, no swap, Spring Boot 4.1.1,
HotSpot 27+35-2325, `-Xmx80m` and default G1 ergonomics. Builds and startup-only
cache training used a separate Linux builder with matching JDK/platform.
The host was outside the measured VM budget; results are local virtual-machine
observations, not measurements of a commercial VPS service.

The Market Replay application used MVC/Tomcat, Jackson, Actuator/Micrometer,
Spring JDBC JdbcClient and Hikari min/max 1/4. It polled a deterministic local
HTTP quote fixture once a minute, persisted three-row atomic batches and served
latest/history JSON endpoints and a browser UI. The Python fixture also ran in
the measured VM. MariaDB/InnoDB used loopback access and the
[small-server configuration](mariadb-small.cnf), with durability defaults retained.
The [MariaDB schema](schema.sql) is included for context. This release does not
pin all OS packages or include a full application rebuild.

## Main comparison

A was the ordinary executable JAR. F combined tools-extracted layout, Spring AOT
initialization and a trained JDK AOT cache. Neither used native-image compilation.
The app behavior, runtime libraries, SQL, pool and database settings were held
constant. A ran once, then F once. Each followed a separate VM reboot, MariaDB
restart and empty-schema initialization outside startup timing. These are
fresh-process, post-reboot starts; schema initialization warmed storage.

Startup was polled about every 50 ms until health UP and the first three quotes
were persisted. Each run then had 60 seconds idle, 120 seconds warm-up, 300 seconds
measured workload, and 60 seconds recovery. Warm-up and measured load offered
5 requests per second, alternating latest/history reads, with at most four
in flight and no retries. Load ran outside the VM through a localhost tunnel.
Both recorded runs ingested ten ordered batches and 30 rows.

OS collection sampled approximately once a second; Prometheus was scraped every
ten seconds. Samples marking phase transitions are excluded from steady phase
summaries. RSS is process residency; MemAvailable is Linux's host-headroom estimate.
JVM used/committed pool gauges are neither RSS nor a complete native-memory total.
Peaks are sampled and may miss brief spikes. No NMT, attach diagnostics or forced
GC was used. StatLite was off for A/F, MyBatis and the completed H2 comparison.

## Preparation observations

Packaged API/UI, polling, persistence, failure/recovery and restart checks preceded
measurement. Initial preparation included an OOM after ordinary-app readiness and
additional SSH activity, and an OOM during cache training inside the small VM.
These are not accepted comparison runs and do not establish a single cause.
Training moved to the builder. Loose-file transfer initially changed timestamps
and caused cache rejection despite functional startup. Timestamp-preserving
archive transfer and explicit cache-log checks resolved that preparation issue.
The original large secondary database caches were reduced to the published 8/16
MiB MyISAM/Aria settings before accepted A/F execution.

An initially started extracted-only B run was cancelled when the scope changed
to A/F. It is excluded. F logged a Tomcat parallel-classloader registration
warning without observed polling failure. This data package does not include
those preparation logs or the cancelled run.

## Follow-ups

**MyBatis:** MyBatis Core 3.5.19 replaced Spring JDBC/transaction integration in an
isolated app with manually managed sessions, local batch commit/rollback, mapper
and Hikari wiring. It used its own accepted AOT cache. Exact timestamp/decimal
mapping, late-insert rollback and connection release were checked in preparation.
Its phases were 60/120/60/60 seconds. Compare only its first 60 seconds of workload
with the first 60 seconds of JDBC F (59 steady OS samples and 300 requests each).
No conclusion about framework-integrated MyBatis follows from this boundary.

**H2:** H2 2.4.240 replaced MariaDB driver 3.5.10; 62 shared runtime libraries were
byte-identical. Durable file-backed storage, its original schema initialization,
the same pool/heap/workload and a separately trained cache were used. MariaDB was
stopped. Restart persistence was checked first. A first monitored 15-minute
attempt was interrupted without a completed request record and is excluded.
The accepted run used the original 60/120/300/60-second phases without StatLite.
Each F comparison has 298 workload OS samples and 29 JVM scrapes. This is a
deployment-shape comparison, not a test of equivalent database guarantees,
backup recovery, multi-instance behavior or maximum database performance.

**Monitoring:** The separate 900-second JDBC F addendum ran from 2026-10-23
23:53:52 to 2026-10-24 00:08:52 UTC. It used StatLite v0.6.2-dev, source revision
`a4881332e2f27a84749e568a12bd7103f64dd728`, on the same VM at a 30-second polling
interval, including self-monitoring. Explicit DB-health checks were enabled.
Traffic began after readiness without the main comparison's separate warm-up.
Its 896 steady recorded samples exclude boundaries and post-run inspection.
Two readiness `/actuator/health` 503s predated load and are distinct from zero
workload errors. Early-to-late app median RSS rose from 177.9 to 191.0 MiB;
that establishes neither a leak nor a long-term plateau. The operator inspected
the dashboard after load, then monitoring was stopped before storage collection.
