# Monitoring a small Javalin application with StatLite

Can a small Javalin application be monitored with StatLite using Javalin's
existing Micrometer instrumentation?

**Yes.** Javalin's Micrometer metrics contain the core signals StatLite needs.
This example translates those metrics into StatLite's existing lightweight
metrics profile and demonstrates requests, errors, latency, JVM memory, CPU,
health, and restart history.

This is an application-side proof of concept, not built-in Javalin support or
a supported helper library. No Prometheus server or Grafana is required.
Javalin already exposes the useful metrics through Micrometer; the example
adds a small fixed translation, rather than new request instrumentation.

## Run it

Requirements: Java 17+, Maven, Python 3, and a StatLite binary supporting
`statlite-metrics/v1`. The recorded experiment used Java 25 and unmodified
StatLite revision `633daa6bfc9f9cf4a0f4f4dbf74d3da6e62afa03` (`v0.6.1-dev`).
Get StatLite from [PVRLabs/statlite](https://github.com/PVRLabs/statlite), or
build that revision with `go build -o statlite ./cmd/statlite`.

From this directory:

```sh
mvn -q compile dependency:build-classpath -Dmdep.outputFile=target/classpath.txt
mkdir -p runtime
python3 launch.py
```

In a second terminal, from this same directory:

```sh
statlite --config statlite.yaml
```

In a third terminal:

```sh
python3 probe.py
```

Open <http://127.0.0.1:19087> to see StatLite's dashboard. The probe sends 48
requests (12 each to `/hello`, `/slow`, `/missing`, and `/error`), verifies the
adapter counters and duration, then checks that requests, errors, heap, CPU,
and application health appear in StatLite's API. Keep other traffic off the
demo during the exact-count probe. Repeat it to add history.

Both services bind to loopback. Ports are 18087 (app) and 19087 (dashboard).
The two-second poll interval is for this local demo. SQLite history lives in
`runtime/statlite.sqlite`. Stop each service with Ctrl-C. For a fresh history,
move the runtime directory aside while StatLite is stopped and recreate it.
Set `DEMO_JAVA` to an absolute Java executable to select a different runtime.

## What the example contains

- [Application.java](src/main/java/example/Application.java): a small Javalin
  application with the normal `MicrometerPlugin`, standard JVM/CPU binders,
  a successful route, a 120 ms slow route, an unmatched 404, and a handled 500.
- [StatLiteSnapshot.java](src/main/java/example/StatLiteSnapshot.java): about
  59 lines translating cumulative Micrometer timers and gauges to
  [`statlite-metrics/v1`](https://github.com/PVRLabs/statlite/blob/main/docs/statlite-metrics-v1.md).
- [PrometheusDemo.java](src/main/java/example/PrometheusDemo.java): optional
  `/prometheus` output, following Javalin's usual Micrometer setup.
- [statlite.yaml](statlite.yaml): the existing `type: statlite-metrics` target
  pointing at `/statlite/metrics`.

The adapter sums `http.server.requests` counts and durations, classifies errors
by status, sums heap-only `jvm.memory.used` gauges, and converts Micrometer's
process CPU fraction into CPU cores. It supplies JVM start/uptime and optional
host CPU. Monitoring and health-control routes are excluded from both request
counts and duration. Average latency is duration delta divided by request delta.

Health is an explicit application assertion, initially `UP`. To demonstrate
successful collection with unhealthy application status:

```sh
curl -X POST http://127.0.0.1:18087/demo/health/DOWN
# Wait a few seconds and inspect the dashboard, then restore health:
curl -X POST http://127.0.0.1:18087/demo/health/UP
```

This local control route is demonstration code, not a production health check.
To demonstrate restart history, stop only the Java app, wait a few seconds,
restart `python3 launch.py`, and rerun `python3 probe.py`. Keep StatLite running
with its existing database. Its restart event and new process start should
appear; counter deltas must not cross application runs.

### Without Prometheus jars

Stop the app and run:

```sh
python3 launch.py simple
python3 probe.py
```

This uses `SimpleMeterRegistry` and removes every Prometheus jar from the
runtime classpath. `/prometheus` is absent; the same adapter and collector work.
The POM includes Prometheus only to demonstrate the normal scrape endpoint.

## Experiment result

The original version-pinned run on 2026-10-07 used Javalin 7.2.3,
Micrometer 1.17.0, Jetty 12.1.12, Temurin 25.0.4.1+1-LTS, and macOS x86_64.
Dependencies in this example remain pinned to the tested versions.

| Check | Recorded result |
|---|---|
| Initial workload | 48 requests, 12 404/4xx, 12 5xx, 1.488 s accumulated duration, 31.0 ms average |
| Runtime and health | Heap, process CPU, start/uptime, optional host CPU; explicit DOWN and UP collected |
| Restart | New run detected; first sample had no counter delta; no negative or cross-run deltas |
| Post-restart workload | 16 requests, 4 404/4xx, 4 5xx, 0.502 s duration |
| Simple registry, no Prometheus jars | 16 requests, 4 404/4xx, 4 5xx, 0.507 s duration |
| Dashboard | Requests, errors, average latency, runtime metrics, health, and restart behavior verified |

The polished public example was also rerun in both registry modes: each gave
48 requests, 12 404/4xx, 12 5xx, and 1.493 s duration. Health transitions and
restart boundaries passed; see [concise validation](validation.json).

These are observations from the completed spike, not performance guarantees
or certification of every Javalin version. This public example retains the
mapping and reproduction steps, rather than the investigation logs and screenshots.
A reusable application-owned helper was estimated at roughly 100–180 production
lines excluding tests/docs; none is published as a Maven library here.

## Could StatLite support Javalin directly?

Yes, probably with relatively little additional work. Javalin already exposes
these metrics through its normal Micrometer/Prometheus endpoint. StatLite
already contains bounded Prometheus/OpenMetrics parsing for framework-specific
integrations such as Quarkus and Micronaut. It would not need generic
Prometheus scraping support.

A future first-class target could potentially look like:

```yaml
targets:
  - name: my-app
    type: javalin
    url: http://localhost:8080
```

**This configuration is a proposal and does not work today.** In that model,
StatLite would read the application's existing Javalin/Micrometer endpoint
directly, without this experiment's `statlite-metrics/v1` adapter. The work
would mainly be Javalin-specific metric mapping, target/config wiring, tests,
docs, and compatibility certification. Native support has not been implemented
or certified; further engineering depends on Javalin community feedback.

## Limitations

- These Micrometer metrics provide no obvious authoritative application-health
  signal. The app supplies health; the demo does not infer dependency health.
- Very fast request timings appeared quantized to whole milliseconds in
  Javalin 7.2.3. This is handler execution timing, not network round-trip latency.
- Coverage is Javalin 7.2.3 / Micrometer 1.17.0, not every Javalin release.
- Counters must be cumulative. This example covers Prometheus and the default
  Simple registry, not step-based registries, shared apps, or removed meters.
- Count and duration reads are separate and can briefly skew under concurrency.
  CPU is a JVM/OS estimate; this run does not certify container CPU scaling.
- The fixed JSON writer accepts only controlled health strings and fixed keys;
  it is example code, not a general serializer. Host memory/disk and maximum
  latency display are outside this example.

## References

- [Javalin's Micrometer setup](https://javalin.io/plugins/micrometer)
- [Pinned Javalin plugin source](https://repo.maven.apache.org/maven2/io/javalin/javalin-micrometer/7.2.3/javalin-micrometer-7.2.3-sources.jar)
- [Micrometer timer semantics](https://docs.micrometer.io/micrometer/reference/concepts/timers.html)
- [StatLite](https://github.com/PVRLabs/statlite)
