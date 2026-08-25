# Spring Boot low-memory experiment

This experiment tests whether useful monitoring fits beside a functioning,
constrained Spring Boot application. It contains two related runs:

1. An Ubuntu 24.04 / Java 21 comparison that established the practical
   512 MB deployment result.
2. A separate Alpine Linux / Java 25 follow-up that tested how far the same
   application could be pushed on a nominal 256 MiB VPS.

These are separate deployment experiments, not a controlled JDK-only
benchmark. The operating system, guest-visible memory, swap, JVM profile, and
service manager differ between them.

See [Experiment details](EXPERIMENT.md) for the method, full comparison, exact
runtime identities, Alpine deployment kit, and selected sanitized observations.

## What was tested

- Spring Boot 3.5.5 with Spring MVC, embedded Tomcat, JPA, Hibernate, H2, and
  Actuator
- A GitHub-stars application with scheduled outbound GitHub polling
- StatLite monitoring the Spring application and itself
- One vCPU and a 5 GB virtual disk
- Ubuntu 24.04 with Java 21 for the original comparison
- Alpine Linux 3.24 with Java 25 for the 256 MiB follow-up

The demo application is preserved in [`springboot-stars/`](springboot-stars/).
It tracks GitHub star counts and exposes a dashboard and Spring Boot Actuator
endpoints. See its README for build and run instructions.

## Results at a glance

| Run | Memory / swap | JVM | Outcome |
|---|---|---|---|
| Ubuntu comparison | 512 MB RAM / 256 MB swap | Java 21, 64 MiB heap | Clean 60-minute run |
| Alpine follow-up | Nominal 256 MiB RAM / 512 MiB swap | Java 25, 80 MiB heap, compact object headers | Completed 60-minute run with limits |

## Practical JVM profiles

The original practical comparison used:

```text
-Xms16m -Xmx64m -Xss256k -XX:+UseSerialGC
```

The Alpine stretch run used:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

## Alpine 256 MiB follow-up

The Alpine guest exposed approximately 216.9 MiB. With 512 MiB of swap, the
Java 25 configuration completed the full one-hour Spring Boot + StatLite
observation:

- no OOM kills or service restarts;
- all 72 bounded HTTP checks returned HTTP 200;
- StatLite polling continued for both targets;
- Spring's scheduled GitHub polling continued after one early EOF/retry;
- final Spring RSS: 87,616 KiB;
- final StatLite RSS: 10,196 KiB;
- final combined RSS: 97,820 KiB; and
- final swap use: 184 MiB of 511 MiB.

The run also recorded a Hikari housekeeper delay of about 2 minutes 13
seconds. The result is therefore viable with limits, not a comfortable
production baseline. The reproducible deployment and observation kit is in
[`alpine-256mb/`](alpine-256mb/).

## Ubuntu practical result

The useful low-end configuration demonstrated by the original comparison was:

`512 MB configured RAM / 256 MB swap / simple JVM`

The preserved run observed approximately 452 MiB usable RAM, 14-second Spring
Boot startup, zero Spring and StatLite restarts, 72 of 72 bounded HTTP checks
returning 200, final Spring RSS of approximately 167 MiB, final StatLite RSS
of approximately 12 MiB, approximately 160 MiB of swap in use, and
approximately 140 MiB RAM available at the final checkpoint.

## Conclusion

256 MB RAM is an extreme stretch configuration for this application. Java 25,
Alpine, swap, and a constrained JVM profile allowed the nominal 256 MiB run to
complete a controlled hour, but the high swap use and scheduling delay matter.
For a real deployment, 512 MB RAM plus a modest swapfile remains the sensible
starting point.

StatLite was not the dominant memory consumer in either run. The experiment
tested whether useful observability fits alongside a constrained, functioning
Spring Boot application rather than measuring an empty JVM.

The detailed private checkpoints and execution diaries are not mirrored here;
this repository contains the reproducible demo, deployment kit, and curated
public summary.
