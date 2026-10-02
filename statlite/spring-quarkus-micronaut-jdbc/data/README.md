# Curated evidence

These files preserve the observations used in the experiment result while
omitting private raw databases, process arguments, service journals, and host
account paths. Timestamps use UTC; screenshot labels use Pacific time.

| File | Contents |
| --- | --- |
| `process-memory.csv` | Five-second timed-window RSS in KiB and guest available memory; 180 sample times per phase |
| `cpu-buckets.csv` | The 13 selected 60-second CPU buckets per phase and series; explicit denominator |
| `requests.csv` | All 1,914 individual-window scripted requests, durations, response sizes, success flags |
| `collector-status.csv` | Ten-second collection statuses for all configured targets, including stopped apps |
| `fixture-positions.csv` | Fixture availability and replay position at timed process sample times |
| `summary.json` | Original calculated summary, readiness timings, initial/final batches, and interval RSS statistics |
| `deployed-artifact-sha256.txt` | Frozen application/fixture/StatLite payload SHA-256 hashes, excluding the superseded initial runner |
| `deployed-artifact-verification.txt` | Successful reverification of the retained run-02 payload before measurement |
| `runner-artifact-verification.txt` | Deployed runner hash and verification |

RSS CSV includes the three applications as present, StatLite, and the fixture.
Preparation, readiness-only samples, window-end snapshots, and subsequent
operator inspection samples are excluded. RSS distributions include the first
three minutes designated warmup. CPU selection excludes startup/boundary buckets:
include timestamps >= window start + 60 seconds and < window end - 60 seconds.
CPU fields are percent of one core for applications and percent of the two-core
VM for the host. They must not be added directly.

`summary.json` includes final H2 file sizes. Individual files were closed after
their own timed phase. Shared-phase files stayed open through operator
inspection until 20:49:42 UTC; their sizes describe that later shutdown, not the
15-minute shared observation. Its final batches come from the timed endpoint
snapshots. First-batch metadata identifies different replay starts (0, 15, 30
for individual runs; 45 for the shared starts).

Timing: individual windows started at 18:47:39, 19:02:42, and 19:17:45 UTC;
shared observation started at 19:32:55 UTC and ended at 19:47:55 UTC.
Dashboard access began around 19:35 UTC. Screenshot last-poll labels are around
19:37 UTC; exact capture times were not supplied. Operator dashboard access
during the shared window may affect StatLite self HTTP metrics. Shared-window
scripted request count was zero.

One initial active-app error status per individual window, and one initial
Micronaut error in the shared window, precede successful collection. Inactive
target errors are intentional; health fields can retain earlier observations.
No fixture availability loss/replay regression was recorded, and the captured
kernel journal contained no OOM messages. Those statements come from private
raw logs/observations; the timed fixture and collector CSVs expose the relevant
public continuity evidence. Clean shutdown and SQLite integrity checks were
recorded during wrap-up.

Run `python3 ../analyze.py` to recompute the headline values. Included source
is the clean Market Replay source snapshot from private source revision
`30aa0502ecc8cb555c4574613fcd2237bb7f3ce0`; this records provenance, not a
claim that rebuilding today produces byte-identical JARs. Frozen JAR hashes
identify the actual measured artifacts. The public package manifest is separate
from these original deployment hashes.
