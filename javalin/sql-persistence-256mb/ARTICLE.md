# MyBatis vs. jOOQ vs. Jdbi: Java Persistence on 256 MB RAM

## Why compare SQL-first persistence libraries?

The earlier Javalin and Spring Boot experiment used raw JDBC to keep database work explicit. For an application I would maintain, I also wanted to compare libraries that take over some of that work.

This experiment records runtime, package, and application-code measurements for Jdbi Core, MyBatis Core, and jOOQ Open Source Edition in the same Javalin application on a 256 MiB server. It describes the implementation responsibilities and observed resource use of explicit SQL APIs and a type-safe SQL DSL, using conventional HotSpot and minimal infrastructure.

## Shared application and setup

All three variants use the same plain Java repository contract and domain records, constructor-injected controller, explicit application wiring, H2 file database, HikariCP pool, StatLite monitoring, JVM flags, routes, fixture, SQL semantics, and workload. The controller remains independent of each persistence library. Each implementation uses explicit repository construction and keeps framework-specific failures inside its persistence layer, while using idiomatic internals for its library.

The common 256 MiB experiment configuration used an Alpine Linux 3.24.2 VM with one vCPU, 256 MiB nominal memory (about 214.9 MiB guest `MemTotal`), 512 MiB swap, and swappiness 60. The runtime was OpenJDK 25.0.4 with `-Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k`. StatLite 0.6.0, the monitor I develop at PVR Labs, polled at 30-second intervals. The workload lasted five minutes and scheduled 1,500 requests at five per second, with an 80/20 read/write mix and at most four outstanding requests. The [MyBatis implementation and measurement record](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/experiment-design.md) documents checks, inputs, and deviations.

There is one completed run per library. The measurements describe these applications and do not establish a statistically reliable ranking.

## Jdbi Core implementation and measured results

The completed Jdbi variant uses Jdbi Core 3.55.0. A plain `QuoteRepository` interface sits between the controller and `JdbiQuoteRepository`; the application wires Hikari, Jdbi, repository, and controller explicitly. SQL and database-error translation stay in the persistence layer. There is no DI container or extra service layer. Latest quotes use three queries on one handle; Jdbi constructs a query for each symbol where the raw JDBC baseline reused one prepared statement.

The measured run completed all 1,500 requests correctly and retained useful system headroom, with small workload paging:

| Jdbi Core result | Measurement |
|---|---:|
| Readiness | 4.13 s |
| Idle median Java RSS | 101.55 MiB |
| Workload median Java RSS | 112.83 MiB |
| Recovery median Java RSS | 116.80 MiB |
| Minimum settled `MemAvailable` | 55.04 MiB |
| External HTTP p95 | 7.39 ms |
| Successful requests | 1,500 / 1,500 |
| Workload swap-in / swap-out | 0.20 / 0.05 MiB |

Small workload paging and successful operation do not mean the run was swap-free. Startup includes schema creation and fixture loading. The full [Jdbi results](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/JDBI3-RESULTS.md) include acceptance checks, code/dependency measurements, environment details, and limitations. The [archived measured run](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/results/run-20261008T235523Z-javalin-jdbi3/analysis.json) and [preparation checks](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/checks/jdbi3/README.md) are preserved in the public experiment package.

For historical context, the single Jdbi run reached readiness 1.67 seconds later and used 6.41 MiB more workload RSS than the original JDBC implementation. That comparison also includes application restructuring, so it does not estimate Jdbi's intrinsic overhead. See [JDBI3-RESULTS.md](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/JDBI3-RESULTS.md) for the detailed JDBC comparison; this article's primary comparison is MyBatis, jOOQ, and Jdbi.

## MyBatis Core implementation

The MyBatis variant uses MyBatis Core 3.5.19, an annotated mapper interface with visible SQL text blocks, an explicitly built `SqlSessionFactory`, and repository-owned session lifecycles. Its controller, repository interface, records, routes, H2/Hikari configuration, and portable error responses match the Jdbi application. Its first-level local cache is scoped to statements. Three-row writes use `ExecutorType.BATCH`, followed by an explicit flush and commit; preparation checks verified rollback when a later row conflicts.

## jOOQ Open Source Edition implementation

