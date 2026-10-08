# Javalin Micrometer/Prometheus experiment

Demonstrates Javalin's native Micrometer/Prometheus endpoint and preserves the
earlier experiment for possible future Javalin-specific StatLite integration
work. Current StatLite does not consume this Prometheus endpoint directly.

This archived application exposes `/prometheus` and a separate application-owned
`/statlite/metrics` adapter from the same registry. The included StatLite YAML
polls only the JSON adapter. The [main example](../) uses SimpleMeterRegistry
and the helper from the official StatLite integration guide.

## Reproduce the earlier experiment

Requirements: Java 17+, Maven, Python 3, and StatLite. From this directory:

```sh
mvn -q compile dependency:build-classpath -Dmdep.outputFile=target/classpath.txt
mkdir -p runtime
python3 launch.py
```

In separate terminals, from this directory:

```sh
statlite --config statlite.yaml
```

```sh
python3 probe.py
curl http://127.0.0.1:18087/prometheus
```

Open <http://127.0.0.1:19087>. Stop both services with Ctrl-C. The archived
example uses the same ports as the main example; run only one at a time.
`python3 launch.py simple` preserves the earlier no-Prometheus comparison.

[validation.json](validation.json) records the original 2026-10-07 results
with Javalin 7.2.3 and Micrometer 1.17.0. It describes the earlier helper,
not validation of the main example's revised helper or general compatibility.
The old helper's controlled JSON writer accepts only `UP` and `DOWN`; health
is application-owned. Its counters require cumulative registries and one
process. Request timing is quantized to whole milliseconds in this setup.
