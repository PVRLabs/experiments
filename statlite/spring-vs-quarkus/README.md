# Spring Boot vs Quarkus

Completed side-by-side resource and monitoring experiment for the
`springboot-stars` and `quarkus-stars` applications. Both applications and
StatLite ran on the same 512 MiB Multipass VM with JDK 25 and the final
`-Xmx80m` JVM profile used by the 256 MiB experiment.

Both H2 consoles remain disabled. One StatLite process monitors Spring Boot,
Quarkus, and itself. After the fixed one-hour observation, the StatLite SQLite
database was preserved for local replay and captured publication dashboard
screenshots.

This public package is curated rather than a complete forensic archive. It
includes the application sources, VM setup and observation scripts, service
units, StatLite configuration, selected checkpoints, and the publication
screenshots. The SQLite databases, disposable replay copies, verbose service
logs, and machine-specific credentials remain private.

The evidence hierarchy is important:

- `results/observation-20260901-190650/` is the authoritative health-enabled
  controlled comparison.
- `results/memory-residency-20260901-121042/` supports the RSS, PSS, and swap
  interpretation.
- `results/observation-20260902-105906/` is a failed constrained-VM run that
  began after the obvious package-maintenance pressure had cleared. It
  documents the fresh observation's Spring OOM/recovery and selected final
  checkpoints. The earlier Sep 2 maintenance incident is documented in the
  journal.

Operational note from the 2026-09-01 run: both applications polled the same
three GitHub repositories independently every five minutes. The combined
unauthenticated request rate exceeded GitHub's per-IP limit for part of the
hour. The applications recorded the upstream failures and continued running,
then recovered after the limit window cleared. Use an authenticated token, a
coordinated poller, or a deterministic local fixture when repeating this
comparison.

The completed experiment also includes a narrow Phase 5 memory-residency
follow-up. It reuses the same VM and configuration, adds only `/proc` RSS, PSS,
anonymous/file-backed and swap measurements, and compares Spring Boot and
Quarkus at settled, 15-minute, 30-minute, and 60-minute checkpoints.

A separate 2026-09-02 follow-up started both JVMs again after the obvious
Ubuntu package-maintenance pressure had cleared. Spring was OOM-killed about
41 minutes into that fresh observation and recovered automatically; Quarkus
and StatLite did not restart, and the final health checks were successful. This
failed constrained-VM run is preserved as operational evidence that 512 MiB
RAM plus 256 MiB swap is not a reliable configuration for guaranteeing
one-hour survival of both JVM applications.

See
[`2026-09-01-spring-vs-quarkus-side-by-side-experiment.md`](2026-09-01-spring-vs-quarkus-side-by-side-experiment.md)
for the execution plan and
[`2026-09-01-spring-vs-quarkus-side-by-side-journal.md`](2026-09-01-spring-vs-quarkus-side-by-side-journal.md)
for the chronological operator record.

The shorter article is
[`article-draft-spring-boot-vs-quarkus-512mb.md`](article-draft-spring-boot-vs-quarkus-512mb.md).

The operational approach reuses the JVM profile, snapshots, fixed observation
clock, raw-output preservation, and journaling patterns used by the related
StatLite low-memory experiments, while keeping this result independent of
those completed experiments.