The jOOQ Open Source Edition 3.21.9 application uses `QuoteController → QuoteRepository → JooqQuoteRepository`, a Hikari datasource, an H2 `DSLContext`, and generated `quotes` table and field types. The repository builds its lookups and inserts with jOOQ DSL expressions and maps results to the unchanged plain Java records. Request batches use a transaction-scoped DSL context and `Batch.execute()`; preparation confirmed rollback when a later row conflicts. A later correction also made fixture loading transactional and passed a separate host-side rollback/recovery check. That correction was not in the original VM run. Schema generation runs on the host from the same DDL resource used at startup, with generated classes separate from handwritten source.

## Runtime comparison

Each measured artifact completed one five-minute workload with 1,500 successful requests and the same final database state. These are three individual runs and do not establish a stable library ranking.

| Measurement | Jdbi Core 3.55.0 | MyBatis Core 3.5.19 | jOOQ OSE 3.21.9, original artifact |
|---|---:|---:|---:|
| Readiness, including schema and fixture setup | 4.13 s | 3.59 s | 4.44 s |
| Idle median Java RSS | 101.55 MiB | 94.85 MiB | 107.32 MiB |
| Workload median Java RSS | 112.83 MiB | 110.55 MiB | 112.19 MiB |
| Workload peak Java RSS | 116.78 MiB | 115.39 MiB | 116.93 MiB |
| Recovery median Java RSS | 116.80 MiB | 114.09 MiB | 116.55 MiB |
| Minimum workload `MemAvailable` | 55.04 MiB | 59.52 MiB | 57.29 MiB |
| Maximum swap used during application phases | 17.20 MiB | 15.61 MiB | 70.71 MiB |
| Workload swap-in / swap-out | 0.20 / 0.05 MiB | 0.12 / 0.00 MiB | 19.11 / 31.19 MiB |
| Workload guest busy CPU / Java CPU | 3.42% / 2.67% | 3.81% / 3.05% | 3.87% / 3.12% |
| Aggregate HTTP p95 | 7.39 ms | 8.23 ms | 9.34 ms |
| Successful workload requests | 1,500 / 1,500 | 1,500 / 1,500 | 1,500 / 1,500 |
| Final database state | 2,070 rows; sequence 689; sum 630374.22 | 2,070 rows; sequence 689; sum 630374.22 | 2,070 rows; sequence 689; sum 630374.22 |

MyBatis' first workload minute had a 17.22 ms p95; its next four minute p95 values ranged from 4.44 to 7.04 ms. This is one five-minute run and should not be read as a stable latency distribution. The detailed [MyBatis analysis](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/results/run-20261009T011153Z-javalin-mybatis/analysis.json) contains phase samples and route-level values; the [Jdbi analysis](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/results/run-20261008T235523Z-javalin-jdbi3/analysis.json) remains unchanged.

Jdbi and MyBatis had no workload headroom dips and no seconds above the harness's 1 MiB/s paging threshold. jOOQ had no recorded headroom dips; its minimum workload `MemAvailable` was 57.29 MiB. jOOQ swapped in 19.11 MiB and out 31.19 MiB during workload, and its maximum swap occupancy across application phases was 70.71 MiB. About five seconds crossed the paging-rate threshold. Its startup phase separately recorded 14.43 MiB swapped in and 42.44 MiB swapped out, reaching 40.28 MiB occupancy; idle occupancy peaked at 40.76 MiB. In the first 25 seconds of workload, swap use rose to 70.71 MiB, with most swap-out activity in that interval. The first workload minute had a 14.37 ms HTTP p95, versus 5.73–6.81 ms in minutes two through five. This time alignment does not show that paging caused the latency; the run has no independent control for that explanation. MyBatis startup swapped in 4.91 MiB and out 15.44 MiB, with 15.61 MiB maximum occupancy. All three guests had 214.89 MiB `MemTotal`, not a full 256 MiB available to applications.

The [jOOQ analysis](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/results/run-20261009T015612Z-javalin-jooq/analysis.json) includes phase samples, minute-level latency and RSS, and CPU details. The [MyBatis analysis](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/results/run-20261009T011153Z-javalin-mybatis/analysis.json) and [Jdbi analysis](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/results/run-20261008T235523Z-javalin-jdbi3/analysis.json) remain individually preserved. No runs were averaged.

**Measurement provenance note:** The jOOQ measurements and the 280-line / 19,188,345-byte figures describe the original implementation used in the archived run. A subsequent correction made fixture initialization transactional and passed a separate host-side rollback and recovery check. The corrected implementation has not been VM-measured; the recorded readiness and resource figures belong to the original build. See the [correction record](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/jooq-correction.md).

