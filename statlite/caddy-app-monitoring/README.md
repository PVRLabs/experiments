# Monitoring applications behind Caddy

Caddy's per-host metrics let StatLite show HTTP requests, errors and average
latency without changing the applications. This experiment used Express with
no metrics instrumentation and Spring Boot behind the same reverse proxy.
An optional direct Spring Actuator target showed the additional health and
runtime context available from application integration.

![Express dashboard showing separate HTTP error bursts and a latency rise followed by recovery.](screenshots/express-recovery.png)

*HTTP monitoring through Caddy with steady traffic, deliberate errors, slower
responses and recovery. The final request-count drop marks the workload ending.*

- **[Detailed experiment report](report.md):** setup, methodology, verified measurements, all three dashboards and limitations.
- **[Reproduction guide](reproduction-guide.md):** prerequisites, build, fresh-history startup, workload and shutdown.
- **[Recorded evidence](evidence/)** and **[verification script](scripts/check-article.py)**.
- **[Screenshots and paired API snapshots](screenshots/README.md)**.
- **[Application sources](express/)**, **[Spring source](spring/)**, **[Caddyfile](Caddyfile)**, **[StatLite configuration](statlite.yaml)** and **[scripts](scripts/)**.
- **[Website article](https://pvrlabs.xyz/articles/monitoring-applications-behind-caddy.html):** a practical introduction for existing Caddy users.

The experiment used StatLite **v0.6.2-dev**. Caddy support was subsequently
included in **0.7.0**. The reproduction guide pins the actual tested source
revision.

Verify the recorded data with Python 3 alone, from this directory:

```sh
python3 scripts/check-article.py evidence
```

For authoritative monitoring setup, see the [Caddy guide](https://github.com/PVRLabs/statlite/blob/main/docs/targets/caddy.md)
and [Spring guide](https://github.com/PVRLabs/statlite/blob/main/docs/targets/spring.md).
