# OpenTelemetry Java Agent on a 512 MiB VPS

This small exploratory run compared an existing Spring Boot application with the
same application instrumented by the OpenTelemetry Java agent, focusing on the
memory footprint of a small VPS. It is not a general capacity recommendation.

## Environment and method

The application was Spring Boot 4.1.1 on OpenJDK 27+35 HotSpot, with Spring AOT,
an extracted application JAR, local MariaDB, and a separate HTTP fixture. The
Ubuntu VM had one vCPU, 512 MiB RAM and no swap. The agent was OpenTelemetry Java
agent **2.33.1**. It used the logging metrics exporter at 10-second intervals;
trace and log exporters were disabled. Trace generation itself was not explicitly
disabled. The [related Spring Boot experiment](../../spring/boot-jdk27/) describes
the application and deployment; its public package does not include the complete
application source and build needed to reproduce this run.

The initial baseline used `-Xmx80m`, Spring AOT and a trained JDK AOT cache. The
agent was then attached with the same settings and retried at `-Xmx150m`; both
agent attempts failed to reach readiness within 90 seconds. Attaching the agent
caused the existing JDK AOT cache to be rejected because `java.instrument` was
present at runtime but absent during cache training.

A diagnostic then used `-Xmx150m` with **no JDK AOT cache** for either
configuration. It captured startup GC, process RSS, available system memory and
memory pressure. The final agent run temporarily increased VM RAM to 1 GiB; other
VM resources and the application configuration stayed the same. For successful
runs, startup is JVM launch to HTTP health and quote readiness. After 10 seconds
idle, a local client sent 150 requests to `GET /api/quotes/latest` at 5 requests/s.

The diagnostic used the JVM arguments below. These are not complete reproduction
commands: the MariaDB and HTTP fixture configuration is omitted, and the full
application build is not included in the public package.

```sh
java -Xmx150m -Dspring.aot.enabled=true -Xlog:gc* -jar app.jar
```

The agent run added these arguments before `-jar`:

```text
-javaagent:opentelemetry-javaagent.jar
-Dotel.traces.exporter=none
-Dotel.logs.exporter=none
-Dotel.metrics.exporter=logging
-Dotel.metric.export.interval=10000
```

## Observations

| Configuration | VM RAM | Startup | Idle app RSS | Workload app RSS | Requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline, `-Xmx80m`, JDK AOT cache | 512 MiB | 3.88 s | 168.2 MiB | 168.8 MiB median | 150/150 |
| Baseline, `-Xmx150m`, no JDK AOT cache | 512 MiB | 7.16 s | 204.2 MiB | 208.5 MiB at end | 150/150 |
| Agent, `-Xmx150m`, no JDK AOT cache | 512 MiB | Did not reach readiness | — | — | — |
| Agent, `-Xmx150m`, no JDK AOT cache | 1 GiB | 22.50 s | 285.1 MiB | 286.4 MiB at end | 150/150 |

The 512 MiB no-cache agent run was killed during startup by the Linux global
OOM killer; the captured kernel message explicitly identified `global_oom`. Its
peak sampled RSS was 212.3 MiB and the minimum sampled host `MemAvailable` was
12.4 MiB. The cgroup `oom_kill` counter also increased; that counter alone does
not distinguish a global OOM from a cgroup-triggered OOM. Its last
recorded young GC reduced heap use from 61 MiB to 32 MiB, supporting system
memory exhaustion rather than a demonstrated Java heap OOM. A thread dump timed
out and the heap-info attach failed under pressure. The 512 MiB no-cache baseline
also experienced pressure, reaching 15.7 MiB minimum available memory.

On 1 GiB, the instrumented app started and exported
`http.server.request.duration` for the quote route; the exported histogram
contained 151 successful observations including readiness. The 150 workload
requests averaged 8.48 ms with an approximate 15.61 ms p95. The
[retained final-run summary](results/agent-1g.json) and
[HTTP metric excerpt](results/http-metric.txt) are from that run. Earlier guest
logs were cleared by the VM reboot; their results above come from observations
recorded before reboot, not reconstructed raw data.

These are single runs. The 512 MiB baseline and 1 GiB agent runs have different
host headroom, so their RSS and latency differences do not provide a controlled
steady-state agent overhead estimate. Startup and end-of-workload RSS are distinct
observations, and this brief workload does not establish long-term behavior.
The logging exporter avoids network retries but is not representative of every
production exporter. The outcome applies to this application and configuration;
it does not establish that the agent is unsuitable for all small deployments.
