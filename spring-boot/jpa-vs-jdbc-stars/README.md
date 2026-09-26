# Spring Boot Stars: JPA versus JDBC

This experiment asks how much memory a small Spring Boot application can save
by using Spring MVC and `JdbcTemplate` in place of the conventional Spring Data
JPA and Hibernate stack. Both variants use Spring Boot 4.1.1, JDK 25 with compact
object headers, H2, Thymeleaf, Actuator, and Prometheus metrics. They track the
same three public GitHub repositories and expose a Star Pulse style dashboard
and the same monitoring endpoints.

On one macOS host, after a 30 second warmup, the JDBC variant used **about
90–91 MiB less RSS** than the JPA baseline in two reversed-order runs. That was
about **38%** of the baseline RSS. Time from process launch to the first
successful dashboard response was **3.9–4.2 seconds for JDBC**, versus
**8.1–8.8 seconds for JPA**. These observations support choosing Spring JDBC
for small apps where memory and startup matter. The variants also differ in
data model and other application code, so the result is not an isolated
measurement of the Hibernate library alone.

| Run order | JPA median RSS | JDBC median RSS | RSS difference | JPA startup | JDBC startup |
| --- | ---: | ---: | ---: | ---: | ---: |
| [JPA, then JDBC](results/jpa-first.json) | 237.0 MiB | 145.8 MiB | 91.2 MiB | 8.134 s | 4.162 s |
| [JDBC, then JPA](results/jdbc-first.json) | 236.9 MiB | 146.6 MiB | 90.4 MiB | 8.804 s | 3.939 s |

The JSON reports contain every RSS sample, startup timing, JVM flags, host
description, and JAR hashes. [Method and limits](METHOD.md) documents the
workload and provenance.

## Reproduce

Build both variants with JDK 25 and Maven:

```sh
cd jpa && mvn -DskipTests package
cd ../jdbc && mvn -DskipTests package
cd ..
python3 scripts/compare.py
python3 scripts/compare.py --reverse
```

The scripts use only Python's standard library, start a deterministic local
GitHub fixture, create separate H2 files, and stop their processes afterward.
They write new runs under `results/` (ignored by Git).

The [JDBC app](jdbc/) can also run on a Linux host with JDK 25 and its packaged
JAR. It polls every ten minutes, keeps observations in a file-backed H2 database,
and exposes Actuator and Prometheus endpoints for health and application
metrics.
