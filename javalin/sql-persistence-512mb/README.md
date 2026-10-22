# Jdbi, MyBatis and jOOQ in 512 MiB

**[Read the short write-up →](https://pvrlabs.xyz/java-performance/experiments/mybatis-jooq-jdbi-512mb.html)**

Two unmonitored runs per SQL persistence implementation in a small Javalin
market-quote API, followed by one separately selected MyBatis run with StatLite.
Measured on 19 October 2026. This is a practical case study, not a universal
library ranking, production-capacity test or full-framework benchmark.

| Implementation | Version | HTTP p95 across two runs, ms | Median workload RSS across two runs, MiB |
| --- | --- | ---: | ---: |
| Jdbi Core | 3.55.0 | 7.38–8.48 | 120.0–122.4 |
| MyBatis Core | 3.5.19 | 7.47–7.52 | 116.6–118.0 |
| jOOQ Open Source Edition | 3.21.9 | 9.19–9.35 | 152.1–154.3 |

All six main runs completed 1,500 requests correctly, with zero workload errors,
no OOM and no swap. MyBatis consistently had the lowest median workload RSS;
Jdbi/MyBatis p95 ranges overlap. jOOQ had a larger resident footprint here.
Two repetitions provide only a basic consistency check.

The operator selected MyBatis for the combination of measured resource use and
prior preference for its annotation-driven mapper model. Its separate monitored
repeat completed another 1,500 requests correctly, at 8.29 ms p95 and 121.4 MiB
median app RSS. StatLite v0.6.0, polling every 30 seconds, had 15.0 MiB median RSS
during workload. One monitored repeat cannot isolate causal monitoring overhead.

## Evidence and source

- [Method, environment, per-run results and limitations](experiment-method.md)
- [Reanalysis and reproduction](reproduction-guide.md)
- [Six-run comparison](main-comparison.json), [seven-run comparison](complete-comparison.json), and [MyBatis monitored comparison](monitored-comparison.json)
- [Jdbi repository](javalin-jdbi3/src/main/java/lab/JdbiQuoteRepository.java)
- [MyBatis repository](javalin-mybatis/src/main/java/lab/MyBatisQuoteRepository.java) and [annotated mapper](javalin-mybatis/src/main/java/lab/QuoteMapper.java)
- [jOOQ repository](javalin-jooq/src/main/java/lab/JooqQuoteRepository.java), [schema](javalin-jooq/src/main/resources/schema.sql), and [generated schema snapshot](generated-schema/)
- [Measured build/dependency inventory](evidence/measured-build-inventory.json), [host preparation check summary](evidence/host-check-summary.json), and [frozen preparation record](results/preparation/preparation-compact-002.json)
- [Original operator screenshots and captions](screenshots/README.md)

Run `python3 reanalyze.py` here using Python 3 and no external packages. It
recomputes every analysis and all comparisons from the curated data only.

This is separate from the [original 256 MiB experiment](../sql-persistence-256mb/),
which used swap, StatLite and one run per library. Its results remain valid for
that configuration. The reviewed corrected jOOQ implementation here was measured
twice; the historical package's original measured jOOQ source remains distinct.
Do not pool the old and new measurements or interpret the change as RAM alone.

## Curation scope

Application Java sources, POMs and fixtures preserve measured source bytes.
Recorded run metadata, OS CSV, request JSONL, phase/readiness evidence, final
state and per-run analyses are preserved. The recorded source revision refers
to the original private preparation checkout, which explicitly recorded dirty
state; the full measured application source is included here. Rebuilt JAR
hashes may differ because ZIP timestamps and build environments differ.

Harness edits relocate imports and helper paths for this self-contained public
layout. Comparison summaries use public relative paths. Reproduction preparation
accepts an explicit released monitor binary and records new build identities.
These edits do not change archived measurements or the workload. The one-page
MemTotal comparison tolerance is disclosed in the method.

No private journals, agent logs, application logs, raw H2/SQLite databases,
compiled applications, caches, host captures or machine-specific VM paths are
included. Original SQLite integrity checking is recorded, not repeatable without
the omitted database. The screenshots preserve a useful view of monitoring;
the public data independently supports the OS/HTTP results.
