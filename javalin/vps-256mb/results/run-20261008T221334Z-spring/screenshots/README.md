# Operator dashboard screenshots

Original screenshots supplied by the operator after Spring measurement, before
monitor shutdown. Run: `run-20261008T221334Z-spring`. Exact capture timestamp
was not supplied; the Spring view shows last poll at 15:34:04 PDT on 2026-10-08.
Selected dashboard range: 1h. Charts include post-measurement inspection time.
Measured historical window: 22:14:34–22:26:14 UTC (15:14:34–15:26:14 PDT).
Workload: 15:19:14–15:24:14 PDT; recovery ends at 15:26:14 PDT.

- [Spring Boot](spring-boot.png): `spring` target, application request/error,
  average latency and process runtime charts. Current UP/DB-health/poll cards
  are post-cutoff inspection state. Runtime memory is a JVM metric, not RSS;
  dashboard average latency is not external request p95.
- [Host resources](host-resources.png): guest-wide host history collected by
  `statlite-self`, including RAM/CPU and disk. Use the independent OS sample
  CSV for MemAvailable, RSS, swap and CPU with I/O wait/steal separated.

Operator confirmed monitoring may stop after supplying these screenshots.
