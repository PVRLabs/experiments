# Javalin operator screenshots

Original PNGs supplied by the operator on 2026-10-08, preserved without edits
for a future article. Source run: `run-20261008T212522Z-javalin`.

- [Host resources from self-monitoring](host-resources-self-monitoring.png):
  StatLite's `statlite-self` target reports historical guest RAM, host CPU and
  disk usage. Visible chart window approximately 14:26–14:39 PDT.
- [Javalin target](javalin-target.png): application requests, HTTP errors,
  average latency, runtime heap memory and process CPU. The selected dashboard
  range is 1h; populated charts span approximately 14:28–14:38 PDT. The last
  successful poll shown is 14:39:22 PDT. Exact screenshot capture time is unknown.

Recorded measurement ended at 14:37:55 PDT (21:37:55 UTC). Chart points after
that cutoff belong to live inspection. Status, restart, failure and last-poll
cards describe inspection-time state, not historical health throughout the run.
Javalin database health is explicitly “Not reported”; successful SQL traffic
and final persisted-state checks provide separate database evidence.

The Javalin runtime-memory chart shows heap used, not process RSS. Request
values near 150 represent approximately 30-second polling intervals at five
requests/second. Dashboard average latency uses the adapter's millisecond
timing; external workload measurements establish p95 and maximum latency.

SHA-256:

```
fd35932607cc03ed3d72361eff52de2c54c96d227812a2f8cad12833f41eec3c host-resources-self-monitoring.png
20f8118cb7fb375c33f069bf26bc10252b2ef563ae2dba5f8cd5876a1a9544c5 javalin-target.png
```
