# Method and recorded execution

Question: can a useful small JSON API with persistent storage and collocated
monitoring retain headroom and predictable responses on a 256 MiB server?

## Environment and applications

Alpine 3.24.2 cloudinit r2, x86_64, Lima VZ/plain mode on an Intel macOS host;
1 vCPU, 256 MiB configured RAM, 214.890625 MiB guest MemTotal, 4 GiB disk,
512 MiB disk swap, swappiness 60. The pinned image URL and SHA-512 are in
[vm.yaml](vm.yaml). OpenJDK 25.0.4+7-alpine-r0, package 25.0.4_p7-r0;
JVM flags `-Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k`.

Both use the same Quotes.java, schema/seed, JDBC queries and transactions,
H2 2.4.240 file storage (CACHE_SIZE=4096 KiB, default WRITE_DELAY=500 ms),
and HikariCP 7.0.2 (one idle/two maximum connections). No ORM, upstream service,
background quote scheduler or live data source. A batch atomically writes three
symbols. Commits here do not certify crash durability.

Javalin 7.2.3 uses Jetty 12.1.12 default thread policy, explicit routes,
Micrometer 1.17.0 and a StatLite adapter, Jackson 2.22.1, and a shaded JAR.
Spring Boot 4.1.1 uses Tomcat 11.0.24 (16 maximum/two spare workers), Spring MVC,
standard Actuator/Micrometer 1.17.1, Jackson 3.1.5, and official tools-mode
extraction. Extraction occurs on the host; launch uses the generated application
JAR and all 51 libraries. No AOT, CDS training, custom classpath or native build.
These are equivalent application contracts with different framework infrastructure
and monitoring integrations, not equal framework capabilities or monitoring costs.

The fixture has 390 one-minute samples for each of AAPL, GOOG and NVDA, sourced
from Yahoo Finance for the 2026-09-30 session. The checked-in CSV is the only
runtime source; [metadata](evidence/fixture-metadata.json) records provenance.

## Preparation and measured phases

Both variants passed Alpine smoke, including payload correctness, batch rejection,
transaction rollback, persistence reopening and metric collection. Spring's
original nested-JAR smokes were preparation only. The efficient extracted layout
was verified before its first measured run; launcher resources and all libraries
matched the original executable bytes. No measured Java source changed between
runs. Rebuilt archives need not have the original hashes due to build metadata.

Reset the same guest between variants, confirm near-zero swap and no old services,
and use fresh H2 and StatLite storage. No page-cache drop or JVM warm-up is carried
into measurement; guest reboot does not guarantee cold host disk/cache state.
Readiness and monitor polling warm some runtime paths before traffic.

| Phase | Duration and collection |
|---|---|
| Unmonitored baseline | 60 s, OS sampler and tunnels present |
| Monitor-only | 90 s; StatLite 0.6.0, 30 s polls, fresh SQLite; two valid self samples |
| Startup | Readiness probes every 100 ms, bounded 1 s requests; 180 s observation limit |
| Idle | 180 s, monitoring and OS sampling only |
| Workload | 1,500 slots at 200 ms intervals, 300 s schedule, up to 2 s drain |
| Recovery | 120 s, no business requests or forced GC |
| Inspection | After recorded cutoff; operator screenshots, then stop writers and collect |

Traffic: 80% GET reads (latest and 60-row history), 20% POST three-row batches,
at most four outstanding requests, persistent HTTP/1.1 connections through the
same SSH tunnel. No retries. Record missed slots and validate status and payload.
Both runs finished with 2,070 rows, max sequence 689 and price sum 630374.22.

OS samples use /proc: one second during startup, five seconds otherwise. RSS is
resident process memory, not heap; MemAvailable is host headroom. Swap occupancy
and paging volume are distinct. CPU uses tick deltas with CLK_TCK=100 and 4096-byte
pages. Busy excludes idle, I/O wait and steal when available. HTTP percentiles
use nearest-rank; times include the local tunnel. Phase paging uses first/last
sample counters within each phase, not exact boundary counters.

## Predeclared interpretation criteria

| Criterion | Rule |
|---|---|
| Startup | Ready within 60 s; no crash, stack overflow or OOM |
| Correct traffic | All 1,500 slots complete correctly; matching final persisted state |
| Headroom | At least 24 MiB MemAvailable in idle/load/recovery; startup dips separately reported |
| Memory growth | No rise exceeding 8 MiB from load minute 3 to 5 with falling host headroom |
| Paging | No swap-in/out above 1 MiB/s sustained for 30 s in idle/load/recovery |
| Latency | Overall/per-route/minute p95 ≤200 ms; no successful request above 1 s |
| Recovery | Settled memory/headroom, paging below rule, final-minute busy CPU ≤late-idle mean +5 percentage points |

Both passed these rules. Spring's substantial paging still represents operational
memory pressure, so pass status does not establish low-pressure or swap-free
comfort. See [RESULTS.md](RESULTS.md).

## Execution notes and limitations

Javalin ran first at 21:25:22 UTC; its measurement ended 21:37:55 UTC.
Spring ran second at 22:13:34 UTC; monitor started 22:14:34, Java 22:16:04,
workload 22:19:14–22:24:14, cutoff 22:26:14 UTC on 2026-10-08.
Brief SSH refusals while reboot completed were resolved before measurement.
Both completed and were archived after operator inspection; no OOM was found.

Javalin's original sampler omitted steal-time counters. Its raw samples are
preserved, exact busy CPU is unavailable, and corrected busy-plus-steal upper
bounds are reported separately from I/O wait. The Spring sampler includes steal
and raw CPU lines. This sampler revision limits exact CPU comparisons; it does
not change the measured application, RAM, workload or paging counters.

Missing history-symbol and null SQLState error paths were found during review.
Fixes were tested separately and deferred to preserve measured binaries. Original
successful workload paths were unaffected. The public source retains these known
limitations; the unapplied patch and regression check are in
[checks/post-measurement](checks/post-measurement/README.md).

Screenshots include post-cutoff history; current cards show inspection state.
Javalin DB health displays Not reported; SQL/state verification is independent.
One short run per variant in fixed order, local Alpine VM, swap-enabled host and
framework-specific infrastructure do not establish long-term leaks, provider VPS
performance, production capacity or general framework superiority.
