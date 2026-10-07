# Integrate a Javalin application with StatLite

Use this guide to adapt the runnable demo to your own Javalin application.
This is an experimental application-owned `statlite-metrics/v1` integration,
not a built-in Javalin target or supported helper library. Tested coverage is
Javalin 7.2.3 / Micrometer 1.17.0; see [the experiment result](README.md#experiment-result).

The structure follows [StatLite's integration guides](https://github.com/PVRLabs/statlite/blob/main/docs/integrate/README.md)
so these instructions can later be reused there after review. The
[v1 specification](https://github.com/PVRLabs/statlite/blob/main/docs/statlite-metrics-v1.md)
remains authoritative.

## What it provides

Your Javalin application exposes a small JSON endpoint implementing
`statlite-metrics/v1`. StatLite polls it and keeps local SQLite history for
requests, HTTP errors, average latency, runtime memory, CPU, and restarts.
No Prometheus server, Grafana, Spring Boot, or Actuator is required.

The helper reads Javalin's existing Micrometer request timers. It does not add
another request logger or translate arbitrary metrics. The example uses a
Prometheus registry to let you inspect the source metrics, and also runs with
a normal cumulative `SimpleMeterRegistry` without any Prometheus jars.

## Two endpoints, two integration paths

The default demo exposes both endpoints from the same Micrometer registry:

| Endpoint | Purpose | StatLite support |
| --- | --- | --- |
| `/statlite/metrics` | Small fixed JSON adapter for application-owned integration | Works today with `type: statlite-metrics` |
| `/prometheus` | Javalin's normal Micrometer/Prometheus exposition | Demonstrates the source for a possible future native Javalin target |

The Prometheus endpoint makes the native-support opportunity concrete: the
application already exposes the required source metrics without a
StatLite-specific adapter. StatLite's existing bounded parser could be reused;
a Javalin-specific mapping, wiring, tests, and certification would still be
needed. Do not point the current `statlite-metrics` target at `/prometheus`.
Neither endpoint requires a Prometheus server. The Simple registry mode keeps
only the JSON endpoint and demonstrates the standalone adapter path.

## Copy the adapter and register the endpoint

The pinned dependencies are in [pom.xml](pom.xml). Keep the Javalin application
and plugin versions aligned. The adapter adds no SDK, network exporter, or
Maven helper library; it reads your existing Micrometer registry. If you already
register the plugin or bind JVM/CPU metrics, reuse that setup rather than
registering it twice. Close a registry only if your application owns its lifecycle.

For an application without Micrometer, add `io.javalin:javalin-micrometer:7.2.3`, configure a
default `SimpleMeterRegistry`, and install the plugin. The plugin brings
Micrometer core and its Jetty 12 integration. The Prometheus registry is
optional for this JSON endpoint.

The complete runnable setup is [Application.java](src/main/java/example/Application.java).
The fixed mapping is [StatLiteSnapshot.java](src/main/java/example/StatLiteSnapshot.java).
Copy the complete 59-line adapter source into your application's package and register
its endpoint during Javalin configuration, before startup:

```java
import io.javalin.Javalin;
import io.javalin.micrometer.MicrometerPlugin;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics;
import io.micrometer.core.instrument.binder.system.ProcessorMetrics;
import io.micrometer.core.instrument.binder.system.UptimeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.concurrent.atomic.AtomicReference;

// Inside your application's startup method:
MeterRegistry registry = new SimpleMeterRegistry();
new JvmMemoryMetrics().bindTo(registry);
new UptimeMetrics().bindTo(registry);
new ProcessorMetrics().bindTo(registry);
AtomicReference<String> health = new AtomicReference<>("UP");

Javalin app = Javalin.create(config -> {
    config.jetty.host = "127.0.0.1";
    config.registerPlugin(new MicrometerPlugin(plugin -> plugin.registry = registry));
    // Define your ordinary routes here.
    config.routes.get("/statlite/metrics", ctx -> ctx
        .contentType("application/json")
        .header("Cache-Control", "no-store")
        .result(StatLiteSnapshot.json(registry, health.get())));
}).start(8080);
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    app.stop();
    registry.close();
}));
```

The runnable source includes imports and lifecycle cleanup. GC/thread binders
are present there for inspection, but their metrics are not part of this
StatLite mapping. Heap/CPU binders are relevant; uptime/start are also available
directly through JVM management APIs.

The `health` value is **your application's assertion**. Set it from an
authoritative inexpensive or cached readiness signal if you have one; do not
perform database/network checks for each metrics request. The demo deliberately
allows only `UP` and `DOWN`. Its small JSON writer accepts those controlled
strings; use your normal JSON mapper if adapting it for arbitrary status text.
There is no automatic database health, and a 500 response does not itself
change application readiness. Do not infer dependency health from JVM metrics.

## Endpoint contract and field mapping

`GET /statlite/metrics` returns HTTP 200, `application/json`, and
`Cache-Control: no-store`, including when the application reports `DOWN`.
Collection success and application health are separate signals. The response
contains `schema: "statlite-metrics/v1"`, an integration identifier, `status`,
`started_at`, and a `metrics` object. The schema and status are required by v1;
start/uptime and metrics are optional protocol fields that this adapter supplies.
Missing or invalid optional CPU gauges are omitted rather than invented.
The controlled status strings keep the example's fixed JSON writer valid.

The endpoint performs no outbound requests or database I/O, and returns
aggregate values rather than route labels or request data. Snapshot reads do
have a small cost; use ordinary production polling rather than the demo's
fast interval.

## What gets mapped

| Output | Source |
|---|---|
| `requests_total` | Sum `http.server.requests` timer counts |
| `responses_404_total`, `responses_4xx_total`, `responses_5xx_total` | The same counts selected by `status` tags |
| `request_duration_seconds_total` | Sum the same timers' `totalTime(SECONDS)` |
| `runtime_heap_used_bytes` | Sum `jvm.memory.used` gauges with `area=heap` |
| `process_cpu_usage` | `process.cpu.usage` × JVM-visible processor count, in cores |
| `uptime_seconds`, `started_at` | RuntimeMXBean uptime and process start |
| `host_cpu_usage` | Optional `system.cpu.usage` fraction |
| `status` | Explicit application-owned health value |

The helper excludes `/statlite/metrics`, `/prometheus`, and the demo health
control route from both count and duration. Adapt those exclusions together if
you change routes or use a context path. It returns zero HTTP counters before
the first application request. It omits database status and host memory/disk.
Runtime memory means JVM heap used, not process RSS.

## Configure StatLite

Point `type: statlite-metrics` at the exact JSON URL:

```yaml
server:
  listen: "127.0.0.1:9090"
storage:
  sqlite_path: "statlite.sqlite"
polling:
  interval: "30s"
  timeout: "5s"
targets:
  - name: my-javalin-app
    type: statlite-metrics
    url: http://127.0.0.1:8080/statlite/metrics
```

Start your existing StatLite binary with `statlite --config statlite.yaml`.
Open `http://127.0.0.1:9090`. Keep the metrics endpoint on loopback or a private
network; this StatLite target does not send authentication credentials.

## Verify your application

For the application on port 8080 in the setup above:

```sh
curl -fsS http://127.0.0.1:8080/statlite/metrics
statlite inspect 'http://127.0.0.1:8080/statlite/metrics'
statlite --config statlite.yaml
```

Check the schema, explicit status, and process start. Send representative
successful, slow, 404, and 500 requests to your own routes, then fetch the
endpoint again: counts and accumulated duration should increase. After at
least two StatLite polls, check request/error deltas and average latency.
Inspection checks collection and suggests configuration; it does not install
the adapter in your app.

## Verify with the demo

Use [README.md](README.md) for build/run commands. Generate traffic for
`/hello` (200), `/slow` (200 after about 120 ms), `/error` (500), and an unmatched
path (404). Compare `/prometheus` and `/statlite/metrics`, then check the real
StatLite requests, errors, latency, and runtime charts. The supplied probe
checks exact counter increases and verifies collection through StatLite's API.
Run it only against the unmodified demo routes on port 18087.

Restart the application once: start time changes and counters reset. StatLite
should record the restart, omit the new run's first counter delta, and then
show subsequent traffic normally. The recorded experiment verifies this.

## Boundaries to review

* Use a cumulative registry. A step timer reports interval values, not
  process-lifetime totals. The helper cannot read arbitrary registries as v1
  monotonic counters. Default Simple and Prometheus were tested.
* The pinned Javalin plugin truncates request durations to whole milliseconds.
  Sub-millisecond requests can have zero recorded time. Average latency is
  execution time, not a percentile or full client round-trip measurement.
* CPU is a recent best-effort JVM measurement. Counts and durations are read
  separately and can be briefly skewed during concurrent traffic.
* Use a registry scoped to one application process. For multiple replicas,
  use separate stable endpoints/targets; polling a load-balanced URL does not
  aggregate them. Do not rename/remove these meters through custom filters.
* This version-pinned proof of concept does not certify every Javalin, Jetty,
  Micrometer, JVM, or container configuration. Maximum latency is intentionally
  absent from StatLite's display; host memory/disk are optional and omitted.

## Could StatLite support Javalin's Prometheus endpoint natively?

Potentially, through a narrow Javalin-specific collector. StatLite already has
bounded parsing for its fixed Quarkus/Micronaut integrations, so new generic
Prometheus support would not be needed. Native support is gated on community
feedback and has not been implemented or certified. Missing today are a
`javalin` target,
the fixed mapping and compatibility inspection, documentation, and certified
Javalin setup/version coverage. Application health would still need an explicit
source. This is possible future work for discussion, not part of the PoC.

The community review questions are whether the request timer/tag contract is
appropriate, whether the timing and registry caveats are clear, and whether
this lightweight local-history example is useful enough to maintain together.
