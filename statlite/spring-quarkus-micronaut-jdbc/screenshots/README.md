# Operator dashboard screenshots — 2026-10-02

Original PNGs supplied by the operator, preserved without editing. Dashboard
uses the 1h view. App last-poll labels indicate approximately 12:37 PM Pacific
(19:37 UTC); exact screenshot capture times were not supplied. These images
precede the planned end of the shared observation at approximately 12:48 PM.
Dashboard access was enabled around 12:35 PM and recorded in guest evidence.

- `host-resources.png`: self-monitoring host RAM, CPU, and disk. The RAM step
  near 12:33 PM coincides with launching all three apps for the shared phase.
- `micronaut.png`: individual run followed by the shared-phase restart.
- `quarkus.png`: individual run, unavailable interval, then shared-phase restart.
- `spring-boot.png`: individual run, unavailable interval, then shared-phase restart.

Runtime-memory charts show JVM runtime memory, not independently sampled Linux
process RSS. Sawtooth patterns are consistent with allocation and garbage
collection, but these images alone do not establish GC events. Request charts
show the busier scripted interval and subsequent return to baseline. Differences
in collected request counts require endpoint/instrumentation review before
interpreting them as workload differences.

All three app cards show UP and zero current poll failures. Spring DB health
is “Not reported”; this is not a database-failure observation. Latency increases
after shared-phase restart are visible, particularly for Spring; phase-specific
request populations and startup/warmup differ, so these are descriptive evidence
rather than a controlled latency ranking.
