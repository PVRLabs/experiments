# Javalin with JDBC and monitoring on 256 MiB

Curated evidence and reproduction code for a small engineering experiment,
recorded on 2026-10-08. A Javalin JSON API and a functionally equivalent Spring
Boot application each ran on the same constrained Alpine VM with file-backed
H2 and StatLite monitoring. This was a local VPS-sized VM, not a provider VPS
or a saturation benchmark.

Both completed 1,500 correct requests at five requests/second. Javalin started
in 2.458 seconds versus 9.893 seconds for Spring, with more system memory
headroom and substantially less workload paging. Spring passed the original
thresholds but reached approximately 100 MiB swap occupancy, with 27.23 MiB
swapped in and 31.77 MiB out during traffic. Successful operation under this
workload does not establish comfortable operation with little memory pressure.
One targeted Spring repeat is recommended before a strong comfort claim.

| Metric | Javalin | Spring Boot |
|---|---:|---:|
| Startup to readiness | 2.458 s | 9.893 s |
| Median load Java RSS | 106.43 MiB | 118.56 MiB |
| Minimum settled MemAvailable | 69.76 MiB | 45.28 MiB |
| External HTTP p95 | 6.094 ms | 8.393 ms |
| Correct requests | 1,500 / 1,500 | 1,500 / 1,500 |
| Workload swap-in / swap-out | 0.32 / 0.00 MiB | 27.23 / 31.77 MiB |

## Contents

- [RESULTS.md](RESULTS.md): paired analysis, paging interpretation and limitations.
- [METHOD.md](METHOD.md): settings, phases, thresholds and execution deviations.
- [REPRODUCE.md](REPRODUCE.md): build, deploy, smoke, reset, measure and analyze.
- `common/`, `javalin-app/`, `spring-app/`: original measured source and fixture.
- `results/`: original OS/HTTP/probe/phase records, final corrected analyses and
  original operator screenshots with captions.
- [evidence/inputs.json](evidence/inputs.json): versions, measured source/artifact
  hashes and Spring extraction verification. Original binaries are not included.
- `tools/`: shared Lima transfer/deployment/capture helpers used by reproduction.
- `checks/`: CPU accounting tests, preparation transaction check and unapplied
  post-measurement Java error-path fixes with regression checks.

One run per framework, Javalin first, limits generalization. The guest exposed
214.89 MiB RAM with 512 MiB disk swap. Measurements include H2, the selected JVM
policy and framework-specific monitoring. Javalin's original CPU samples lack
steal-time data; corrected busy-plus-steal is an upper bound, not exact busy CPU.

The article draft, operator journal, databases, generated binaries, agent logs,
private paths and machine-specific captures are excluded. Recorded samples are
unchanged. Public run metadata is reduced to variant/smoke flags, and reproduction
helpers are adapted to this self-contained package. `SHA256SUMS` fingerprints the
reviewed public files, not the private archive.
