# Experiment details

This document supplements the concise [README](README.md) with the method,
configuration-by-configuration results, exact Alpine runtime identity, and
selected sanitized observations. It intentionally does not reproduce the
complete private execution journal or service logs.

## Scope

The workload was a small but functioning Spring Boot application rather than
an empty JVM. It used Spring Boot 3.5.5, Spring MVC, embedded Tomcat, Spring
Data JPA, Hibernate, file-backed H2, Actuator, scheduled GitHub polling, and
outbound HTTP. StatLite monitored the Spring application and its own metrics.

The application source is preserved in [`springboot-stars/`](springboot-stars/).
The public repository contains two related deployment experiments. They must
be read as separate tracks, not as a controlled comparison of one JVM flag:

- Ubuntu 24.04 / Java 21 / systemd, originally used to establish the practical
  low-end deployment result.
- Alpine Linux 3.24 / Java 25 / OpenRC, used as a separate 256 MiB stretch
  follow-up for the article.

The Alpine deployment and measurement files are in
[`alpine-256mb/`](alpine-256mb/).

## Measurement method

Both tracks used one vCPU, loopback-only services, a fixed one-hour
observation, and independent operating-system snapshots. The observer recorded
system memory, swap, process RSS, CPU, filesystem use, application-data size,
service state, and restart counts. Service and kernel evidence was checked for
OOM kills and crashes.

The standard workload issued 72 bounded HTTP requests: 12 requests to each of
six Spring and StatLite endpoints. StatLite polled Spring Actuator and its own
metrics endpoint every 30 seconds with seven-day SQLite retention. Spring's
normal scheduled GitHub polling also ran during the window.

A run was not considered clean if either service was OOM-killed, crashed,
restarted, failed to become usable, or experienced severe sustained pressure
that prevented normal operation. High memory use by itself was not a failure
on these deliberately constrained machines.

## JVM profiles

The original Ubuntu comparison used this simple profile:

```text
-Xms16m -Xmx64m -Xss256k -XX:+UseSerialGC
```

The Alpine follow-up used this fixed Java 25 profile:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

The 64 MiB Alpine Java 21 profile was an unsuccessful tuning step. It caused
severe GC and paging pressure and was not used as the final result. The Java
25 run also changed the heap ceiling, compilation policy, code-cache ceiling,
and object-header mode, so the result must not be attributed to compact object
headers alone.

## Ubuntu configuration results

The Ubuntu 24.04 Multipass VM had a 5 GB virtual disk. Configured memory
differs from usable guest memory: the 256 MB VM exposed about 200 MiB, while
the 512 MB VM exposed about 452 MiB. The services ran under systemd.

| Configuration | Observation | Selected evidence | Result |
|---|---|---|---|
| 256 MB RAM, no swap, simple JVM | No stable observation window | Spring was OOM-killed during startup and entered a restart loop. | Not viable |
| 256 MB RAM, 256 MB swap, simple JVM | 60 minutes; 72/72 HTTP checks returned 200 | Swap was effectively full; Spring had one OOM restart; StatLite had none. | Completed, not stable |
| 256 MB RAM, 256 MB swap, aggressive JVM limits | Startup attempt only | Startup failed with a Metaspace allocation error after severe delay; StatLite remained healthy. | Unusable during startup |
| 512 MB RAM, no swap, simple JVM | 60 minutes; 72/72 HTTP checks returned 200 | Spring had one OOM restart during the first three minutes and then recovered; StatLite had none. | Completed, not clean |
| **512 MB RAM, 256 MB swap, simple JVM** | **60 minutes; 72/72 HTTP checks returned 200** | **Zero restarts. Final Spring RSS was 167,420 KiB and StatLite RSS 12,556 KiB, with 160 MiB swap used and 140 MiB RAM available.** | **Clean practical result** |

The successful Ubuntu window contained 240 StatLite polls—120 for each
target—and 2,640 metric samples. Spring reached health in 14 seconds and
normal three-repository polling continued throughout the hour.

## Alpine 256 MiB follow-up

The Alpine VPS was a nominal 256 MiB x86_64 guest with one vCPU and 5 GiB of
disk. The guest exposed approximately 216.9 MiB (`MemTotal: 222104 kB`). A
512 MiB swapfile was enabled before package installation and service startup.
The services ran as separate unprivileged OpenRC services bound to loopback.
Both foreground daemons use OpenRC `command_background="yes"`, allowing
OpenRC to manage their pidfiles and output logs correctly.

The preserved runtime identities were:

| Component | Identity |
|---|---|
| OS | Alpine Linux 3.24.1, x86_64 |
| Java package | `openjdk25-jre-headless-25.0.4_p7-r0` |
| Java runtime | OpenJDK `25.0.4` |
| StatLite | Official Linux amd64 release `v0.3.0` |
| StatLite SHA-256 | `553d6539659759380aaec6a9b0a3e050ecbea59f989b5101b1bd0dd30ce403a4` |
| Services | `stars` and `statlite` under OpenRC |

The Java 25 configuration completed the one-hour combined observation:

- Spring startup took 73.405 seconds.
- Spring and StatLite both remained started with no restart or OOM evidence.
- All 72 bounded HTTP requests returned HTTP 200.
- StatLite polling continued for both targets.
- Spring's scheduled GitHub polling continued after one early EOF/retry event.
- Final Spring RSS was 87,616 KiB.
- Final StatLite RSS was 10,196 KiB.
- Final combined RSS was 97,820 KiB.
- Final swap use was 184 MiB of 511 MiB usable.

The run recorded a Hikari warning for a housekeeper delay of about 2 minutes
13 seconds: “Thread starvation or clock leap detected.” This observation does
not establish whether paging, JVM memory pressure, scheduling, or a clock
event caused it. It is an operational limitation, not proof of a single root
cause.

## Interpretation

The Alpine result supports a narrow conclusion: this representative workload
could complete a controlled one-hour observation on the tested nominal 256 MiB
VPS with Alpine, Java 25, 512 MiB swap, and the constrained profile above. It
does not establish a comfortable production baseline.

The high swap use and long scheduling delay matter. For a real Spring Boot
deployment, the clean Ubuntu result—512 MB configured RAM plus a modest
swapfile—remains the practical starting point.

StatLite was not the dominant memory consumer. It remained a roughly 10 MiB
process in the Alpine result while continuing to monitor both targets. The
application and JVM were the source of the memory and responsiveness pressure.

## Data handling

The values above were transcribed from the preserved checkpoints and service
records. Usernames, hostnames, VM names, network addresses, process IDs, exact
wall-clock timestamps, and host-specific paths were omitted. No credentials,
databases, complete journals, or unrelated machine logs are included. The
detailed originals remain in the private experiment workspace.
