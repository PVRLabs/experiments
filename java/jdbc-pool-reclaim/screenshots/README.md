# Dashboard screenshots, run1007a

These three images were reconstructed after the recording. StatLite storage was copied to a separate inspection directory, and the two application processes were started again with no workload. The charts show the recorded interval, about 10:43–11:01 AM Pacific on 7 October 2026. The UP, start, and restart cards are the later inspection processes.

| File | What it shows |
| --- | --- |
| `pool-a.png` | Pool A's request rate, latency, JVM runtime memory, and process CPU |
| `pool-b.png` | Pool B's longer bursts on the same dashboard |
| `statlite-host-resources.png` | Host RAM, CPU, and disk for the whole VM |

The screenshots do not show PostgreSQL connection counts or PostgreSQL cgroup memory. Those results are in `results/run1007a/`. The host RAM chart includes both JVMs, PostgreSQL, and monitoring, so its dips are not the 29 MiB PostgreSQL result.

**DB health: Not reported.** The fixture disabled Spring's DB-health contributor so a health poll would not borrow a pooled connection during the idle windows. The applications checked the database at startup.

The three visible Pool A HTTP 5xx spikes came from startup health checks returning HTTP 503, not HTTP 500. At 10:52:21, 10:55:13, and 10:58:05 AM Pacific, StatLite recorded `/actuator/health` as `OUT_OF_SERVICE` during startup of reclaim-2, no-reclaim-2, and default-2; each returned to `UP` on the next poll, two seconds later, with the 5xx counter increased by one. Retained Prometheus samples confirm 503 responses on health endpoints. StatLite includes these requests in its HTTP totals. Earlier startup 503s were already present in the first counter baseline and therefore did not appear as spikes. All 2,280 measured workload requests returned HTTP 200; the 12 warmup requests also returned HTTP 200.
