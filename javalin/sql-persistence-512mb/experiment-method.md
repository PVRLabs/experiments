# Method and measured results

## Question and workload

Which latency and resident-memory differences repeat across Jdbi Core 3.55.0,
MyBatis Core 3.5.19 and jOOQ OSE 3.21.9 in the same small Javalin application
when the guest has 512 MiB and no swap? A separate selected MyBatis repeat
demonstrates operation with StatLite; it is not a new library ranking.

The API serves latest quotes for three stock symbols, bounded history and
transactional three-row inserts. Each fresh file-backed H2 database starts
with 1,170 rows. Schema: identity primary key, unique `(batch_seq,symbol)`, and
index `(symbol,id DESC)`. Reads filter by symbol, order by descending ID and
limit rows; history reverses its result for presentation. Latest-quotes executes
three symbol queries. Each write executes the same INSERT batch three times
within one transaction.

External HTTP/1.1 load schedules 1,500 requests over five minutes at 5/s: 300
latest, 900 history and 300 writes, at most four outstanding, no retries. The
client validates status and response contents. Expected final state is 2,070
rows, maximum sequence 689, price sum 630374.22. Final inspection is after cutoff.
This is deterministic functional traffic, not representative production demand
or evidence of maximum capacity.

## Environment and preparation

Intel macOS host, Lima VZ x86_64/plain-mode local VM; one vCPU, 512 MiB configured,
477,708–477,712 KiB Linux MemTotal (about 466.5 MiB), no swap. Alpine 3.24.2,
kernel 6.18.54-0-virt, OpenJDK 25.0.4+7-alpine-r0. Each `run.json` records the
actual runtime, boot ID and settings. Common dependencies include Javalin 7.2.3,
Jetty 12.1.12, H2 2.4.240, HikariCP 7.0.2 and Micrometer 1.17.0; see the inventory.

Every JVM used `-Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k`. Hikari minimum idle 1,
maximum pool 2; H2 `CACHE_SIZE=4096;DB_CLOSE_ON_EXIT=FALSE`. Embedded H2 memory
is part of app RSS. The collector and fixed heap policy are explicit controls,
not claims about minimum library memory requirements.

The VM was cloned from the original stopped 256 MiB guest, resized and prepared
before measurement. The original local Alpine image is unavailable, so exact
VM creation is not reproducible from a public download in this package. The
installed runtime and per-run settings are preserved as evidence; new-image
reproductions must disclose their differences. No image or machine-specific
path is distributed.

Reviewed application JARs were frozen once. Host and guest checks covered
repositories, transaction rollback, late fixture failures/recovery, HTTP
contracts, restart persistence, and collection. Separate preparation smokes
covered all variants and monitoring. Their transient logs are not result data.

## Recorded phases and controls

Before every run the guest was stopped/started, no swap or competing Java/StatLite
was verified, deployment checksums checked, and a fresh database used. Physical
host caches are not claimed cold. Six main runs had no StatLite process or
metrics polling; unchanged application instrumentation remained compiled in.

Each main run: 30 s OS-only baseline, launch to readiness, 30 s idle, five-minute
workload, 30 s recovery, then measurement cutoff and DB inspection. Readiness
was probed every 100 ms. Independent OS sampling used one-second startup and
five-second steady cadence. The final scheduled request is at 299.8 s; recovery
begins after completion, not after an added artificial workload delay.

Order was Jdbi/MyBatis/jOOQ, then jOOQ/MyBatis/Jdbi. Distinct boot IDs and
non-overlapping windows are recorded. Order reversal is not full balancing.
Approval delays between launches did not pause any measured workload. A failed
host launch before preflight created no measured data and is not one of the runs.

Acceptance requires 1,500 uniquely indexed completed requests, zero errors,
fixed final state, correct phase order/durations and OS sample coverage/cadence.
Partial database consistency alone does not establish success. Synthetic checks
exercise failures and invalid matrices. Reanalysis suppresses ranges if the
six-run comparison is incomplete or invalid.

## Individual results

RSS and guest-wide busy CPU summarize workload; percentiles are external-client
measurements including the local tunnel. Ready includes schema and fixture setup.

