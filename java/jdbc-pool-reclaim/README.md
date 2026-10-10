# Idle PostgreSQL connections and Spring Boot's fixed pool

Two Spring Boot instances on one PostgreSQL 16 server either kept every connection they had opened, or released the idle ones. Releasing them reduced PostgreSQL's accounted memory. The pool that leaves HikariCP sizing unset does not release them, because its idle target resolves equal to its maximum.

Run date: 2026-10-07, session `run1007a`. Six valid scenarios, 2,280 of 2,280 measured requests succeeded. Reanalyze the curated series with `python3 analyze.py`. Reproduction notes are in [REPRODUCE.md](REPRODUCE.md).

## What changed

Spring Boot 4.1.1 and HikariCP 7.0.2. `minimumIdle` and `maximumPoolSize` were left unset on the default profile. The running pools resolved both to 10. Hikari's `idleTimeout` retires connections only above `minimumIdle`, so a pool whose idle target equals its maximum stays full after the burst. Hikari documents that fixed-size behavior and recommends it when spike latency is the priority. Its documented `idleTimeout` default is 10 minutes.

| Profile | minimumIdle | maximumPoolSize | idleTimeout | Quiet connections | Quiet PostgreSQL cgroup |
| --- | ---: | ---: | --- | ---: | --- |
| Default sizing | unset, resolved 10 | unset, resolved 10 | off | 10 + 10 | 57.5–57.9 MiB |
| No-reclaim control | 1 | 10 | off | 10 + 10 | 57.4–57.5 MiB |
| Reclaim | 1 | 10 | 10 seconds | 1 + 1 | 28.4–28.5 MiB |

Every profile reached 20 connections at the peak. The 10-second timeout only compressed the recording. It is not a production setting. Lifetime and keepalive were off for all three profiles, so this is pool sizing with retirement either forced off or shortened, not an untouched Hikari configuration.

The no-reclaim row is the control for the obvious one-line change. Starting at `minimumIdle=1` still left 20 connections and about 57 MiB once the pools had grown, because nothing retired the extra idle connections.

## PostgreSQL memory

Cgroup memory is the PostgreSQL cluster's charged memory, including cache. `shared_buffers` was 128 MiB. Connection counts in the table above are medians of ten one-second samples. Each cgroup figure below is the median of the two cgroup readings that fell in the same ten-second window.

| State | Connections | PostgreSQL cgroup |
| --- | ---: | --- |
| Reclaim, both quiet | 2 | 28.4–28.5 MiB |
| Reclaim, one instance still busy | 11 | 42.9 MiB |
| Default or no-reclaim, both quiet | 20 | 57.4–57.9 MiB |
| Reclaim, after both pools reopened | 20 | 57.1 MiB |

The memory followed the connections inside the same reclaim runs: about 28.5 MiB at two connections, about 57.1 MiB after the pools grew back to 20. Private PostgreSQL memory in the quiet window, where it was recorded, was about 12 MiB versus about 36 MiB. The application JVMs stayed around 190–207 MiB either way.

This server allowed 100 connections. Two quiet default pools held 20 of them.

## Reopening

Each instance later received one ten-request wave. Median connection acquisition was 194–207 ms for reclaim and under 3 ms for the pools that had kept their connections. Median request time was about 1.44–1.46 seconds versus about 1.02–1.03 seconds, including the intentional one-second hold. After that wave every pool held 10 connections again.

## Setup

Instance A burst for 16 seconds. Instance B overlapped it and stayed busy until 68 seconds. The quiet comparison is 118–128 seconds, before the revisit. All three profiles ran twice, in mirrored order, with a fresh JVM each scenario. The sampler counted PostgreSQL sessions and read Hikari's active, idle, and total metrics every second. PostgreSQL cgroup memory was requested on every fifth sample and attached when that read finished, about every five seconds. Each published 10-second window therefore has ten connection samples and two cgroup readings. Private and proportional-set-size totals are missing on a reading when a backend disappears during the collection, so some windows have fewer of those values than cgroup readings.

The guest was a 2-vCPU, 1 GiB, swap-off x86_64 VM, Ubuntu 24.04, Temurin 25.0.4.1+1, Serial GC, `-Xms32m -Xmx192m -XX:ActiveProcessorCount=2`. PostgreSQL 16.15 stayed up across all six scenarios. Details and hashes are in [results/run1007a/environment.json](results/run1007a/environment.json).

StatLite ran as an optional dashboard. The screenshots in [screenshots/](screenshots/README.md) were reconstructed after the run. They show request rate and host history. They do not show the connection counts or the PostgreSQL memory. The visible HTTP 5xx spikes came from startup health checks returning 503 while the new application was not yet ready. All 2,280 measured workload requests returned HTTP 200. See the [screenshot notes](screenshots/README.md) for the spike times and counter behavior.

## Limits

The workloads were synthetic ten-connection holds of one second. The retired connections were idle backends, not sessions running large queries or `work_mem` sorts. Two repetitions on one co-located VM are enough to see the mechanism. They are not a general MiB-per-connection formula. Hikari's fixed pool still has the latency advantage measured above when the next burst arrives.
