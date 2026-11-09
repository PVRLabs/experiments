# Five Java stacks on a 512 MiB VM

Two accepted HotSpot runs and two matched Native Image runs per stack: Spring JDBC, Javalin + CoilBase, Jex + CoilBase, Micronaut Data, and Micronaut + CoilBase.

This is a synthetic quote/status/audit fixture, not Market Replay Portfolio. The maintainer develops CoilBase. These observations describe complete stacks under light traffic, not framework capacity or universal rankings.

## Results

Each cell shows run 1 / run 2. RSS is the median application process RSS during the workload; readiness is the database-backed readiness time. These are two observations per configuration, not confidence intervals.

| Stack | HotSpot RSS (MiB) | HotSpot readiness (s) | Native RSS (MiB) | Native readiness (s) |
| --- | ---: | ---: | ---: | ---: |
| Spring Boot + Spring JDBC | 180.6 / 187.9 | 7.425 / 8.653 | 84.0 / 85.0 | 0.172 / 0.273 |
| Javalin + CoilBase | 135.6 / 120.9 | 3.063 / 2.920 | 59.2 / 58.3 | 0.078 / 0.172 |
| Micronaut Data JDBC | 175.0 / 174.0 | 4.397 / 4.345 | 89.7 / 91.7 | 0.188 / 0.175 |
| Micronaut + CoilBase | 166.5 / 167.6 | 4.248 / 5.275 | 82.4 / 81.8 | 0.211 / 0.212 |
| Jex + CoilBase | 116.0 / 116.4 | 2.022 / 2.543 | 33.4 / 51.0 | 0.058 / 0.076 |

See [HotSpot data](hotspot.json) and [Native Image data](native.json) for the full recorded per-run summaries.

## Method

One vCPU, 512 MiB RAM, no swap, colocated MariaDB. Each run: 60 seconds idle, 120 seconds warm-up, 300 seconds workload, 60 seconds recovery. Workload: 1,200 latest reads, 150 quote inserts, 150 status/audit transactions, approximately five requests per second. All accepted runs completed 1,500 requests with SQL trace validation. HotSpot used OpenJDK 27 and G1; Native Image used a different JDK/compiler configuration, so runtime differences cannot be attributed solely to compilation mode.

The JSON files preserve accepted per-run metrics and database validation states. Values containing `mib` use 1,048,576 bytes. Per-run medians describe samples within a run. Two observations do not establish confidence intervals. Sampled memory peaks can miss short events; application RSS excludes database and OS memory. Readiness includes the database-backed readiness probe.

## Verify

Run `python3 analyze.py` from this directory. It requires exactly rounds 1 and 2 for each of the five expected stacks in each runtime, checks recorded warm-up/workload request totals and endpoint successes, rejects errors/timeouts/unsent requests, and verifies recorded final database counts (1,210 quotes, 210 audits, 100 records) and SQL trace validation. It then prints per-run workload RSS and readiness. This verifies the curated summaries only. Raw request traces, OS captures, build logs and complete runnable sources are not included; this package cannot independently reconstruct the original measurements or reproduce the deployment.

The measured CoilBase was an early prototype. The released API subsequently evolved. These measurements are not results for a current CoilBase preview. Native build iteration and compatibility costs are discussed in the accompanying article.
