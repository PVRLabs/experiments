# Dashboard screenshots, run1007a

These three images were reconstructed after the recording. StatLite storage was copied to a separate inspection directory, and the two application processes were started again with no workload. The charts show the recorded interval, about 10:43–11:01 AM Pacific on 7 October 2026. The UP, start, and restart cards are the later inspection processes.

| File | What it shows |
| --- | --- |
| `pool-a.png` | Pool A's request rate, latency, JVM runtime memory, and process CPU |
| `pool-b.png` | Pool B's longer bursts on the same dashboard |
| `statlite-host-resources.png` | Host RAM, CPU, and disk for the whole VM |

The screenshots do not show PostgreSQL connection counts or PostgreSQL cgroup memory. Those results are in `results/run1007a/`. The host RAM chart includes both JVMs, PostgreSQL, and monitoring, so its dips are not the 29 MiB PostgreSQL result.

**DB health: Not reported.** The fixture disabled Spring's DB-health contributor so a health poll would not borrow a pooled connection during the idle windows. The applications checked the database at startup.

HTTP 5xx marks are visible on the pool dashboards. They were not reflected in the independent workload request logs, where all 2,280 measured requests succeeded, and they remain unattributed.
