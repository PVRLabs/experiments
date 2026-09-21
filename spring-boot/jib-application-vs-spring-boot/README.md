# Spring Boot extracted layout vs Jib exploded layout

This small follow-up compares two filesystem layouts for the same Spring Boot
application:

- Spring Boot extracted layout: `app.jar + lib/*.jar`
- Jib-style exploded layout: `classes/ + resources/ + libs/*.jar`

The question is whether removing the application JAR adds a measurable startup
or first-request benefit after dependencies are already outside the nested
executable JAR.

## Result

On this short run, the two layouts were effectively tied for startup. Jib's
median first request was somewhat slower, while RSS and process swap were
similar. The result does not show a clear benefit from removing the application
JAR for this application and environment.

See [`RESULTS.md`](RESULTS.md) for the run table and [`results/measurements.csv`](results/measurements.csv)
for the curated per-run data.

## Setup and protocol

The same Spring Boot 4.1.1 application, OpenJDK 25.0.4, JVM profile, database
fixture, and loopback request validation were used for both layouts. The test
ran on the existing Alpine `spring-boot-layout-256` VM with one vCPU, 256 MiB
RAM, and 512 MiB swap.

There were three fresh starts per layout, in the fixed order `extracted, jib`
for each round. Each start recorded Spring startup, external startup, one first
request, two follow-up requests, RSS, process swap, and 30 seconds of survival.
The Jib artifact was built with Jib Gradle plugin 3.4.5 and launched from its
loose `classes/`, `resources/`, and `libs/` directories. This public package
contains curated measurements; the full harness and raw run archive remain in
the private experiment record.

Related page: [Spring Boot extracted layout vs Jib exploded layout](https://pvrlabs.xyz/java-performance/experiments/spring-boot-jib-layout.html).