| Run (UTC start identifier) | Variant | Ready, s | p50 / p95, ms | Median / peak RSS, MiB | Guest CPU, % |
| --- | --- | ---: | ---: | ---: | ---: |
| 20261019T203115Z | Jdbi | 3.45 | 4.10 / 8.48 | 122.4 / 128.2 | 3.84 |
| 20261019T204216Z | MyBatis | 2.77 | 3.24 / 7.52 | 116.6 / 123.3 | 3.55 |
| 20261019T205545Z | jOOQ | 4.10 | 3.62 / 9.35 | 152.1 / 156.4 | 3.80 |
| 20261019T211837Z | jOOQ | 4.37 | 4.01 / 9.19 | 154.3 / 158.4 | 3.74 |
| 20261019T212821Z | MyBatis | 2.68 | 3.60 / 7.47 | 118.0 / 123.4 | 3.76 |
| 20261019T213850Z | Jdbi | 3.11 | 3.73 / 7.38 | 120.0 / 123.6 | 3.49 |

All six passed. No swapping, OOM events or workload major faults were observed.
Minimum workload available memory across the six runs was 272.55 MiB.
See `results/measured/<identifier>-<variant>/` and the comparison JSONs.

## Selection and monitored repeat

After all six main results and source tradeoffs were presented, the operator
selected MyBatis for lowest median workload RSS in both rounds, competitive
p95 with overlapping Jdbi ranges, and prior preference for annotation-driven
mappers. The preference is qualitative; no significant latency advantage was
demonstrated and MyBatis is not a universal winner.

Run `20261019T215517Z-javalin-mybatis` used the same frozen app and settings,
with fresh StatLite v0.6.0 storage and 30-second polling of self/app targets.
It added a 90 s monitor-only phase after the 30 s OS baseline, verified two self
samples, then repeated the same launch/idle/workload/recovery protocol.

It passed with 1,500 successful requests, correct state and sampling, no swap/OOM,
3.19 s readiness, 3.94 ms p50, 8.29 ms p95, 121.35 MiB median app RSS and 124.58
MiB peak. Guest CPU was 4.26%, minimum workload available memory 292.42 MiB.
StatLite median RSS was 14.07 MiB baseline and 15.03 MiB workload. Its process
CPU tick deltas indicate approximately 0.012% baseline and 0.017% workload of one
vCPU, with sampling quantization. See [monitored comparison](monitored-comparison.json).
A single repeat cannot distinguish monitoring effects from ordinary variation.

UTC phases: OS baseline 21:55:18, monitor-only 21:55:48, startup 21:57:18,
idle 21:57:21, workload 21:57:51–22:02:51, cutoff 22:03:21. Post-cutoff dashboard
inspection was completed by the operator; both screenshots are included with
captions. Services were stopped before database collection and the archived
SQLite integrity check returned `ok`. Only that result is curated, not the DB.
Live status cards are post-run state. App UP is not explicit DB health (which
was not reported); database correctness was checked independently.

## Interpretation and limitations

MyBatis consistently had the lowest median workload RSS, Jdbi was competitive
on HTTP latency and jOOQ had a larger resident footprint. These are complete
implementations under one workload/JVM/embedded-DB policy, not isolated library
costs. Two runs are a basic repeatability check, not a robust variation estimate.
No load saturation, production database behavior or long-term stability is tested.

MyBatis explicitly sets `localCacheScope=STATEMENT`, overriding SESSION; it is
not a general freshness guarantee. For latest-quotes Jdbi holds one handle and
MyBatis one session/pooled connection across three reads. Datasource-backed jOOQ
checks out/returns per query: three logical pool cycles, not necessarily three
physical connections. Its impact was not isolated; SQL equivalence does not
mean identical lifecycles or an atomic snapshot across symbols.

The original matrix checker required exact MemTotal equality and rejected a
4 KiB difference on first jOOQ and second Jdbi boots. After measurement it was
corrected to allow only a one-page spread with matching configured RAM/other
inputs. Values were not rounded or modified in evidence; regression checks
accept 4 KiB and reject 8 KiB/larger spreads. No measured artifact, workload or
raw measurement changed. The precise cause of the boot variation was not
investigated; its scale is immaterial to multi-MiB RSS differences and headroom.

The [256 MiB measurements](../sql-persistence-256mb/) used swap, StatLite,
different phase timing and one run each; jOOQ used its historical fixture loader.
They remain valid observations but cannot be pooled with these results or
interpreted as a controlled RAM-only change.
