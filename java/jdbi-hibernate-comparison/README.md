# Jdbi and Hibernate persistence comparison

This experiment compares Jdbi with direct Hibernate using Stargazer, a small repository-monitoring demo application, in the same [CoilBase](https://github.com/PVRLabs/coilbase), [Jex](https://github.com/avaje/avaje-jex) and [JTE](https://github.com/casid/jte) infrastructure. A Spring Boot, Spring Data JPA and Hibernate application provides a whole-stack reference. It asks how the complete applications behave on a small Linux VM; it does not measure the isolated memory cost of a library.

The author also develops CoilBase. The Hibernate application retains transitive Jdbi libraries through CoilBase, but its packaged lifecycle checks confirm that no Jdbi repository context is initialized. See [its disclosure](coilbase-hibernate/README.md).

## Results

The table gives the range of two accepted run medians for application-process memory during the extended mixed phase. Embedded H2 is included in RSS and PSS. Startup and dashboard latency ranges are individual runs; each mixed phase recorded 300 dashboard requests.

| Application | Startup (s) | RSS / PSS (MiB) | Dashboard p50 / p95 (ms) | Sum of deployed JARs (MiB) |
| --- | ---: | ---: | ---: | ---: |
| CoilBase + Jdbi | 1.05–1.16 | 95.2–96.4 / 92.8–94.0 | 4.4 / 7.7–7.9 | 6.8 |
| CoilBase + direct Hibernate | 2.31–2.32 | 151.8–153.6 / 149.3–151.2 | 7.9 / 15.1–15.6 | 27.7 |
| Spring Boot + Spring Data JPA | 6.80–7.10 | 235.7–235.8 / 233.4–233.5 | 12.3–12.4 / 29.5–31.1 | 58.2 |

JAR sizes sum the application and dependency JAR files, excluding other deployment files. They are not compressed bundles or complete deployment sizes. RSS ranges are individual run medians, not confidence intervals.

The second extended Hibernate attempt was rejected after the guest OOM killer killed Java during mixed load. The firmware refresh timer started shortly beforehand; timing is a correlation, not proof of cause. The accepted replacement used the same artifact, flags and workload after automatic update and firmware refresh timers were disabled and the firmware service stopped. Its background environment therefore differs from earlier runs; do not interpret small between-run differences as meaningful. The rejected attempt's selected evidence is retained in [results/rejected](results/rejected/02-coilbase-hibernate-oom/).

This is a paced workload on one VM, not a maximum throughput test. Two runs per variant and the 30 refreshes per mixed phase constrain tail latency interpretation. Spring's original-mode monitoring requests differ from the Jex variants. The Spring reference also differs in infrastructure and template engine; its difference from direct Hibernate cannot be attributed to Spring Data JPA alone. Further workload-specific tuning may change results.

## Evidence and checks

The curated [results](results/) contain per-second samples, requests, offline database snapshots and selected metadata for twelve accepted runs, with the rejected attempt separate. Run:

```sh
python3 check.py
python3 scripts/analyze.py results/original
python3 scripts/analyze.py results/extended
```

`check.py` recalculates phase summaries and verifies the accepted-run count, sample fields, no process swap, HTTP status, SQL statistics, OOM counters, collector status, and offline committed state including timestamp windows. It checks retained evidence; it does not rerun applications or independently recreate the original kernel logs. Metadata has been reduced to measurement and validation fields; logs, raw databases, absolute paths and host-specific captures are not included.

## Method and reproduction

The measured source revision was `912c7bdf8ef6009d2dba3679d3ddafa34646e5bb` in the original experiment workspace. Application sources and the benchmark runner are included here. The public build script accepts `MAVEN` (default `mvn`); the preparation smoke script uses the extracted Spring layout and reports early startup errors, and the bundle script includes the public README. These preparation changes were made after measurement and do not alter the measured application or runner.

The Linux guest was Ubuntu 24.04 x86-64 on QEMU/KVM, one vCPU, 512 MiB allocated (452 MiB reported by the guest), no swap, and Temurin 25.0.5. The pinned image configuration is [vm.yaml](vm.yaml). H2 2.4.240 is file-backed and embedded; HikariCP uses maximum four and minimum idle one. Every run starts with a fresh database and identical fixture responses. The shared JVM flags are:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC -XX:TieredStopAtLevel=1
-XX:ReservedCodeCacheSize=32m -XX:+UseCompactObjectHeaders
```

Build on a machine with JDK 25, Maven and Python 3, outside the small guest:

```sh
bash scripts/build.sh
python3 scripts/smoke.py
python3 scripts/bundle.py /tmp/stargazer-bundle
```

Deploy the bundle to a fresh Linux VM directory, verify its files and JDK, confirm one CPU and no swap, and run a short preparation check before measurement. The smoke command above operates on the extracted layout; it uses temporary databases. The bundle preserves application and dependency JARs, fixtures and runner. The original measurement used verified deployment and captured VM/host environment before measurement.

From the deployed bundle in the guest, use new output paths:

```sh
python3 scripts/benchmark.py --mode original --order spring-jpa coilbase-jdbi coilbase-hibernate --runs 2 --output /tmp/stargazer-original --execute
python3 scripts/benchmark.py --mode extended --order coilbase-hibernate coilbase-jdbi spring-jpa --runs 2 --output /tmp/stargazer-extended --execute
python3 scripts/analyze.py /tmp/stargazer-original
python3 scripts/analyze.py /tmp/stargazer-extended
```

The second repetition reverses each specified order. Original mode has a 30-second warmup and 60-second sample, with four requests every five seconds; Jex diagnostics replace Spring's metrics and Prometheus requests. Extended mode has 60 seconds idle, 120 seconds warmup, 300 seconds mixed and 60 seconds recovery; dashboard and readiness requests are paced at one per second, with fixture advances and refreshes every ten ticks. Automatic polling is deferred to keep writes under harness control. Filesystem cache was warm; startup is not a cold-boot measurement.

The runner collects RSS, PSS, process swap, available memory, request timings, jstat, H2 SQL statistics and guest OOM counters. Acceptance requires all phases, no HTTP errors or guest OOM counter increase, samples and SQL statistics, and an offline database snapshot matching each fixture generation and refresh timestamp window. Cumulative SQL counts include bootstrap, diagnostics and commits and are not network roundtrips. See [benchmark.py](scripts/benchmark.py) for the exact collection and acceptance logic.
