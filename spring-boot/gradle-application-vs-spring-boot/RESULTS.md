# Results

Run on 2026-09-17 using the existing `spring-boot-layout-256` VM: Alpine,
one vCPU, 256 MiB RAM, 512 MiB swap, OpenJDK 25.0.4. Each layout had three
fresh starts in the fixed order `fat, extracted, gradle`, three loopback
requests, and 30 seconds of observation. All nine runs succeeded.

| run | layout | Spring startup | external startup | first request | peak RSS | settled RSS |
|---|---|---:|---:|---:|---:|---:|
| 01 | fat | 10.449 s | 11,320 ms | 1.950138 s | 157,964 KiB | 134,844 KiB |
| 02 | extracted | 8.130 s | 8,720 ms | 1.449283 s | 152,736 KiB | 132,148 KiB |
| 03 | Gradle application distribution | 7.921 s | 8,490 ms | 1.343323 s | 158,140 KiB | 135,936 KiB |
| 04 | fat | 9.905 s | 10,690 ms | 1.990808 s | 153,084 KiB | 131,248 KiB |
| 05 | extracted | 8.357 s | 8,890 ms | 1.414253 s | 154,352 KiB | 132,188 KiB |
| 06 | Gradle application distribution | 7.572 s | 8,100 ms | 1.276889 s | 156,924 KiB | 132,612 KiB |
| 07 | fat | 10.103 s | 10,890 ms | 1.878592 s | 152,176 KiB | 128,384 KiB |
| 08 | extracted | 8.500 s | 9,100 ms | 1.427215 s | 155,592 KiB | 134,108 KiB |
| 09 | Gradle application distribution | 10.106 s | 10,760 ms | 1.727440 s | 154,120 KiB | 139,432 KiB |

## Median summary

| layout | Spring startup | external startup | first request |
|---|---:|---:|---:|
| fat | 10.103 s | 10,890 ms | 1.950138 s |
| extracted | 8.357 s | 8,890 ms | 1.427215 s |
| Gradle application distribution | 7.921 s | 8,490 ms | 1.343323 s |

The Gradle distribution had the lowest medians in this short run, about 21.6%
below the fat JAR for Spring startup and 31.1% below it for first-request
latency. RSS did not produce a useful winner from three samples per layout.