## Dependency and application footprint

The jOOQ shaded application JAR is 19,188,345 bytes (SHA-256 `4ef0e678f3ad256abf6e51a27f212f20d60cafa432206c95dbebb5031d217fb8`). Its additional runtime dependency set is jOOQ 3.21.9 (5,445,966 bytes), `r2dbc-spi` 1.0.0.RELEASE (67,645 bytes), and `reactive-streams` 1.0.3 (11,369 bytes). The latter two arrive transitively; the application uses JDBC. Code generation uses `jooq-codegen-maven` 3.21.9, its `jooq-codegen` and `jooq-meta` modules, and H2 2.4.240 in the Maven plugin realm, outside the measured application classpath. See the [resolved runtime dependency tree](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/evidence/jooq-release-002/dependencies.txt), [build-only artifact record](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/evidence/jooq-release-002/build-only-artifacts.json), [dependency verification](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/evidence/jooq-release-002/dependency-verification.json), and [code-cost record](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/evidence/jooq-release-002/code-cost.json) for sizes and hashes.

## How much application code does each approach require?

Code size is a first-class measurement alongside RSS and startup. The existing handwritten Java counts use the same method: count nonblank, noncomment physical Java lines across application startup, repository, mapper, domain records, controller, error handling, and wiring. The identical 83-line StatLite adapter is excluded from the primary comparison and recorded separately. These are counts, not maintainability scores.

| Application code in measured artifacts | Jdbi | MyBatis | jOOQ, original artifact |
|---|---:|---:|---:|
| Handwritten Java lines, excluding shared StatLite adapter | 207 | 358 | 280* |
| Unchanged StatLite adapter Java lines, reported separately | 83 | 83 | 83 |
| Generated Java files / generated Java lines | 0 / 0 | 0 / 0 | 6 / 224 |
| Compiled generated-class footprint | 0 bytes | 0 bytes | 14,695 bytes |
| Shaded JAR size | 14,818,339 bytes | 15,479,070 bytes | 19,188,345 bytes |

\* The jOOQ value is for the measured pre-correction artifact. Current source has 293 handwritten application lines under the same counting method after adding atomic fixture loading; its rebuilt shaded JAR is 19,188,465 bytes. Neither corrected-build figure has VM measurement provenance.

The identical contract, controller, validation, record types, and portable error class account for 72 handwritten Java lines in each variant. Jdbi then has a 30-line application entry point and a 105-line repository. MyBatis has a 52-line entry point, 151-line repository, and 83-line annotated mapper. In the measured jOOQ artifact, the entry point had 45 lines and the DSL repository had 163. The jOOQ generator emitted six Java files and 224 nonblank, noncomment lines; the compiled generated classes total 14,695 bytes. Generated code is shown separately and is not added to handwritten LOC. The corrected repository currently has 176 lines, reflecting the additional atomic fixture-load path.

Jdbi expresses queries in repository SQL and delegates handle, mapping, and batch work to Jdbi APIs. MyBatis puts SQL text and result annotations in its mapper, while repository code owns `SqlSession` setup, flush/commit/rollback, and lifecycle. jOOQ expresses query structure and typed columns in Java DSL; the generated table class supplies compiler-checked fields, while handwritten repository code still owns binding, record-to-domain mapping, initialization, transactions, and error translation. Code count is evidence about where responsibilities live, not a maintainability verdict.

## Where the application code lives

