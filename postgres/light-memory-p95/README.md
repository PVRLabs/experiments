# PostgreSQL 18 on a Small VPS: Two Low-Memory Tuning Strategies

Can PostgreSQL serve a small application efficiently on a memory-constrained VPS? We compared two configurations with PostgreSQL 18.6 defaults. The successful comparison ran on a 512 MiB VM, not 256 MiB; an earlier 256 MiB preparation attempt ran out of memory. No application was deployed alongside PostgreSQL.

## Configurations

Both alternatives limit PostgreSQL to five connections, reserve one for a superuser, disable JIT and parallel queries, and retain fsync, autovacuum and standard replica WAL. [Theory A](config/theory-a.conf) reduces shared buffers to 16 MB, work memory to 1 MB and maintenance work memory to 16 MB, retaining PostgreSQL 18's default worker I/O. It leans on the OS filesystem cache. [Theory B](config/theory-b.conf) uses 32 MB shared buffers, default query memory and synchronous I/O. The [baseline](config/default.conf) has no experiment overrides. These are configuration bundles, not an attribution of individual settings.

## Method and results

The local Ubuntu VM had one vCPU, 512 MiB allocated (approximately 456 MiB usable), and no swap. The 222 MB fixture was loaded once. Four persistent non-superuser connections concurrently executed point lookups, range queries and an aggregate with a sort. Each variant had five seconds idle, 20 seconds warm-up and 50 seconds measurement, in fixed order default, A, B. The filesystem cache was not cleared. PSS, summed RSS, MemAvailable and swap counters were sampled approximately once per second; query latency and throughput were recorded by the driver.

| Metric | Default | Theory A | Theory B |
|---|---:|---:|---:|
| Peak sampled PSS | 180.1 MiB | 50.4 MiB | 79.7 MiB |
| Idle median PSS | 39.2 MiB | 28.7 MiB | 27.5 MiB |
| Measured median PSS | 172.4 MiB | 49.3 MiB | 75.3 MiB |
| Throughput, queries/s | 863 | 1,056 | 861 |
| Point p95 | 2.90 ms | 2.64 ms | 2.92 ms |
| Range p95 | 1.95 ms | 1.93 ms | 2.09 ms |
| Aggregate p95 | 98.55 ms | 74.25 ms | 103.18 ms |

Peak is the highest sample across idle, warm-up and measurement. B peaked at 81,655 KiB during warm-up; its measured peak was 81,630 KiB. PSS apportions shared pages among processes, while summed RSS counts shared pages repeatedly; PSS is therefore more useful for this PostgreSQL process footprint. Neither is the full VPS memory cost: OS services and filesystem cache also consume memory. No driver errors or swap activity were observed.

Theory A is the preferred configuration for this workload: it used less process memory and showed higher throughput and lower p95 values in this run. This does not establish that A is universally faster. The sort spilled under both query-memory settings during preparation.

## Apply Theory A

On Debian/Ubuntu the cluster configuration usually lives under `/etc/postgresql/18/main/`. Find the active file with `SHOW config_file;` in `psql`. Add the following settings to that file or an included configuration file, checking for later overrides:

```conf
max_connections = 5
superuser_reserved_connections = 1
jit = off
max_parallel_workers_per_gather = 0
max_parallel_workers = 0
shared_buffers = '16MB'
work_mem = '1MB'
maintenance_work_mem = '16MB'
```

Restart the cluster, for example `sudo systemctl restart postgresql@18-main` on Debian/Ubuntu: connection limits and shared buffers require restart. Verify with:

```sql
SELECT name, setting, unit, pending_restart FROM pg_settings
WHERE name IN ('max_connections','superuser_reserved_connections','jit',
 'max_parallel_workers_per_gather','max_parallel_workers','shared_buffers',
 'work_mem','maintenance_work_mem','io_method','fsync','autovacuum','wal_level')
ORDER BY name;
```

Five slots include the reserved superuser slot, leaving at most four ordinary client connections when no other reservations apply. Size all application pools and operational access accordingly. Query memory is per operation, not a global cap; a low value may cause disk spills. Keep durability and maintenance enabled.

## Limitations

One short run per configuration, fixed order and a warm cache limit comparisons. The workload was read-only and does not evaluate sustained writes or autovacuum. Background guest services could have interfered. The failed 256 MiB preparation is not a successful 256 MiB result. Other applications may need more connections or query memory; test with their own workload and full host budget.

## Reproduction and evidence

The [scripts](scripts/) include the fixture, four-client driver, sampler, variant setup and analysis; [original samples and summaries](results/) include all measured query latencies and memory samples. The scripts target a disposable Debian/Ubuntu PostgreSQL 18 cluster and alter its configuration and service. They require Python 3, `python3-psycopg2`, PostgreSQL 18, sudo and Linux `/proc`. The fixture uses an intentionally simple local-only test role and password; never use it on a production or network-exposed database.

On a fresh isolated guest with a default `18/main` cluster and no swap, install dependencies, then from this directory:

```sh
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -f scripts/fixture.sql
sudo scripts/run.sh /tmp/pg-light-results
```

The output directory must not exist. `run.sh` restarts and stops the cluster for each variant and writes settings, samples and summaries. It assumes local TCP password authentication for the fixture role. The baseline startup checks the twelve captured settings and stops if any differ; use a fresh, unmodified PostgreSQL 18 cluster because other settings are not checked. Confirm available disk and authentication first; use a dedicated guest, and do not reuse production data. The original VM was local x86-64 Lima/VZ on macOS; guest Linux was 6.8.0-134-generic. Different hardware, host activity, packages and caches can change results. The scripts sample all processes owned by the postgres account and require root access to `smaps_rollup`; dedicate that account to the tested cluster. Run `scripts/analyze.py results/default` (and `a`, `b`) to reanalyze the included measured samples. Its peak output is per phase; calculate the overall peak across all phases as described above.
