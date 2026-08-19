# Experiment details

This document supplements the concise benchmark summary with the experiment
method, configuration-by-configuration results, and selected measurements from
the preserved runs. It intentionally does not reproduce the complete execution
journal or service logs.

## Method

The experiment used an Ubuntu 24.04 Multipass VM with 1 vCPU and a 5 GB virtual
disk. A Java 21 Spring Boot 3.5.5 application and StatLite ran as separate
systemd services. Both services listened only on the VM loopback interface.

The application used Spring Data JPA, Hibernate, H2, embedded Tomcat,
Actuator, scheduled GitHub polling, and outbound HTTP. Except for the explicitly
labeled aggressive-JVM attempt, Spring used:

```text
-Xms16m -Xmx64m -Xss256k -XX:+UseSerialGC
```

StatLite polled Spring Actuator and its own metrics endpoint every 30 seconds
with seven-day SQLite retention. The standard observation was a fixed 60-minute
window. It included 72 bounded HTTP requests: 12 requests to each of six Spring
and StatLite endpoints. Checkpoints recorded system memory, swap, process RSS,
CPU, filesystem use, application-data size, service state, and restart counts.
Service and kernel evidence was checked for OOM kills and crashes.

A configuration was not considered clean if Spring or StatLite was OOM-killed,
crashed, restarted, failed to become usable, or experienced severe sustained
memory pressure or paging that prevented normal operation. High memory use by
itself was not a failure on these deliberately constrained machines.

## Configuration results

Configured memory differs from usable guest memory: the 256 MB VM exposed
about 200 MiB, while the 512 MB VM exposed about 452 MiB.

| Configuration | Observation | Selected evidence | Result |
|---|---|---|---|
| 256 MB RAM, no swap, simple JVM | No stable observation window | Spring was OOM-killed during startup and entered a restart loop. | Not viable |
| 256 MB RAM, 256 MB swap, simple JVM | 60 minutes; 72/72 HTTP checks returned 200 | Swap was effectively full; Spring had one OOM restart; StatLite had none. Final RSS was 50,840 KiB for Spring and 3,616 KiB for StatLite after recovery. | Completed, not stable |
| 256 MB RAM, 256 MB swap, aggressive JVM limits | Startup attempt only | At the failure checkpoint, 187 MiB of 255 MiB swap was used. Startup failed with a Metaspace allocation error after severe delay; StatLite remained healthy. | Unusable during startup |
| 512 MB RAM, no swap, simple JVM | 60 minutes; 72/72 HTTP checks returned 200 | Spring had one OOM restart during the first three minutes and then recovered; StatLite had none. Final RSS was 270,284 KiB for Spring and 5,300 KiB for StatLite. | Completed, not clean |
| **512 MB RAM, 256 MB swap, simple JVM** | **60 minutes; 72/72 HTTP checks returned 200** | **Zero restarts. Final RSS was 167,420 KiB for Spring and 12,556 KiB for StatLite, with 160 MiB swap used and 140 MiB RAM available.** | **Clean practical result** |

The aggressive profile added explicit limits for metaspace, code cache, direct
memory, and tiered compilation. It was an extreme diagnostic comparison, not a
recommended production profile.

## Selected successful-run observations

These checkpoints come from the clean `512 MB RAM / 256 MB swap / simple JVM`
run. Times are relative to the start of the observation; host-specific
timestamps and process identifiers have been omitted.

| Checkpoint | RAM available | Swap used | Spring RSS | StatLite RSS | Combined RSS | Restarts Spring / StatLite |
|---|---:|---:|---:|---:|---:|---:|
| Start | 81 MiB | 37 MiB | 244,024 KiB | 13,128 KiB | 257,152 KiB | 0 / 0 |
| +90 seconds | 109 MiB | 97 MiB | 202,532 KiB | 13,588 KiB | 216,252 KiB | 0 / 0 |
| +3 minutes, after bounded traffic | 106 MiB | 140 MiB | 211,944 KiB | 10,044 KiB | 221,992 KiB | 0 / 0 |
| +60 minutes | 140 MiB | 160 MiB | 167,420 KiB | 12,556 KiB | 179,976 KiB | 0 / 0 |

Spring reached health in 14 seconds. All 72 bounded requests returned HTTP 200,
and normal three-repository polling continued throughout the hour. The window
contained 240 StatLite polls—120 for each target—and 2,640 metric samples. H2
data remained 44 KiB, while StatLite data grew from 548 KiB to 736 KiB. Root
filesystem utilization increased from 65% to 70%.

## Selected failure evidence

The preserved service records showed these failure observations:

- With 256 MB RAM and no swap, Spring was OOM-killed before a settled baseline
  could be maintained and systemd repeatedly restarted it.
- With 256 MB RAM and 256 MB swap, systemd recorded an OOM kill 35 minutes into
  the observation. Spring recovered automatically; StatLite stayed active and
  continued monitoring.
- With aggressive JVM limits, Spring emitted a thread-starvation warning and
  failed during application-context creation with a Metaspace allocation error.
- With 512 MB RAM and no swap, systemd recorded an OOM kill about three minutes
  into the observation. Spring restarted and operated normally for the rest of
  the hour; StatLite remained active.

These failures are why results from the five configurations are reported
separately rather than blended into one baseline.

## Interpretation and limits

This is evidence for one small but representative Spring Boot application, not
a claim that every Spring Boot workload fits the same heap or machine. GitHub
API behavior, VM overhead, kernel behavior, dependency versions, and application
features can change the result. A larger application may reasonably require a
larger heap and more system memory.

The experiment supports a narrower conclusion: 256 MB RAM was an extreme and
unstable target for this workload. A VM configured with 512 MB RAM and a modest
swapfile completed the controlled hour cleanly, while StatLite remained a small
part of the total footprint.

## Data handling

The values above were transcribed from the original checkpoints and service
records. Usernames, hostnames, VM names, network addresses, process IDs, exact
wall-clock timestamps, and host-specific paths were omitted. No credentials,
databases, complete journals, or unrelated machine logs are included. The
detailed originals remain in the private experiment workspace.
