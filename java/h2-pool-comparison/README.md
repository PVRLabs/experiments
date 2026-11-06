# Embedded H2 native pool and HikariCP

On November 6, 2026, we compared H2's built-in `JdbcConnectionPool` with HikariCP in one small embedded-H2 application. Hikari used approximately 2 MiB more process RSS at idle; mean RSS under moderate load was comparable. Hikari's observed p95 and p99 were slightly lower in both runs. This short, lightly contended test does not establish a general performance advantage or measure pool saturation. It does not compare external databases.

| Run | Pool | Idle mean RSS (MiB) | Moderate mean RSS (MiB) | Moderate p95 (ms) | Moderate p99 (ms) |
| --- | --- | ---: | ---: | ---: | ---: |
| A1 | H2 native | 85.30 | 111.05 | 6.82 | 9.71 |
| B1 | HikariCP | 87.98 | 109.05 | 5.84 | 8.42 |
| B2 | HikariCP | 87.85 | 109.80 | 6.23 | 8.84 |
| A2 | H2 native | 86.15 | 110.85 | 6.96 | 10.21 |

## Method

The same CoilBase preview1 and Avaje Jex application, SQL, and file-backed H2 2.5.250 database were used for both pools. HikariCP 7.0.2 used an unpooled H2 datasource. Both pools had a maximum of four connections; Hikari's minimum idle was one. The application returned up to 100 rows on reads; each write read a template, updated counters, and inserted a history row in one transaction. The request mix was four GETs per POST.

The Ubuntu 24.04 QEMU/KVM VM had one vCPU, 512 MiB RAM and no swap. JDK 27 used SerialGC, `-Xms16m` and `-Xmx80m`. Four runs used native/Hikari/Hikari/native order and a fresh JVM and database each time; filesystem caches were not reset. The Linux host generated load through QEMU TCP forwarding. Each run had 20 seconds idle, 30 seconds warm-up at 5 requests/s, 30 seconds light load at 5 requests/s, 60 seconds moderate load at 30 requests/s, and 20 seconds recovery. The generator allowed eight concurrent requests, reused HTTP connections, and used a two-second timeout without retries.

RSS is whole-process resident memory sampled once per second, including embedded H2. Phase means use the samples within recorded phase boundaries. Latency is measured after dispatch. Each moderate phase completed 1,800/1,800 requests without errors, missed slots or timeouts. Post-run checks found 420 history rows and matching counters in each database. Measurements are short and sampled, and cannot isolate pool-specific allocations.

Earlier iterations on an actively used development Mac encountered scheduling delays. Subsequent Linux diagnostics observed an approximately 43 ms latency tail associated with SSH forwarding; QEMU TCP forwarding eliminated it in that diagnostic fixture. The precise SSH mechanism was not established. The final run used QEMU forwarding. Earlier attempts are not included as benchmark comparisons.

## Evidence

The [results](results/) retain phase boundaries, one-second memory samples and phase summaries for each run, plus warm-up and light summaries, individual moderate requests, and post-run database checks. Run directories `1-native`, `2-hikari`, `3-hikari`, and `4-native` correspond to A1, B1, B2, and A2. `memory.json` values are KiB; divide by 1,024 for MiB. Timestamps in samples and phase boundaries are Unix epoch seconds. Request latency excludes dispatch lag. Percentiles use the nearest-rank definition, selecting the sorted successful latency at rank `ceil(n × p)`. The dataset omits VM-specific provisioning, database files and operational logs; it is evidence for the reported run, not a turnkey reproduction bundle.

Run `python3 check.py` to verify the published table, request counts, timing summaries, and sample-derived phase means against the retained evidence. Reproduction requires recreating the described application, load generator, VM, and forwarding setup; this package does not supply those components.
