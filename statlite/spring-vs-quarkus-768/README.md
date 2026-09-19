# Spring Boot vs Quarkus at 768 MiB

This is a follow-up memory-behavior comparison of equivalent Spring Boot and
Quarkus applications under a shared 768 MiB Ubuntu VM budget. It extends the
earlier [Spring Boot vs Quarkus experiment](../spring-vs-quarkus/) without
replacing it.

## Result

In the recorded 10-minute observation, Spring used more resident memory and
accumulated process swap. Quarkus used less resident memory and accumulated no
process swap. Both applications remained healthy, and StatLite monitored all
three targets successfully.

This claim is limited to the measured applications, JVM profile, workload, VM,
and observation described here. It is not a framework-wide performance
ranking.

## Environment

- Ubuntu 24.04 x86_64
- 768 MiB VM memory, 1 vCPU, 256 MiB swap
- Eclipse Temurin 25.0.4.1+1
- Spring Boot 4.1.1
- Quarkus 3.39.4
- StatLite 0.4.2
- Common JVM profile with `-Xmx80m` and SerialGC
- Deterministic loopback GitHub-like fixture

## Method

Spring started first, followed by Quarkus. Each application received one
deliberate request, StatLite then began monitoring, and the paired workload
sent ten requests to each application. RSS, process swap, heap, host pressure,
service state, and StatLite polling were sampled repeatedly through the
10-minute observation.

See [METHOD.md](METHOD.md), [RESULTS.md](RESULTS.md), and the normalized
[checkpoint data](results/checkpoints.csv).

## Evidence

- [Host resources screenshot](screenshots/host-resources.png)
- [Quarkus target screenshot](screenshots/quarkus-target.png)
- [Spring target screenshot](screenshots/spring-target.png)
- [Workload record](results/workload.txt)
- [Final polling summary](results/polling-final.csv)

The private run archive contains additional raw snapshots and closeout data.
Credentials, VM access material, the private SQLite database, and disposable
runtime files are intentionally excluded from this public package.
