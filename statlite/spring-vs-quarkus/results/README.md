# Selected result evidence

This directory is a curated public subset of the private experiment results.
It keeps the measurements needed to understand the comparison and the later
operational failure without publishing every command transcript or runtime
artifact.

## Evidence hierarchy

- `observation-20260901-190650/` is the authoritative health-enabled
  2026-09-01 controlled comparison. Its selected checkpoints, final target
  summary, bounded-traffic output, and kernel tail show the one-hour result.
- `memory-residency-20260901-121042/` is the supporting follow-up. Its settled,
  3-minute, 15-minute, 30-minute, and 60-minute snapshots explain the RSS,
  PSS, JVM heap, and swap relationship.
- `observation-20260902-105906/` is the failed constrained-VM follow-up. Its
  selected checkpoints, bounded-traffic output, and kernel tail document the
  later Spring OOM and recovery while Quarkus and StatLite continued running.

The broader Sep 2 history also includes an earlier maintenance-pressure
episode, documented in the journal. It is separate from the
`observation-20260902-105906/` result, which began after that pressure had
cleared. The same journal documents the reused Sep 1 preflight artifact and
its correction; the misleading preflight file is intentionally not part of
this public subset.

SQLite databases, database backups, verbose service journals, and disposable
replay files remain private. The report and journal provide the database
capture status, run identity, service restart chronology, package-maintenance
context, GitHub rate-limit limitation, and methodology boundaries.
