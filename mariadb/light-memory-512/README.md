# MariaDB on a 512 MiB VM: Defaults vs. Two Lightweight Configurations

How much room does MariaDB need for a small read workload? All three configurations completed on a 512 MiB VM. In an earlier [256 MiB run](results/256-mib/), stock and A were OOM-killed; only B completed. These are exploratory, database-only runs, not a budget for a database colocated with an application.

## Results

| VM | Variant | Outcome | Peak PSS | Completion rate | Point p95 | Range p95 | Aggregate p95 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 512 MiB | Stock | Completed | 215.9 MiB | 788.3/s | 3.15 ms | 4.27 ms | 93.57 ms |
| 512 MiB | A | Completed | 125.6 MiB | 933.6/s | 3.05 ms | 4.26 ms | 92.02 ms |
| 512 MiB | B | Completed | 93.6 MiB | 873.2/s | 3.36 ms | 4.68 ms | 103.70 ms |

Peak PSS is the maximum across all sampled phases. Completion rate counts queries initiated during the measurement window and completed after draining, divided by the window duration. All completed runs had complete memory sampling and no swap or OOM. Each is a single run, without a variance estimate.

At 512 MiB, B saved about 32 MiB peak PSS versus A, with lower throughput and higher p95 in this run. A's savings versus stock reflect the entire profile, not just its InnoDB pool. See the separate [PostgreSQL experiment](../../postgres/light-memory-p95/) for similar-workload context; its SQL plans and fixture size differ, so it is not an equivalent database comparison.

## Method

Ubuntu 24.04 MariaDB 10.11.14 package defaults were the stock baseline: 128 MiB InnoDB buffer pool, 128 MiB MyISAM key cache, 128 MiB Aria page cache and 151 maximum connections. A used a 64 MiB InnoDB pool, 8 MiB key cache, 16 MiB Aria cache, and 10 maximum connections, plus loopback binding and UTC. B changed only A's InnoDB pool to 32 MiB. Durability and other server settings remained at package defaults; effective settings are recorded alongside the results.

The 512 MiB guest had one vCPU, no swap and 467,304 KiB usable RAM. The fixture had 520,000 rows and occupied approximately 164 MiB including indexes. Four persistent connections ran a 75% point lookup, 20% short primary-key range and 5% 12,000-row sort mix. Each variant had 5 seconds idle, 20 seconds warm-up and a 50-second query initiation window. Queries in flight were drained before final counters were read.

Runs proceeded stock, A, then B. MariaDB was stopped and its saved InnoDB buffer-pool file removed before each start. OS cache could carry between variants, although the effective InnoDB flush method was `O_DIRECT`. PSS, RSS and host counters were sampled at approximately one-second intervals. The read-only workload does not measure flush or binary-log costs. Short, fixed-order single runs on a local VM cannot establish general database efficiency or predict production behavior.

## Reproduction and analysis

The [VM definition](vm-512.yaml) and [scripts](scripts/) record the setup, fixture, workload and collection. Use a disposable Ubuntu 24.04 guest: setup installs MariaDB and disables automatic updates and MariaDB startup; fixture and variant scripts alter database state and server configuration. The VM image is pinned, but package repositories can change, so a later installation may not reproduce the same MariaDB version or package defaults. Install with `sudo bash scripts/setup.sh`, create the fixture with `sudo bash scripts/load-fixture.sh`, then run `sudo bash scripts/run-sequence.sh /tmp/mariadb-run measured`. If an OOM interrupts the sequence, reboot and resume with the same output directory and the next variant (`a` or `b`) as the third argument. Run a separate `smoke` sequence first. Fixture creation uses B and drops clean page cache between insert batches; measured runs do not drop it. Review the scripts before running them on a dedicated guest.

Recalculate a result using the included samples, for example:

```sh
python3 scripts/analyze.py results/512-mib/b/samples
```

The summaries and samples retain the completed runs. Memory evidence requires adequate sample coverage, a completed measurement window, and no driver error or OOM. See the analyzer for the precise checks.
