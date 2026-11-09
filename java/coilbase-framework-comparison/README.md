# Five Java stacks on a 512 MiB VM

Two accepted HotSpot runs and two matched Native Image runs per stack: Spring JDBC, Javalin + CoilBase, Jex + CoilBase, Micronaut Data, and Micronaut + CoilBase.

This is a synthetic quote/status/audit fixture, not Market Replay Portfolio. The maintainer develops CoilBase. These observations describe complete stacks under light traffic, not framework capacity or universal rankings.

## Method

One vCPU, 512 MiB RAM, no swap, colocated MariaDB. Each run: 60 seconds idle, 120 seconds warm-up, 300 seconds workload, 60 seconds recovery. Workload: 1,200 latest reads, 150 quote inserts, 150 status/audit transactions, approximately five requests per second. All accepted runs completed 1,500 requests with SQL trace validation. HotSpot used OpenJDK 27 and G1; Native Image used a different JDK/compiler configuration, so runtime differences cannot be attributed solely to compilation mode.

The JSON files preserve accepted per-run metrics and database validation states. Values containing `mib` use 1,048,576 bytes. Per-run medians describe samples within a run. Two observations do not establish confidence intervals. Sampled memory peaks can miss short events; application RSS excludes database and OS memory. Readiness includes the database-backed readiness probe.

## Verify

Run `python3 analyze.py` from this directory. It requires exactly rounds 1 and 2 for each of the five expected stacks in each runtime, checks recorded warm-up/workload request totals and endpoint successes, rejects errors/timeouts/unsent requests, and verifies recorded final database counts (1,210 quotes, 210 audits, 100 records) and SQL trace validation. It then prints per-run workload RSS and readiness. This verifies the curated summaries only. Raw request traces, OS captures, build logs and complete runnable sources are not included; this package cannot independently reconstruct the original measurements or reproduce the deployment.

The measured CoilBase was an early prototype. The released API subsequently evolved. These measurements are not results for a current CoilBase preview. Native build iteration and compatibility costs are discussed in the accompanying article.
