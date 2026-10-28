# Spring Boot deployment optimizations on JDK 27

An ordinary executable Spring Boot JAR compared with the same application using
extracted layout, Spring AOT and a trained JDK AOT cache, inside a 512 MiB,
1 vCPU, no-swap Ubuntu VM with local MariaDB. Separate follow-ups examine manual
MyBatis integration, file-backed H2, and monitoring with StatLite.

## Three deployment stages

The Oracle follow-up retains the application, MariaDB settings and five-rps
protocol, while changing the deployment toolchain. HotSpot A and F use **JDK 27**;
Oracle GraalVM Native Image uses **JDK 25**, not JDK 27.

| Observation | Standard HotSpot A, JDK 27 | Optimized HotSpot F, JDK 27 | Oracle Native Image, JDK 25 |
| --- | ---: | ---: | ---: |
| HTTP and persistence readiness | 11.91 s | 3.789 s | 0.183 s |
| Workload median app RSS | 212.0 MiB | 186.9 MiB | 107.0 MiB |
| Workload minimum host MemAvailable | 25.6 MiB | 66.0 MiB | 204.9 MiB |
| HTTP p50 / p95 | 3.61 / 5.34 ms | 3.55 / 5.54 ms | 3.46 / 4.84 ms |
| Successful workload requests / errors | 1,500 / 0 | 1,500 / 0 | 1,500 / 0 |

Native median app RSS was 42.7% lower than optimized F in these observations.
Its default build took 707.74 seconds on a separate 6 GiB/two-vCPU builder,
with 5,192,172 KiB OS peak RSS. Runtime heaps have independent `-Xmx80m`
guards; HotSpot G1 and compiled native Serial GC have different memory layouts.
F ran October 23 and native October 28 on separate VMs/boots, with kernel/libc
patch drift. These single runs do not isolate compiler effects, estimate variance,
or establish capacity or long-term safety. Host headroom is measured separately
from process RSS; small latency differences at five rps do not establish a ranking.

See the [Oracle methodology and limitations](oracle-native-image/README.md),
[detailed comparison](oracle-native-image/results/comparison.json),
[build provenance](oracle-native-image/results/build.json) and
[reproduction guide](oracle-native-image/reproduction-guide.md).
Recheck native evidence independently with `python3 oracle-native-image/analyze.py`.
The existing HotSpot results, methods and follow-up evidence below are retained.

## Results

| Observation | Ordinary MariaDB A | Optimized MariaDB F | Optimized file-backed H2 F |
| --- | ---: | ---: | ---: |
| Startup to HTTP and persistence readiness | 11.91 s | 3.79 s | 4.97 s |
| Workload median app RSS | 212.0 MiB | 186.9 MiB | 202.9 MiB |
| Workload minimum host MemAvailable | 25.6 MiB | 66.0 MiB | 104.6 MiB |
| HTTP p50 / p95 | 3.61 / 5.34 ms | 3.55 / 5.54 ms | 3.35 / 5.67 ms |
| Successful requests / errors | 1,500 / 0 | 1,500 / 0 | 1,500 / 0 |

The combined optimized deployment started about 68% sooner and used about
25.1 MiB less median app RSS. The comparison does not isolate the contribution
of extraction or either AOT mechanism. No clear request-latency advantage was
observed at 5 rps. Both A and F completed without OOM or swap, but A had 148 of
298 workload samples below 32 MiB MemAvailable. An earlier preparation OOM is
retained as context in the [method](experiment-method.md).

H2 increased app RSS by about 16 MiB while leaving about 38.6 MiB more host
MemAvailable at the sampled minimum. Its database memory is inside Java RSS;
MariaDB F had a separate database process at about 70.6 MiB median RSS. Database
and fixture residency also varied: app RSS savings do not map one-for-one to
host headroom, and summed process RSS is not exact host consumption.

The MyBatis Core/manual-session capture showed no clear saving against the
matched first minute of JDBC F: median app RSS 186.0 versus 187.2 MiB, idle RSS
181.7 versus 178.7 MiB, startup 3.78 versus 3.79 s. Both matched windows served
300 requests without errors. Six Spring libraries were removed and one MyBatis
JAR added; runtime JAR bytes increased by 768,553. This integration lost automatic
JDBC/pool metrics and datasource health and required manual transaction ownership.
Framework-integrated MyBatis was not tested.

The separate monitored MariaDB F run completed 4,500 requests in 15 minutes
without workload errors. StatLite RSS was 11.9/14.9 MiB median/sampled peak;
minimum host MemAvailable was 48.2 MiB. Its different warm-up schedule and active
health checks prevent a controlled estimate of monitoring overhead.

## Evidence and reanalysis

Run from this directory, with Python 3 and no third-party packages:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 analyze.py
```

The script recomputes request percentiles, phase memory statistics, the matched
MyBatis window and monitoring RSS. It also regenerates both detailed JVM/OS
memory summaries with the original [memory analyzer](memory-observations.py).
It fails if these disagree with the accepted summaries.

- [Method, environment and limitations](experiment-method.md)
- [Data schema and reanalysis scope](reproduction-guide.md)
- [Curation journal](journal.md)
- [A/F accepted comparison](results/comparison.json)
- [Matched MyBatis comparison](results/mybatis-comparison.json) and [dependencies](results/mybatis-dependencies.json)
- [MariaDB JVM/OS observations](results/mariadb-F-memory-observations.json) and [H2 observations](results/h2-F-memory-observations.json)
- [Monitored run summary](results/stability-F-001.json)
- [Dashboard screenshot and provenance](screenshots/README.md)

One run per configuration, fixed A-then-F order and short workloads do not
establish variability, maximum throughput, long-term safety or database
performance equivalence. Boot 4.1.1's tagged requirements list support through
Java 26; the JDK 27 observations are empirical compatibility evidence.

This is a curated data release. It includes sample-level evidence for the
reported memory and HTTP results, not the complete application/build/deployment
source needed to rerun the experiment. Full raw captures, databases, build
artifacts and operator records are excluded. No article is published by this
package.
