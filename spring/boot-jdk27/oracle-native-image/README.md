# Optimized Spring Boot HotSpot F versus Oracle Native Image

Accepted 2026-10-28: the unchanged Market Replay application passed native
functional validation, two short pipeline smokes and one full deployment run.
This is the Oracle native follow-up to the JDK 27 HotSpot investigation. The
operator explicitly authorized the installed Oracle compiler, overriding the
original requirement that the native compiler itself be based on JDK 27.
The completed Liberica experiment is excluded from this primary comparison.

| Observation | Optimized HotSpot F | Oracle Native Image |
| --- | ---: | ---: |
| Readiness: health UP plus three persisted quotes | 3.789 s | 0.183 s |
| Idle app RSS, median | 178.7 MiB | 106.8 MiB |
| Workload app RSS, median / sampled peak | 186.9 / 189.2 MiB | 107.0 / 107.6 MiB |
| Workload MariaDB RSS, median | 70.6 MiB | 71.6 MiB |
| Workload fixture RSS, median | 19.1 MiB | 22.4 MiB |
| Workload host MemAvailable, minimum | 66.0 MiB | 204.9 MiB |
| Workload app / DB sampled CPU time | 6.28 / 0.64 s | 1.67 / 0.73 s |
| Workload HTTP p50 / p95 | 3.55 / 5.54 ms | 3.46 / 4.84 ms |
| Successful workload requests / errors | 1,500 / 0 | 1,500 / 0 |

Median application RSS was **42.7% lower** in this native observation. Readiness
was much shorter; small latency differences at five offered rps do not establish
a ranking or capacity limit. Host headroom is an independently observed result,
not a subtraction of process RSS or a compiler-isolated saving.

## Method and provenance

Both deployments use Ubuntu 24.04 x86_64, one vCPU, 512 MiB allocated RAM
(about 456 MiB MemTotal), no swap, local MariaDB and the deterministic Python
fixture in the same budget. Hikari minimum/maximum is 1/4. Database caches are
64/8/16 MiB for InnoDB/key/Aria, with the same durability and other recorded
settings. The measured DB snapshot matches historical F. Boot 4.1.1, Framework
7.0.9, Tomcat 11.0.24, HikariCP 7.0.2 and MariaDB driver 3.5.10 were verified
from the generated dependency inventory; hinted application inputs matched the
previously accepted source byte-for-byte. No framework changes were made.

HotSpot F uses OpenJDK 27+35-2325/G1, extracted layout, Spring AOT and trained
JDK AOT cache. Native uses **Oracle GraalVM 25.0.4+7.1**, Java build
**25.0.4+7-LTS-jvmci-b01**, Substrate VM **25.0.4+7-LTS**, compiled Serial GC.
Both launch with an independent -Xmx80m guard; their heaps and memory layouts
are not equivalent. This native executable is not based on JDK 27.

After preparation, the builder was stopped and the runtime fresh-booted. Payload
verification and schema preparation intentionally warmed filesystem state.
Readiness polling was approximately 50 ms. Phases were 60 seconds idle, 120
warm-up, 300 workload, 60 recovery. The host offered five alternating latest/history
reads per second, at most four in flight, no retries. Minute ingestion continued;
OS sampling was about one second and metrics every ten seconds. StatLite and
periodic explicit DB checks were off; update services were stopped/inactive.

600/600 warm-up and 1,500/1,500 workload requests passed. Ten ordered batches
produced 30 rows; process identities, sample/phase spans, SQL export, shutdown,
request percentiles and collection passed reanalysis. There were no OOM kills,
swap use or workload samples below 32 MiB MemAvailable. CPU/RSS summaries exclude
phase transitions. The full comparison includes all phase measurements.

## Build and compatibility cost

The default native Maven build took **707.74 seconds (11m 47.74s)** on the separate
6 GiB/two-vCPU Linux builder, with **5,192,172 KiB (5,070.5 MiB)** OS peak RSS;
the compiler reported 5.32 decimal GB peak. The executable is **112,527,624 bytes**;
six emitted companions bring the full payload to **114,066,296 bytes**.
Optimization was 2, CPU target x86-64-v3, with built-in ML-inferred profiles.
There was no optimization matrix, custom profile or compiler heap tuning.
This is one complete build with a populated Maven cache, not a controlled
comparison with old build costs. A deployment JVM/JAR build cost was not rerun.

The actual packaged executable passed all eight native checks: JSON binding,
API/UI, persistent restart, late-insert transaction rollback and connection release,
HTTP timeout and DB outage recovery, history bounds/decimal/UTC mapping,
configuration and graceful shutdown. The rollback fault reached the first two
inserts, left 12 persisted rows unchanged and released the active connection.
Two separate 2/2/12/2 pipeline smokes each passed 70/70 requests; their data is
excluded from measurement. Existing focused JSON-binding compatibility fixes
were reused. No macOS native build or framework comparison was added.

## Limitations and evidence

Historical F was measured on October 23; native on October 28, on separate
VMs/boots. Fresh boot loaded an installed OS update: native kernel 6.8.0-147
and libc 2.39-0ubuntu8.9 versus historical kernel 6.8.0-134/libc 8.7. A short
smoke passed on the updated kernel. This patch drift, different compilers/collectors
and ordinary host variation prevent isolating a compiler effect. No material
application/DB/workload mismatch was found that justified rerunning F.

One observation per configuration does not estimate variance, maximum throughput,
long-term stability or minimum framework memory. Sampled peaks may miss spikes;
RSS can double-count shared pages. Native logs warn that GC notifications are
unavailable; missing diagnostics are not zero. Unused AWT functionality was not
exercised despite retaining its emitted libraries. Startup and functional/compiler reports are
retained observations; curated sample/request arithmetic can be rechecked offline.

See [comparison](results/comparison.json),
[build provenance](results/build.json), [functional checks](results/functional.json),
[environment](results/environment.json) and [reproduction](reproduction-guide.md).
The baseline is the independently
[published F dataset](https://github.com/PVRLabs/experiments/blob/main/spring/boot-jdk27/results/comparison.json),
verified against the published dataset at curation.
Run `python3 analyze.py` here to verify the curated data.
See [the three-stage comparison](../README.md) for standard and optimized HotSpot results.

The [curation journal](journal.md) records publication checks.
