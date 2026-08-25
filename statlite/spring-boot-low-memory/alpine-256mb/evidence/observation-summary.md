# Alpine Java 25 observation summary

This is a curated summary of the preserved one-hour observation. It omits
hostnames, addresses, process IDs, exact wall-clock timestamps, and raw logs.

## Configuration

- Alpine Linux 3.24.1, x86_64
- Nominal 256 MiB VPS; guest-visible memory: approximately 216.9 MiB
- One vCPU and 5 GiB disk
- 512 MiB swapfile; 511 MiB usable at the final checkpoint
- OpenJDK 25.0.4 from `openjdk25-jre-headless-25.0.4_p7-r0`
- StatLite `v0.3.0`, Linux amd64 release
- Spring JVM:

  ```text
  -Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
  -XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
  -XX:+UseCompactObjectHeaders
  ```

## Outcome

| Measure | Result |
|---|---:|
| Observation window | 60 minutes |
| Spring startup | 73.405 seconds |
| Bounded HTTP checks | 72 / 72 returned HTTP 200 |
| Spring restarts | 0 |
| StatLite restarts | 0 |
| OOM evidence | None observed |
| Final Spring RSS | 87,616 KiB |
| Final StatLite RSS | 10,196 KiB |
| Final combined RSS | 97,820 KiB |
| Final swap use | 184 MiB of 511 MiB |

StatLite continued polling both the Spring Actuator target and its own metrics
target. Spring's scheduled GitHub polling continued after one early EOF/retry
event. A Hikari warning recorded a housekeeper delay of approximately 2
minutes 13 seconds; the observation did not isolate its cause.

The result demonstrates a controlled one-hour completion on the tested
configuration. It should be described as viable with limits, not as a
comfortable production baseline.
