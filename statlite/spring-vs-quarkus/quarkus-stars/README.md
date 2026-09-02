# Star Pulse for Quarkus

An independent Quarkus version of [`springboot-stars`](../springboot-stars/).
It tracks GitHub star counts for up to four repositories, stores changes in a
file-backed H2 database, renders the same dashboard shape, and polls every five
minutes after a short startup delay.

This fixture is intentionally independent of the VPS and StatLite experiments.
It uses Quarkus-native CDI, Qute, REST Client Reactive, Hibernate ORM with
Panache, and the Quarkus scheduler. It is a JVM application, not a native-image
benchmark.

## Requirements

- JDK 21
- Maven or `mvn-lite` for building
- No Maven is needed on the eventual runtime host

## Build and run

```bash
mvn-lite test
mvn-lite package -DskipTests -Dquarkus.analytics.disabled=true
./run.sh
```

The dashboard listens on [http://localhost:8081](http://localhost:8081).
Prometheus metrics use the same application server at `/q/metrics`, so the
complete URL is `http://localhost:8081/q/metrics`. The
`quarkus-smallrye-health` dependency exposes
`http://localhost:8081/q/health`; Quarkus's built-in datasource readiness check
reports H2 status so a StatLite Quarkus target records `db_health_status` like
the Spring Boot target.

Set `APP_GITHUB_REPOS` and optionally `GITHUB_TOKEN` before starting. The
default repositories match the Spring fixture. H2 data is written below
`./data-quarkus/` and survives restarts. This path is intentionally distinct
from Spring's `./data/` path for side-by-side runs.

## Configuration

| Property | Default | Purpose |
|---|---|---|
| `app.github.repos` | three PVRLabs repos | comma-separated repositories, capped at 4 |
| `app.github.api-base-url` | `https://api.github.com` | GitHub API base URL |
| `app.github.token` | `GITHUB_TOKEN` or empty | optional bearer token |
| `quarkus.http.port` | `8081` | dashboard port |
| `quarkus.micrometer.export.prometheus.path` | `metrics` | Prometheus path below `/q` |
| `app.github.poll-interval` | `5m` | scheduled poll interval |

The low-resource defaults use one HTTP I/O thread, one Vert.x event-loop
thread, and a four-thread worker-pool ceiling. These are Quarkus-specific
settings and are not intended to be numerically equivalent to Spring's
Tomcat thread settings.

History rules and the database tables intentionally follow the Spring app:
every successful response updates `last_polled_at`, and a `star_history` row
is added only when the star count changes. A failed repository does not abort
the rest of the poll cycle.
