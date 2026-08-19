# Spring Boot low-memory experiment

This experiment tests whether useful monitoring fits beside a functioning,
constrained Spring Boot application.

## What was tested

- Spring Boot 3.5.5 with Java 21
- An H2/JPA GitHub-stars application
- StatLite monitoring the Spring application and itself
- Ubuntu 24.04 on 1 vCPU
- A 5 GB virtual disk

The demo application is preserved in [`springboot-stars/`](springboot-stars/).
It tracks GitHub star counts and exposes a dashboard and Spring Boot Actuator
endpoints. See its README for build and run instructions.

## Why JPA/Hibernate?

This application could have used a much lighter persistence layer. We
intentionally used a typical Spring Boot stack with Spring Data JPA, Hibernate,
H2, embedded Tomcat, Actuator, scheduled work, and outbound HTTP so the
experiment would represent a small real-world application rather than a demo
optimized specifically to minimize memory usage.

## Practical JVM profile

The practical comparison used:

```text
-Xms16m -Xmx64m -Xss256k -XX:+UseSerialGC
```

## Configuration progression

The configurations were kept separate:

| Configuration | Result |
|---|---|
| 256 MB RAM, no swap | Spring entered an OOM/restart loop before a stable baseline. |
| 256 MB RAM, 256 MB swap, simple JVM | Spring restarted once during the hour and swap was effectively full. |
| 256 MB RAM, 256 MB swap, aggressive JVM limits | Startup failed with a Metaspace allocation error. |
| 512 MB RAM, no swap, simple JVM | The hour completed, but Spring had one OOM restart. |
| **512 MB RAM, 256 MB swap, simple JVM** | **Clean 60-minute result described below.** |

## Successful practical result

The useful low-end configuration was:

`512 MB configured RAM / 256 MB swap / simple JVM`

The preserved run observed:

- The VM exposed approximately 452 MiB usable RAM.
- Spring Boot startup took 14 seconds.
- Spring Boot restarts during the 60-minute observation: 0.
- StatLite restarts: 0.
- All 72 bounded HTTP checks returned 200.
- Final Spring RSS: approximately 167 MiB.
- Final StatLite RSS: approximately 12 MiB.
- Final swap use: approximately 160 MiB of 256 MiB.
- Approximately 140 MiB RAM remained available at the final checkpoint.
- The 60-minute window recorded 240 StatLite polls, 120 per target, and
  2,640 metric samples.

StatLite remained a small part of the footprint while staying healthy and
continuing to monitor both targets. This experiment specifically tested
whether useful observability still fits alongside a constrained Spring Boot
application, rather than measuring an empty JVM.

## Conclusion

256 MB RAM is an extreme stretch configuration for this application. 512 MB
RAM plus a modest swapfile is the useful low-end deployment result demonstrated
by this experiment.

The detailed checkpoints and execution diary remain in the private workspace;
this repository contains the reproducible demo and the concise public summary.
