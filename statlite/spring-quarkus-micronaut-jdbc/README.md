# Spring Boot, Quarkus, and Micronaut with JDBC — results

All three applications completed their 15-minute scripted-load windows with
638 requests and zero request errors. Quarkus had the lowest median process
RSS and fastest launch-to-readiness in this run. Micronaut used slightly more
RSS and CPU than Quarkus; Spring used more RSS than both. Absolute CPU usage
was low throughout the measured workload. These are observations from one
fixed-order engineering experiment, not a general framework ranking.

## Method and inputs

Run date: 2026-10-02. Equivalent Market Replay applications use a deterministic
local quote fixture, scheduled 60-second synchronization, file-backed H2
2.4.240, JDBC without an ORM, and one-to-four connection pool bounds. Spring
Boot 4.1.1 and Micronaut Platform 5.2.1 (Core 5.2.11) use HikariCP;
Quarkus 3.40.1 uses Agroal.

Ubuntu 24.04 x86_64 runs in Lima VZ with 2 vCPUs, 1 GiB RAM, and no swap.
All applications use Temurin 25.0.4.1+1 LTS with
`-Xms32m -Xmx192m -XX:+UseG1GC -XX:ActiveProcessorCount=2`.
The frozen StatLite candidate is commit
`4220d5fd0bbd3a07fea72eb46c2461e92b96f9f1`, with 10-second measured polling.
See [REPRODUCE.md](REPRODUCE.md) and [the evidence notes](data/README.md) for pinned
image/JDK hashes, artifact verification, readiness, and collection details.

All three guest smoke checks passed before measurement, warming filesystem
state while using separate databases and monitoring storage. Each measured
app starts a fresh JVM and database. Readiness requires healthy status and a
persisted three-observation batch. Spring, Quarkus, and Micronaut run in that
order. Latest/history request pairs occur every five seconds, increasing to
every second during minutes 7–10. Minutes 0–3 are designated runtime warmup.

The fixture and one measured StatLite process remain running across all four
windows. Fresh databases isolate the final all-three, no-generated-load window.
Timed execution finished at 19:47:55 UTC (12:47:55 PM Pacific).

## Individual results

RSS is independently sampled Linux process resident memory every five seconds,
including runtime warmup: 180 samples per individual window. Heap limits and
StatLite JVM runtime-memory charts are different quantities from RSS.

| Application | Readiness | Median RSS | Peak sampled RSS | Mean app CPU | Mean host CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Spring | 4.90 s | 214.3 MiB | 224.9 MiB | 0.539% | 0.727% |
| Quarkus | 2.25 s | 178.4 MiB | 190.3 MiB | 0.439% | 0.498% |
| Micronaut | 2.54 s | 186.7 MiB | 189.9 MiB | 0.790% | 0.817% |

App CPU is StatLite's `process_cpu_cores` multiplied by 100: percent of one
CPU core. Host CPU is percent of the VM's total two-core capacity, so the
columns have different denominators. Both use 13 one-minute aggregated values
per window, excluding startup and boundary buckets. Bucket timestamps must be
at least 60 seconds after window start and strictly before window end minus
60 seconds. These means are not instantaneous peaks or complete-window CPU
integrals.

Quarkus's median RSS was 8.3 MiB below Micronaut's and 36.0 MiB below Spring's.
Quarkus and Micronaut had nearly identical sampled RSS peaks. Whole-VM mean CPU
was approximately 0.32 percentage points higher during Micronaut's window than
Quarkus's. No root-cause attribution is needed for these descriptive findings.

Median RSS by planned workload interval:

| Application | Warmup, 0–3 min | Baseline, 3–7 min | Busier, 7–10 min | Return, 10–15 min |
| --- | ---: | ---: | ---: | ---: |
| Spring | 206.6 MiB | 212.6 MiB | 220.6 MiB | 224.4 MiB |
| Quarkus | 169.6 MiB | 177.0 MiB | 179.5 MiB | 189.7 MiB |
| Micronaut | 178.7 MiB | 184.6 MiB | 187.6 MiB | 189.4 MiB |

RSS increased during these short windows; these results do not establish a
long-term memory plateau or leak. Each individual phase ended with latest-row
IDs 46–48, consistent with 16 three-row persisted batches under the shared
append-only schema. Each closed individual H2 file is 36,864 bytes.
Starting fixture sample indexes were 0, 15, and 30 respectively.

