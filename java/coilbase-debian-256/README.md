# HotSpot and OpenJ9 on a 256 MiB Debian guest

Recorded 2026-11-17. One short run of the existing quote API on Temurin and on
Semeru. This is not a rerun of the [Alpine HotSpot comparison](../coilbase-vps-256mb/README.md),
and it does not replace those results.

After the first few seconds, Jex + CoilBase used less resident memory on
Semeru than on Temurin, and the guest had more memory available. The initial
smoke observation at the first successful request is separate from the later
repeated-sample capture. The second Semeru start, with the shared class cache
already written, was ready about as fast as Temurin and did not swap.
Spring Boot was larger on both runtimes. Both Spring processes swapped.
Semeru kept more of Spring off swap and left more guest memory available.

## Result

Medians of nine samples taken every 5 seconds, at phase offsets 0 through 40
seconds. RSS is the application process's `VmRSS`, including embedded H2;
swap is the same process's `VmSwap`. Both were sampled from process status.
Available memory is guest-wide `MemAvailable`. Figures are MiB.

| Run | Ready | Idle RSS | Idle swap | Idle available | Load RSS | Load swap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Temurin CoilBase | 3 s | 90.6 | 0 | 62.7 | 92.8 | 0 |
| Semeru CoilBase, cold cache | 8 s | 74.9 | 4.6 | 102.3 | 81.1 | 8.8 |
| Semeru CoilBase, warm cache | 3 s | 73.7 | 0 | 90.1 | — | — |
| Temurin Spring | 10 s | 126.6 | 58.2 | 37.9 | 118.6 | 70.6 |
| Semeru Spring, cold cache | 21 s | 88.5 | 14.8 | 86.8 | 121.9 | 19.4 |

Ready is the one-second poll count until `GET /api/quotes/latest` succeeded.
Each sampled phase spans about 45 seconds; nine observations occur from 0 to
40 seconds after sampling starts. The warm run did not repeat the read load.
Adding idle RSS and idle swap gives rough accounting indicators of about 90.6
MiB for Temurin CoilBase, 79.6 MiB for cold Semeru CoilBase, 73.7 MiB for warm
Semeru CoilBase, 184.8 MiB for Temurin Spring, and 103.3 MiB for Semeru Spring.
RSS is resident pages and swap is nonresident; their sum is not physical RAM
occupied or an exact process footprint. Spring's
load RSS moved in opposite directions: Temurin fell from 126.6 to 118.6 MiB
while its swap rose from 58.2 to 70.6 MiB; Semeru rose from 88.5 to 121.9 MiB
while its swap rose from 14.8 to 19.4 MiB.



Cold Semeru CoilBase RSS was 97.2 MiB at the first idle sample and 102.2 MiB
at five seconds, then the remaining samples were about 70–75 MiB. The median of
all nine samples is 74.9 MiB. The earlier single-point smoke, taken at the
first successful request with no swap reset, recorded 100.1 MiB ([smoke evidence](smoke-001.txt)); it is a
separate observation from the repeated-sample capture. During the read load, Semeru
CoilBase RSS ranged from 68.3 to 96.0 MiB. Temurin CoilBase stayed between
90.5 and 95.4 MiB in idle and between 90.5 and 93.6 MiB under load, with no
process swap.

Every load request succeeded: 206, 202, 202 and 198 reads, and no failed
reads. The connection-refused lines in the capture are the readiness polls
before the process was listening. The Semeru cache directory was about 22 MiB
on disk after CoilBase and about 43 MiB after Spring.

## Method

Debian 13 genericcloud (image `20260712-2537`) on a local macOS Lima VZ
guest, `coilbase-debian-256`. One vCPU, 256 MiB allocated (211 MiB guest
MemTotal), 6 GiB disk, 512 MiB swapfile, swappiness 60. Kernel
6.12.95+deb13-cloud-amd64. Apt daily timers and fwupd refresh were disabled.
The guest was not rebooted between runs.

Runtimes are the Temurin 25.0.5+8 JRE and the IBM Semeru Runtime Open Edition
25.0.5.0 JRE (Eclipse OpenJ9 0.63.0). Both were extracted on the Mac and
copied to the guest after extraction on the host because the guest temporary filesystem was too small. Launch
flags were `-Xms16m -Xmx80m -Xss512k`. No collector flag was set. A separate
Temurin process with those heap flags selected Serial GC ergonomically; the
measured processes did not log the collector. Semeru was started with its
shared class cache enabled and a per-application cache directory
(`-Xshareclasses:name=<app>,cacheDir=...,nonfatal`), so CoilBase and Spring
did not share one cache. The warm CoilBase run reused the cache the cold run
had just written.

The applications are the packaged jars from
the earlier Alpine experiment bundle: Jex + CoilBase
0.1.0-preview3, and Spring Boot 4.1.1 with Spring JDBC. Same quote API,
file-backed H2 2.4.240, and Hikari pool of one idle and two maximum
connections. Each run had a fresh `run.dir`, so each process created its own
database. H2 memory is part of application RSS.

Before each run the swapfile was turned off and back on, and the page cache
was dropped. Sampling started after the first successful latest-quote read:
every 5 seconds for 45 seconds idle, then 45 seconds of the same read. The
client slept 0.2 seconds after each request, so the achieved rate was about
4.5 requests per second, not a scheduled 5 per second. The warm run sampled
idle only. No StatLite agent and no write traffic. Evidence:
[capture.txt](capture.txt).

## What this run does not support

One run per cell, on a guest that stayed up. Startup is coarse to one second,
and dropping the page cache makes the first seconds include reading the JRE
from disk. The Alpine numbers used an explicit Serial GC, a rebooted guest,
and a longer mixed read/write load. They are a different measurement.
Collector, shared-cache, and thread differences are recorded here, not
separated. Spring's swap means its RSS ranking during the load is not its
memory requirement.
