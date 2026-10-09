# Recorded evidence, run1007a

Recording on 2026-10-07. Six scenarios, mirrored order: `default-1`, `no-reclaim-1`, `reclaim-1`, `reclaim-2`, `no-reclaim-2`, `default-2`.

`summary.csv` is the session summary produced from the original one-second samples. Each scenario directory keeps the files needed to check it:

- `series.csv` keeps one row per second: PostgreSQL counts, Hikari active/idle/total, PostgreSQL cgroup, PSS and private memory, JVM RSS, and `MemAvailable`. A blank cgroup cell means that one-second row did not receive a memory reading. Readings were requested every fifth sample and are about five seconds apart, so each 10-second comparison window has ten connection samples and two cgroup values. Full Prometheus exposition, per-backend process lists, and raw `/proc/meminfo` text are omitted.
- `requests.csv` is the workload log, including the excluded serial warm-up.
- `run.json` is the scenario timing and validity record.
- `mechanism-check.json` is the late B-busy connection check. It keeps the per-sample Hikari and PostgreSQL counts. Per-backend process rows from the original check are omitted.

`environment.json` is the sanitized host, JVM, and PostgreSQL record. `manifest.json` is the deployed-bundle fingerprint from the run.

Regenerate the check from this directory's parent with `python3 analyze.py`.
