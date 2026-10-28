# Reanalysis guide

From this directory, run `python3 analyze.py` with Python 3; no third-party
packages, database, VM or private repository are required. Keep the public
repository layout so the existing Spring F baseline is available. Native
reanalysis also reads the sibling HotSpot curated summary.

`results/experiment.json` records runtime/stack versions, deployment inputs,
method and provenance. Detailed comparison files retain accepted numeric values
without rounding. Their Spring F detail is replaced by a reference to the
existing public `/runs/F` record; native's four-way file retains comparison
values for all four configurations, not a second copy of baseline evidence.
README values use three decimals for startup, two for RSS and HTTP p95.

Each evidence directory is selected from the named accepted run:

- `memory-samples.json`: phase, guest monotonic seconds, process RSS in MiB and
  host MemAvailable in MiB projected from `guest/samples.jsonl`. MiB conversions
  match the original analyzer (proc KiB divided by 1024). Transition labels are
  retained and excluded when selecting steady phases.
- `warmup-requests.json` and `workload-requests.json`: request index, route,
  status, success, latency and dispatch lag projected from the original JSONL.
  The private runner validated response payloads before marking success.
- `readiness.json`: exact startup seconds, epoch and first persisted quotes;
  private launch paths removed.
- `history.json`: final observed history, retained as JSON.
- `validation.json`: accepted validation observations, not a new raw measurement.

The script recomputes sample counts, phase intervals, median/peak process RSS,
minimum host available memory, success counts and nearest-rank HTTP percentiles.
It checks readiness, final history, baseline differences and native optimization
calculations against accepted summaries. OOM, swap, cache, CPU continuity and
kernel observations remain accepted checks from the original analyzer; this
projection does not independently rederive them from full OS/application logs.
Native build excerpts and contract output preserve the successful MariaDB build
cost and behavior evidence; build durations are compiler-reported, not external
wall time. Failed preparation/H2 build attempts are not comparative evidence.

This package supports reanalysis, not an end-to-end benchmark rebuild. The README
records the workload, configuration and key build/training settings, but complete
application sources, pinned OS packages, fixture inputs and deployment runners
are not included. New measurements require reconstructing those inputs and
validating behavior and metadata coverage first. The accepted published numbers
should not be treated as reproducible to their displayed decimal precision.