Mean host CPU in the busier interval was 0.892% for Spring, 0.808% for Quarkus,
and 1.052% for Micronaut (three timestamp-selected minute buckets each).
Highest included host CPU minutes were 2.362%, 0.870%, and 1.197%, respectively.
The host metric includes app, fixture, monitoring, and guest services.

StatLite median RSS was 18.5, 19.4, and 20.1 MiB across the successive individual
windows. Fixture RSS remained approximately 22.4 MiB.

## Shared-host observation

All three restarted into fresh databases and ran together for 15 minutes
without generated API load. Normal quote synchronization and monitoring
continued. Report this separately from the individual tests.

| Process | Median RSS | Peak sampled RSS | Mean app CPU, one-core basis |
| --- | ---: | ---: | ---: |
| Spring | 212.7 MiB | 215.3 MiB | 0.304% |
| Quarkus | 171.4 MiB | 172.6 MiB | 0.231% |
| Micronaut | 180.3 MiB | 182.5 MiB | 0.588% |
| StatLite | 21.5 MiB | 21.9 MiB | — |
| Fixture | 22.4 MiB | 22.4 MiB | — |

Mean host CPU was 1.039%, median 0.995%, and highest included minute 1.277%.
The operator's host screenshot shows RAM rising from approximately 0.48 GB to
0.8 GB as all three launch, below the displayed approximately 0.94 GB total.
A startup CPU spike subsides quickly; disk usage changes little.

Dashboard latency rises after the shared-phase restart, especially for Spring.
The request populations and warmup conditions differ, so this is an observed
transition, not a controlled latency ranking.

## Monitoring and operational observations

StatLite self-monitoring reported successful collection in all 90 recorded
status checks of each timed window. Each individually active app had one
initial error status and then 89 successful statuses, consistent with readiness
preceding the next metrics poll. In the shared window Spring and Quarkus had
90 successful statuses each; Micronaut had one initial error and 89 successes.
Unavailable targets remain configured intentionally. One stale successful
Spring status appears at the first Quarkus-window check before the next poll
records Spring's shutdown. Health fields can retain their previous value and
observation timestamp while collection is failing; interpret those together.

There were no recorded fixture availability losses, exits, or replay regressions,
and no guest OOM messages in the captured kernel journal. All three planned
restarts recovered collection. This does not certify every counter-normalization
or dashboard behavior.

Screenshots show bounded, sawtooth JVM-memory traces, consistent with allocation
and collection, but do not identify GC events. Quarkus counts approximately two
fewer requests per polling interval than Spring/Micronaut under the same runner
traffic. Preserve this instrumentation observation; dashboard latency/request
populations need not match. Spring DB health is “Not reported,” not an observed
database failure. See the [original screenshots and captions](screenshots/README.md).

## Evidence and limitations

[Curated evidence](data/README.md) contains timed process RSS samples, CPU
buckets, runner requests, collector statuses, fixture positions, calculated
statistics, and frozen artifact verification records. The private raw archive
also retains logs and closed databases; neither private paths nor databases
are needed for the public numerical comparisons. Both captured StatLite SQLite
databases passed `PRAGMA integrity_check` before curation.

[summary.json](data/summary.json) contains the calculated statistics. Run
`python3 analyze.py` from this experiment directory to reproduce the headline
RSS/CPU/request figures directly from the curated CSV files. `SHA256SUMS`
identifies public package files. Source and reproduction steps are included.

This is one fixed-order run with prepared caches and changing replay positions.
Background guest services are included in host metrics. Startup is externally
observed launch-to-readiness, not pristine cold boot or framework log timing.
No repeated trials, throughput limits, or statistical significance are claimed.

The operator opened the dashboard around 12:35 PM Pacific, during the shared
window, rather than waiting for its end. The private intervention record preserves the timing; dashboard traffic may affect StatLite's own
HTTP metrics. Screenshots around 12:37 PM precede the timed window's end.
Apps continued running for inspection until clean service shutdown at
20:49:42 UTC. Later inspection samples and shared database growth are excluded
from timed statistics. Shared H2 file sizes in the raw summary describe final
shutdown state, not minute 15. The phase-end API snapshots retain the timed
endpoint state.

The VM and dashboard tunnel are stopped, with evidence preserved. Root-cause
analysis was not required for this observational experiment.
