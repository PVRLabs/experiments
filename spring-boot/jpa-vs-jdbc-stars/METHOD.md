# Method and provenance

## Variants

- `jpa/` is the conventional Stars app adapted from an earlier PVRLabs
  experiment. It uses Spring Data JPA, Hibernate, and a richer project/history
  model with star, fork, watcher, and push fields.
- `jdbc/` uses Spring MVC, `JdbcTemplate`, and a single `star_observation` table.
  Every successful poll stores a timestamp and star count, including unchanged
  values. It retains the Star Pulse visual style.
- Both use Spring Boot 4.1.1, H2 file storage, Thymeleaf, Actuator, and the
  Micrometer Prometheus registry. Both were built from source revision
  `20573688f189b8bbd27fe59bdf9a0ff2385f7477` in the private experiment
  workspace, plus the JDBC source included here. The raw reports contain the
  exact built JAR hashes.

The original Stars app had a five minute scheduler. The measurement overrides
both variants to a ten minute interval and initial delay. The JDBC app's normal
default is ten minutes. Scheduler threads exist in both measured processes.
Both memory runs used executable fat JARs. The JDBC deployment instructions
prefer an extracted layout, which was evaluated separately in the earlier
[Stars layout experiment](../extracted-layout/).

## Machine and workload

The two paired runs were made on one macOS x86_64 machine with Temurin JDK
25.0.4.1. The complete JVM profile for both apps was:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

The local fixture returns fixed counts for `PVRLabs/statlite` (142),
`PVRLabs/aibadger` (87), and `scriptella/scriptella-etl` (63). The harness
starts each app with a fresh H2 file, requests the dashboard until ready,
performs one manual refresh, then requests the dashboard plus Actuator health,
metrics, and Prometheus endpoints every five seconds. It warms for 30 seconds,
then samples whole-process RSS with `ps -o rss=` every five seconds for one
minute. It checks the dashboard values and the monitoring endpoints. Both
orders were run to expose order effects.

The fixture response JSON files are in `fixture/responses/`. The checked-in
reports in `results/` retain the twelve RSS samples per variant and timing;
the adjacent fixture request logs show the three GitHub responses for each app.
They are raw observations; MiB values in the summary divide KiB by 1024.
The `source_revision` and `fixture` fields in these public copies identify the
source and relative fixture path without local user directory names.

## What the result supports

The two runs found a 90.4–91.2 MiB lower median RSS for the JDBC variant,
or 38.1–38.5% of the JPA baseline. Startup to the first successful dashboard
response was 8.1–8.8 seconds for JPA and 3.9–4.2 seconds for JDBC. Both apps
still grew by about 1–2 MiB during the sample minute, so the run shows a warm
runtime comparison rather than a final memory plateau. One host and two runs
do not establish a general Spring Boot memory guarantee.

The difference is the complete application change. The JPA baseline stores
more fields and has more repository and service code. Actuator and Prometheus
were equalized because monitoring with StatLite is part of the intended use.
An isolated Hibernate cost would require variants with identical data model,
UI, and all other dependencies.

An exact StatLite `v0.5.0` binary built from tag
`48827b2d5d5694786605c6d820e507c5afdf229b` collected the JDBC app with
`collection_status: ok`, application health `UP`, and a JVM runtime memory
point. The response is in `results/statlite-0.5.0-check.json`.
