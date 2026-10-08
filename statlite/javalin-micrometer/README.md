# Monitor Javalin with StatLite

A small Javalin application demonstrating requests, HTTP errors, average
latency, JVM heap, process CPU, application health, and restart history:

**Javalin → Micrometer → tiny `statlite-metrics/v1` adapter → StatLite**

It uses `SimpleMeterRegistry` and Javalin's Micrometer plugin. No Prometheus
dependency or server is required. [StatLiteMetrics.java](src/main/java/example/StatLiteMetrics.java)
is the helper published in the official [Javalin integration guide](https://github.com/PVRLabs/statlite/blob/main/docs/integrate/java/javalin.md).
That guide owns the application setup instructions and caveats; this directory
owns the runnable example. The application owns its adapter and readiness
signal; StatLite consumes the generic metrics contract.

## Run

Prerequisites: Java 17+, Maven, Python 3, and a
[StatLite binary](https://github.com/PVRLabs/statlite/blob/main/docs/install.md).
The example pins Javalin 7.2.3, its Micrometer plugin (Micrometer 1.17.0), and
Jackson Databind 2.22.1. From this directory, start the app:

```sh
mvn compile exec:java
```

In a second terminal, from this directory, start StatLite:

```sh
mkdir -p runtime
statlite --config statlite.yaml
```

In a third terminal, generate traffic:

```sh
python3 probe.py
```

Open <http://127.0.0.1:19087>. The probe sends 48 requests: 12 each to `/hello`,
`/slow` (120 ms), an unmatched `/missing` (404), and `/error` (500). It checks
counter increases and StatLite collection. Repeat it to add history; avoid
other application traffic during its exact-count checks.

Both services bind to loopback. The app uses port 18087 and exposes
`/statlite/metrics`; StatLite uses port 19087. The two-second polling interval
is for this local demo. History is stored in `runtime/statlite.sqlite`.
Stop each service with Ctrl-C.

## Health and restarts

Health starts at `UP`. The demo control route changes the application-owned
readiness value without running dependency checks:

```sh
curl -X POST http://127.0.0.1:18087/demo/health/DOWN
# Wait for a poll, view the dashboard, then restore readiness:
curl -X POST http://127.0.0.1:18087/demo/health/UP
```

The health-control requests count as application traffic; only the metrics
route is excluded by the shared helper. Restore `UP` before running the probe,
which checks healthy collection. This control route is local demo code.

To see a restart, keep StatLite running, stop the Java app, and run
`mvn compile exec:java` again. Rerun `python3 probe.py`; the JVM start time
changes and StatLite records the new run without deriving deltas across it.

## Earlier Prometheus experiment

[prometheus/](prometheus/) preserves the earlier source and results for
Javalin's native Micrometer/Prometheus endpoint. Current StatLite does not
consume that endpoint directly.
