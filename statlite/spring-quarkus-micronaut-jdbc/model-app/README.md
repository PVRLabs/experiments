# Market Replay model application

This small application gives future Java, framework, and runtime experiments a
repeatable synchronization workload. It intentionally resembles the scheduled
HTTP-to-database update pattern used by applications such as FinRecord: each
successful poll moves a small JSON response through parsing and persistence,
then makes the stored history available to an API and browser chart.

## Architecture

`fixture/` is a Python standard-library HTTP server over a checked-in CSV.
Three Maven applications implement the same contract:

| Directory | Framework baseline | Web / JDBC stack | Health | Prometheus |
| --- | --- | --- | --- | --- |
| `spring-app/` | Spring Boot 4.1.1 | Spring MVC / JdbcClient / HikariCP | `/actuator/health` | `/actuator/prometheus` |
| `quarkus-app/` | Quarkus 3.40.1 | Quarkus REST / JDBC / Agroal | `/q/health` | `/q/metrics` |
| `micronaut-app/` | Micronaut Platform 5.2.1 (Core 5.2.11) | Netty / JDBC / HikariCP | `/health` | `/prometheus` |

The new ports use the latest stable platform releases listed by Maven Central
on 2026-10-01: [Quarkus metadata](https://repo.maven.apache.org/maven2/io/quarkus/platform/quarkus-bom/maven-metadata.xml)
and [Micronaut metadata](https://repo.maven.apache.org/maven2/io/micronaut/platform/micronaut-parent/maven-metadata.xml).
Quarkus 4 beta is excluded. Framework versions are pinned; builds do not use
floating `LATEST` versions. Micronaut Platform and Core have separate versions.
Micronaut 5 uses Jackson 3 through the framework `JsonMapper`; Spring and
Quarkus use Jackson 2. Record these stack differences in experiment results.

All three use Java 25, H2 2.4.240, and explicitly configured pools with one idle
connection and a maximum of four. They use no ORM. The ports use prepared SQL
and local JDBC transactions for atomic writes; Spring uses its transaction
manager. SQL, schema, and browser resources are equivalent. Chart.js is vendored under the static resources, so the page works
without a CDN or internet access.

The fixture data is 390 one-minute closing prices per symbol for AAPL, GOOG, and
NVDA on 2026-09-30, 09:30–15:59 America/New_York. Yahoo Finance's chart data
endpoint was the acquisition source; see [fixture/README.md](fixture/README.md).
The runtime reads only the local CSV. At fixture startup, monotonic elapsed time
starts at sample 0 (09:30). Each sample lasts 60 seconds by default. Reads do
not advance the replay, and after sample 389 the fixture returns to sample 0
with its cycle counter incremented. `--step-seconds` or
`FIXTURE_STEP_SECONDS` can shorten the interval for a local smoke run.

## Application contract

All three implementations preserve this behavior:

- one local deterministic fixture, three symbols, and one simulated trading day;
- a one-minute replay interval, stable repeated reads, and looping after 390 samples;
- an application poll approximately once per minute, initially on startup;
- each successful poll stores exactly three observations with local fetch time,
  cycle, sample index, market time, symbol, and price;
- a local file-backed database, `GET /api/quotes/latest`, and bounded
  `GET /api/quotes/history` (up to 390 observations per symbol);
- one browser page with current prices and an updating history chart;
- normal framework health and metrics endpoints, including Prometheus metrics.

The REST payload is a JSON array of observation records. History is ordered by
insertion, oldest to newest within the retained window. A failed fixture poll is
logged and the next scheduled poll proceeds normally. Polling uses a fixed delay
of 60 seconds after completion, rather than a fixed wall-clock rate. The HTTP
fetch and payload validation happen before the database transaction; each
three-row batch is committed atomically. Invalid replay metadata, duplicate or
unknown symbols, and prices outside the positive `DECIMAL(12,4)` contract are
rejected before any rows are written.

History responses are bounded, but stored rows are not pruned. Experiments must
use fresh database files and equal run durations. The browser reports the last
stored fetch time so a successful API refresh does not imply a fresh fixture poll.

## Ports and configuration

| Component | Default | Configuration |
|---|---:|---|
| Python fixture | `127.0.0.1:8090` | `--host`, `--port`, `FIXTURE_HOST`, `FIXTURE_PORT` |
| Application (all three) | port `8080` | `SERVER_PORT` |
| Fixture URL | `http://127.0.0.1:8090/quotes` | `MARKET_FIXTURE_URL` |
| Replay step | 60 seconds | `--step-seconds` / `FIXTURE_STEP_SECONDS` |
| App poll | 60 seconds | `MARKET_POLL_INTERVAL_MS` |
| Initial poll delay | 0 milliseconds | `MARKET_POLL_INITIAL_DELAY_MS` |
| H2 file | `./data/market-replay` | `MARKET_DB_URL` |

Spring additionally exposes `/actuator/info` and `/actuator/metrics`. See the
framework table for each app's health and scrape paths. Database paths are
relative to each app's working directory. Run one app at a time on port 8080,
or assign separate ports and database files for an optional combined run.
Micronaut exposes aggregate JDBC health details for the isolated experiment.

All three intentionally use the same JDK single-thread `ScheduledExecutorService`
with `scheduleWithFixedDelay`, one non-daemon thread named `market-poll`, and
identical initial-delay/interval handling. Shutdown interrupts the executor and
waits up to five seconds for termination. Framework scheduler APIs and semantics
are not sufficiently uniform for scheduling to be a useful part of this
experiment; many applications also use their own executors. Scheduling is
normalized infrastructure and is not being benchmarked.

Framework lifecycle hooks differ naturally and only start/stop the executor;
Quarkus and Micronaut also initialize their repositories before starting it.
Spring initializes its schema through its existing JDBC configuration.
Readiness remains externally defined as application health plus the first
successfully persisted batch, not the framework lifecycle event that starts
polling. The comparison still measures the complete framework application stack
around the common workload. Basic application components, dependency injection,
HTTP handlers, and JDBC integration translate more directly across these
frameworks than their scheduling APIs do.

API JDBC reads execute off the Netty/event-loop threads in both
ports. All apps use the JDK HTTP client with 3-second connect and 5-second
request timeouts.

## Run locally

In one terminal, start the fixture:

```sh
cd market-replay/model-app/fixture
python3 server.py
```

In another terminal, start Spring Boot (Java 25 and `mvn-lite` are used by the
current repository's Spring experiments):

```sh
cd market-replay/model-app/spring-app
mvn-lite spring-boot:run
```

The app performs its first poll immediately. Open <http://localhost:8080>.
Useful endpoints are:

```sh
curl http://127.0.0.1:8080/api/quotes/latest
curl http://127.0.0.1:8080/api/quotes/history
curl http://127.0.0.1:8080/actuator/health
curl http://127.0.0.1:8080/actuator/prometheus
```

For an accelerated smoke run, use `python3 server.py --step-seconds 2` and
`MARKET_POLL_INTERVAL_MS=2000 mvn-lite spring-boot:run`.

### Run either new port

Keep the fixture running, then build and launch one app:

```sh
cd market-replay/model-app/quarkus-app
mvn-lite package
java -jar target/quarkus-app/quarkus-run.jar
```

```sh
cd market-replay/model-app/micronaut-app
mvn-lite package
java -jar target/market-replay-micronaut-0.1.0-SNAPSHOT.jar
```

Both serve <http://localhost:8080> and the same `/api/quotes/latest` and
`/api/quotes/history` routes. Quarkus deployment requires the entire
`target/quarkus-app/` directory. Micronaut packages a runnable shaded JAR.
For an accelerated smoke check, launch the fixture with `--step-seconds 2`
and prefix either `java` command with `MARKET_POLL_INTERVAL_MS=2000`.

## Validation

Run the fixture tests from this directory, and run `mvn-lite package` in each
application directory to execute Java tests and build the runnable artifacts:

```sh
python3 -m unittest discover -s fixture/tests
mvn-lite -f spring-app/pom.xml package
mvn-lite -f quarkus-app/pom.xml package
mvn-lite -f micronaut-app/pom.xml package
python3 tests/contract.py
```

The Spring application smoke test uses a mocked quote client to exercise JSON
parsing, persistence of three rows per poll, latest/history queries, the page,
local Chart.js asset, health, and Prometheus. A separate fixture/client
integration test starts the real Python fixture and fetches its checked-in
09:30 sample through the real Java HTTP client. Tests use in-memory H2; normal
runs use the file-backed database. The fixture/client integration test needs
Python 3 and permission to bind a loopback port.

The ports have repository tests for rollback of a failed third insert and the
390-per-symbol history limit across replay wrap. `tests/contract.py` starts each
packaged app sequentially with a temporary file-backed database and a
controllable HTTP server serving the real checked-in fixture's sample zero. It
checks startup/repeated polling, JSON fields and prices, exact browser assets,
health/metrics, rejection of malformed batches, HTTP failure/recovery, and
persistence after restart. It requires permission to bind loopback ports. These
accelerated checks are not performance measurements.

To run a subset or inspect monitoring compatibility using a candidate StatLite
binary:

```sh
python3 tests/contract.py --framework quarkus micronaut
python3 tests/contract.py --statlite /absolute/path/to/statlite
```

Spring inspection uses discovery; Quarkus and Micronaut use explicit types.
StatLite is being upgraded locally to target Micronaut 5.x while retaining 4.x
support without collector code changes. Inspection validates endpoints;
sustained collector continuity, restart
normalization, and Linux process measurements remain experiment rehearsal work.

## Spring baseline

The initial implementation uses Java 25 and Spring Boot 4.1.1, matching the
repository's current Spring experiment convention. See [Spring Boot 4.1.1
release information](https://spring.io/blog/2026/08/20/spring-boot-4-1-1-available-now/).
