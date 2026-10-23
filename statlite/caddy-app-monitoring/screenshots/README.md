# Selected dashboards

These are unmodified 1440 by 1100 dashboard viewport captures. Times displayed
in the images are PDT (UTC minus seven hours). Their adjacent `*-api.json`
files contain capture time, dashboard URL, series and summary from a fetch a
few seconds after the screenshot. All URLs in these snapshots are loopback
test endpoints.

| Image | Role | Paired API |
| --- | --- | --- |
| [Express via Caddy](express-recovery.png) | Main image: separate 404/500 bursts, slow responses and recovery | [JSON](express-recovery-api.json) |
| [Spring via Caddy](spring-caddy.png) | Supporting evidence: independent host without Express's errors or latency spike | [JSON](spring-caddy-api.json) |
| [Spring direct](spring-direct.png) | Optional comparison: health, startup, JVM memory and CPU | [JSON](spring-direct-api.json) |

Suggested main caption:

> StatLite monitoring an Express application through Caddy. The controlled
> workload introduces HTTP errors and slower responses, all visible without
> application instrumentation.

Caddy UP means metrics collection succeeded, not that the upstream application
is healthy. The last request-count drop marks the generator stopping. Counts
are per polling interval, not requests per second. The 404 and 4xx lines overlap
because they count the same responses in this workload.

The Spring direct restart event predates the workload and comes from restarting
the fixture with retained history; it was not an injected failure.
