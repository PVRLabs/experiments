# MyBatis vs. jOOQ vs. Jdbi on 256 MiB

Three Javalin JSON services using SQL-first persistence libraries, file-backed H2,
HikariCP and collocated StatLite on an Alpine Linux VM. One recorded run per
implementation, five minutes of traffic at five requests/second. All 1,500
requests succeeded in each run and the final database states matched.

| Recorded measurement | Jdbi Core | MyBatis Core | jOOQ OSE, original artifact |
|---|---:|---:|---:|
| Version | 3.55.0 | 3.5.19 | 3.21.9 |
| Readiness | 4.13 s | 3.59 s | 4.44 s |
| Workload median Java RSS | 112.83 MiB | 110.55 MiB | 112.19 MiB |
| HTTP p95 | 7.39 ms | 8.23 ms | 9.34 ms |
| Workload swap-in / swap-out | 0.20 / 0.05 MiB | 0.12 / 0.00 MiB | 19.11 / 31.19 MiB |
| Handwritten Java lines, excluding shared adapter | 207 | 358 | 280 |

These are observations from complete applications, not isolated library overhead
or a stable ranking. The jOOQ run had more paging; this does not establish its cause.

- [Experiment write-up](https://pvrlabs.xyz/java-performance/experiments/mybatis-jooq-jdbi-256mb.html) and [Markdown text](ARTICLE.md).
- [Reanalysis, builds and VM reproduction](reproduction-guide.md).
- [Curated execution record and limitations](experiment-design.md).
- [Original JDBC/Spring experiment](../vps-256mb/), retained separately.
- [Jdbi detailed result](JDBI3-RESULTS.md).
- [jOOQ correction](jooq-correction.md) and [historical measured source](historical/jooq-release-002/).

## Source and evidence layout

`javalin-jdbi3/` and `javalin-mybatis/` contain measured application sources.
`javalin-jooq/` contains the corrected fixture loader, which was checked on the
host but has not been measured in the VM. Reconstruct the measured jOOQ source
by replacing its repository with the separately preserved historical file.
The recorded 4.44-second startup and 280-line count belong to that original source.

`results/` contains original OS samples, HTTP events, phase/readiness timestamps,
final state, analyses and input manifests. `evidence/` contains dependency and code
inventories, original input manifests and the correction check. Original manifest
keys retain the archive's layout; reproduction-guide.md explains the public source mapping.
`generated-schema/` preserves the six generated jOOQ Java sources for inspection;
Maven regenerates them from the included DDL rather than compiling this copy.

The original measured binary is identified by its recorded hash; binary artifacts
are not distributed here. Historical rebuilding matched every JAR entry's contents;
ZIP timestamps differed. Git records public file history. Existing provenance
hashes are retained; no additional per-file checksum manifest is needed.

The public package intentionally excludes private journals, session logs, raw
H2/SQLite databases, VM disks, local environment captures and compiled output.
