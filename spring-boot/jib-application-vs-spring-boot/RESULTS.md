# Results

Run on 2026-09-21 using the existing `spring-boot-layout-256` VM: Alpine,
one vCPU, 256 MiB RAM, 512 MiB swap, and OpenJDK 25.0.4. All six planned
starts succeeded. Every run served three validated HTTP 200 requests and
survived the 30-second observation.

RSS and process swap values in this file and the CSV are KiB. Startup and
request values are seconds unless the column says milliseconds.

## Per-run measurements

| run | layout | Spring startup | external startup | first request | peak RSS KiB | settled RSS KiB | observation-end process swap KiB |
|---|---|---:|---:|---:|---:|---:|---:|
| 01 | extracted | 12.934 | 13,880 | 1.829480 | 160,992 | 143,368 | 80,948 |
| 02 | Jib | 12.841 | 13,740 | 2.018467 | 165,468 | 132,164 | 81,164 |
| 03 | extracted | 12.472 | 13,350 | 1.798460 | 158,504 | 126,672 | 76,968 |
| 04 | Jib | 13.100 | 14,030 | 2.186600 | 156,832 | 144,920 | 74,488 |
| 05 | extracted | 13.275 | 14,200 | 2.022414 | 156,416 | 130,580 | 85,780 |
| 06 | Jib | 12.767 | 13,610 | 1.846652 | 158,720 | 125,780 | 94,024 |

## Median summary

| layout | Spring startup | external startup | first request | peak RSS | settled RSS | process swap |
|---|---:|---:|---:|---:|---:|---:|
| Extracted | 12.934 s | 13,880 ms | 1.829 s | 154.8 MiB | 127.5 MiB | 79.1 MiB |
| Jib | 12.841 s | 13,740 ms | 2.018 s | 155.0 MiB | 129.1 MiB | 79.3 MiB |

Jib's median external startup was 140 ms lower, which is effectively tied at
this sample size. Its median first request was about 0.19 seconds higher, but
the individual values varied. The memory measurements were similar and did
not identify a clear winner.

This is directional evidence for one application, VM, JDK, and JVM profile;
it is not a general claim about Jib or Spring Boot.
