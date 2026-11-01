# StatLite memory with multiple targets

How much does StatLite's resident memory change when it monitors more targets? This short local spike measured a single StatLite v0.7.1 process with 1, 6, and 12 active targets. It is an approximation, not a benchmark.

| Targets | Startup baseline RSS | Median RSS | Peak RSS | Successful polls |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 2.75 MiB | 14.51 MiB | 15.15 MiB | 5 |
| 6 | 2.30 MiB | 16.48 MiB | 17.50 MiB | 30 |
| 12 | 2.38 MiB | 17.55 MiB | 18.19 MiB | 60 |

Median RSS increased by **3.04 MiB (about 21%)** from 1 to 12 targets; peak RSS also increased by 3.04 MiB. Each target completed five successful polls, and no failed polls were stored. Dividing the median difference by the 11 additional targets gives about 0.28 MiB per target for this particular comparison; it is not a general per-target capacity estimate.

## Method

On October 31, 2026, the existing macOS x86-64 StatLite v0.7.1 binary (SHA-256 `7627f97ada10162a9c65d91140a081c523fea55d01d2007abefc41e246c51256`) monitored a local Python HTTP fixture. The fixture served StatLite Metrics v1 JSON at 12 distinct URLs, with changing cumulative request, error, and duration values simulating modest HTTP activity. All paths used the same synthetic pattern.

The three configurations ran sequentially for approximately 122 seconds each, using 30-second polling, a five-second timeout, and a fresh SQLite database. `ps -o rss=` sampled the StatLite PID approximately once per second (121 samples per run); the Python fixture was excluded. The baseline is the first nonzero sample immediately after launch, before startup settles. Median and peak cover the entire run. Successful poll counts are SQLite `polls` rows with status `ok`; six metric samples were stored per successful poll. The [summary data](results.jsonl) preserves the original KiB values and poll counts; individual RSS samples were not retained.

## Reproduce

On macOS with Python 3 and a StatLite binary available, run:

```sh
python3 run.py /path/to/statlite
```

The [runner](run.py) starts the local fixture, generates the three configurations and fresh databases, samples RSS, and prints the results. It writes temporary artifacts to the directory it prints. Ports 18765 and 18766 must be available. A complete run takes about six minutes. `ps` RSS units and behavior are platform-dependent; the reported measurements are from macOS.

## Limits

These are single short runs on one machine, with identical lightweight local payloads and synthetic counters rather than application traffic. They do not characterize variability, long-term retention, different platforms, real integrations, or larger target counts. Startup RSS is not a steady-state baseline; allocation and garbage collection affect the median and peak, and one-second sampling can miss brief peaks.