The comparison below uses the [Jdbi repository](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/javalin-jdbi3/src/main/java/lab/JdbiQuoteRepository.java), [MyBatis repository](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/javalin-mybatis/src/main/java/lab/MyBatisQuoteRepository.java) and [mapper](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/javalin-mybatis/src/main/java/lab/QuoteMapper.java), and [original measured jOOQ repository](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/historical/jooq-release-002/JooqQuoteRepository.java). The [corrected jOOQ repository](https://github.com/PVRLabs/experiments/blob/main/javalin/sql-persistence-256mb/javalin-jooq/src/main/java/lab/JooqQuoteRepository.java) adds atomic fixture initialization and was tested separately.

| Responsibility | Jdbi Core | MyBatis Core | jOOQ Open Source Edition |
|---|---|---|---|
| SQL organization | SQL text blocks are constants in the repository; query execution is beside the SQL. | SQL text blocks and mapper methods live in an annotated interface; repository code calls mapper methods. | Query structure is expressed as DSL calls in the repository; no raw query strings for application reads/writes. |
| Parameter binding and mapping | Named binds (`:symbol`, `:limit`) and registered `Quote` row mapper. | `@Param` names pair with `#{...}` binds; `@ConstructorArgs` declares record construction. | Generated fields provide Java types for table columns; fetched jOOQ records are mapped to the plain `Quote` record in a small method. |
| Transactions and resources | `withHandle`/`useHandle` scopes handles; `useTransaction` scopes fixture and request batches; Jdbi closes its handle resources. | Repository explicitly opens/closes `SqlSession`; batch writes flush, commit, and roll back on failure. | Hikari owns connections; `DSLContext.transaction` supplies a transaction-scoped context for request batches and, in corrected source, fixture loading. |
| Error translation | Walks causes to SQLState and maps class 23 to portable conflict. | Same portable SQLState rule; session rollback failures are attached as suppressed errors. | Same portable SQLState rule; translation remains inside the repository. |
| Schema checks and generation | DDL runs at initialization; SQL names and result shape are not checked against a generated Java schema. | Annotated SQL is explicit, but statement names/columns are resolved by MyBatis at runtime; no generated schema code. | Generated `QUOTES` fields make table/column references Java-compiler checked; code generation adds a host-side Maven step. Database semantics still require runtime tests. |

For example, Jdbi binds a named query with `createQuery(SELECT).bind("symbol", symbol)`. MyBatis uses `@Select(LATEST_OR_HISTORY)` and `@Param` on mapper arguments. jOOQ expresses the corresponding predicate with `where(QUOTES.SYMBOL.eq(symbol))`, then adds ordering and limits through the DSL. This shows where each implementation places SQL structure; it does not establish a general readability or maintainability preference.

All three applications keep explicit constructor wiring and the same controller/repository boundary. The application entry points initialize Hikari and monitoring, construct the persistence object, then pass the repository to the controller. The jOOQ Maven plugin additionally prepares the H2 schema and generates six schema-model Java files at `generate-sources`; MyBatis adds mapper annotations, and Jdbi has no generated schema sources. Maven/XML configuration is build complexity, not Java LOC.

## Code generation and build complexity

The Maven `generate-sources` phase runs `org.jooq:jooq-codegen-maven:3.21.9` against an in-memory H2 2.4.240 database initialized from `src/main/resources/schema.sql`. It generates only the `QUOTES` schema model under `target/generated-sources/jooq`; the input and six output source hashes are listed in the preparation code-cost record and the schema hash is in the input manifest. `mvn -f javalin/sql-persistence-256mb/javalin-jooq/pom.xml clean package` regenerates the model before compiling and shading the application. After a schema change, update the DDL resource, regenerate, inspect generated types, and rerun functional preparation. The generator runs on the host and its plugin dependencies do not enter the shaded runtime JAR.

## Database compatibility and licensing

jOOQ's Open Source Edition lists H2 and open-source databases including PostgreSQL, MySQL, MariaDB, and SQLite. Its published policy targets the latest database versions; commercial editions offer a broader historical-version matrix. The current jOOQ edition page lists Oracle and SQL Server support outside the Open Source Edition, with Oracle Express and SQL Server Express listed separately in the Express tier. This database-portability and licensing detail is separate from the runtime measurements. A JDBC driver may connect to a database without that implying official jOOQ dialect support. See jOOQ's [edition and database list](https://www.jooq.org/download/), [version support matrix](https://www.jooq.org/download/support-matrix), and [licensing information](https://www.jooq.org/legal/licensing) for the current policy. The generated DSL and schema model also provide typed query construction and compiler-visible table/column names; these are implementation characteristics, not performance conclusions.

## Limitations and conclusion

These runs report observed values for three complete applications under one workload and one VM configuration. Each candidate has one run; the jOOQ measurement is for the original artifact, while the corrected fixture-initialization source remains unmeasured. The table and source analysis describe the observed outcomes and implementation responsibilities. Differences include application structure, startup work, packaging, and runtime behavior; they are not isolated measurements of intrinsic library overhead. The workload is small and deterministic, and the guest is a VPS-sized local VM rather than a provider VPS. The public experiment package preserves the original measured source and the separately tested fixture correction.

See the [original Javalin vs. Spring Boot experiment](https://pvrlabs.xyz/java-performance/experiments/javalin-vs-spring-boot-256mb.html).
