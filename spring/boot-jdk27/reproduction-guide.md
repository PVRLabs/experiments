# Reanalyzing the curated evidence

Use Python 3; all analysis uses its standard library. From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 analyze.py
```

The command reads only files shipped here, prints per-run observations and checks
accepted A/F, matched MyBatis and monitored memory/HTTP values. It also reruns the
original JVM/OS observation function and compares its complete output against
both saved memory summaries. It does not launch a VM, install software or run load.

## Files and units

Each `data/<run>/` directory contains:

- `samples.csv`: original sample order, monotonic seconds, phase, MemAvailable
  and swap-used MiB, cumulative host OOM counter, and per-process RSS MiB.
  A blank process field means absent, not zero. Phase transitions are retained
  for inspection but excluded from steady summaries. Monotonic clocks are local
  to each run and should not be aligned between boots.
- `requests.csv`: recorded workload only, preserving request index, endpoint,
  UTC Unix epoch seconds, status, success, latency milliseconds and dispatch lag
  milliseconds. No retries. Percentiles use nearest rank over successful requests.
- `workload-summary.json`: original external workload summary, including timing,
  route percentiles, offered rate and concurrency limit. Warm-up requests are
  excluded from the request CSVs.
- `startup.json`: original seconds to combined HTTP/persistence readiness where
  available; command lines and operator filesystem paths were omitted. The
  monitoring release has no startup record in this package.

Optimized MariaDB and H2 additionally include `memory-samples.jsonl` (workload
phase and the nine consumed app `/proc` memory fields only) and `memory-metrics.jsonl` (workload
phase and only the JVM memory/buffer/thread/class gauges consumed by the
analyzer). These retain the input values used in the accepted memory summaries,
without unrelated Prometheus labels or process command lines.

`results/` contains unchanged accepted JSON summaries. `mariadb-memory-observations`
from the separate monitored addendum is deliberately omitted: the paired
unmonitored MariaDB F/H2 F observations are the relevant category comparison.
The sample extraction is a projection of existing evidence, not a new measurement.

## Scope of verification

CSV projections permit checking memory distributions, pressure signals and
workload outcomes without distributing multi-megabyte raw `/proc` captures,
monitor databases or build output. The accepted summaries retain additional
observations such as boot identities, CPU/PSI deltas, ingestion checks and
final kernel review. Those fields are archival summaries; this reduced package
does not independently recompute them. Startup values are retained observations,
not independently reconstructed from a startup event trace. Dependency inventories
are retained summaries, not a replacement for the original packaged JARs.

Full deployment reproduction requires the application, fixture, build/cache
training and VM orchestration sources, which are not part of this data release.
The [method](experiment-method.md) specifies the recorded workload and environment;
do not treat this reanalysis command as a complete experiment runner.
