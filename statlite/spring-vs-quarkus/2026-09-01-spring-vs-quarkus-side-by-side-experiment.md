# Spring Boot, Quarkus, and StatLite side-by-side experiment

Status: executed; qualified success for the health-enabled 2026-09-01 comparison; 2026-09-02 continued observation failed on Spring OOM; curated public package

Execution journal:
[`2026-09-01-spring-vs-quarkus-side-by-side-journal.md`](2026-09-01-spring-vs-quarkus-side-by-side-journal.md)

## Public package

This export is deliberately curated. It includes the two application source
trees, the VM and observation scripts, service units, StatLite configuration,
the detailed report and journal, the article draft, three 24h screenshots, and
selected text checkpoints. SQLite databases, disposable replay copies, verbose
service logs, credentials, and machine-specific artifacts remain private.

The controlled one-hour measurements remain authoritative and are not merged
with the later operational findings. The selected public result files are
listed in [`results/README.md`](results/README.md).

## Objective

Run the equivalent `springboot-stars` and `quarkus-stars` applications side by
side on one constrained Multipass VM, monitor both applications and StatLite
itself with one StatLite process, and preserve enough evidence to publish a
reproducible PVRLabs experiment and supporting article.

The primary questions are:

1. Can the two JVM applications and StatLite remain operational together for
   one hour on a 512 MiB VM?
2. What are the Spring Boot, Quarkus, StatLite, and combined process footprints
   at settled idle, after polling, after bounded traffic, and after one hour?
3. Can StatLite collect useful framework-specific metrics from Spring Boot and
   Quarkus while also presenting host CPU, memory, and disk through its
   self-monitoring target?
4. What resource, restart, swap, storage-growth, or polling differences appear
   under the same runtime and application workload?

This is a constrained deployment and monitoring experiment. It is not a
throughput benchmark, a native-image comparison, or a claim that the two
frameworks expose identical metrics.

## Fixed experiment configuration

- Multipass VM: `statlite-svq-512`.
- Ubuntu 24.04 LTS, with the exact image and release recorded in the journal.
- 512 MiB configured RAM, with guest-visible memory recorded separately.
- 1 vCPU and 5 GiB disk.
- 256 MiB persistent swap, created before runtime package installation and
  retained throughout the observation.
- One exact JDK 25 distribution and build for both applications.
- Spring Boot 3.5.5 in JVM mode on `127.0.0.1:8080`.
- Quarkus 3.39.1 in JVM mode on `127.0.0.1:8081`.
- StatLite `v0.4.0-dev` from the exact Git commit recorded in the journal, on
  `127.0.0.1:9090`.
- Seven-day StatLite retention, 30-second polling, and a 10-second poll timeout.
- Both applications use the same repository list and five-minute GitHub poll
  interval.
- All services bind to loopback and are accessed from the host through
  Multipass or an SSH tunnel.

The configuration label in results and publication material is:

```text
512 MiB RAM / 256 MiB swap / JDK 25 / two Xmx80m JVMs / StatLite
```

Do not combine this result with the historical 256 MiB, 300 MiB, or 512 MiB
single-application results.

## Common JVM profile

Both Spring Boot and Quarkus must receive the final JDK 25 profile used by the
256 MiB Alpine experiment:

```text
-Xms16m
-Xmx80m
-Xss256k
-XX:+UseSerialGC
-XX:TieredStopAtLevel=1
-XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

Do not use the applications' current `-Xmx64m` development launcher defaults.
Do not include `-XX:MaxRAM=192m`; that setting belonged to the separate 300 MiB
Ubuntu experiment. Record the effective command line for each JVM before the
observation starts.

Framework-specific server settings remain fixed and visible in the captured
configuration. Spring uses its bounded Tomcat settings, and Quarkus uses its
bounded Vert.x and worker-pool settings. They are not presented as equivalent
knobs.

## Application equivalence and isolation

- Use `PVRLabs/statlite`, `PVRLabs/aibadger`, and
  `scriptella/scriptella-etl` in both applications unless the journal records a
  deliberate replacement.
- Prefer a deterministic local GitHub API fixture. If the live GitHub API is
  used, provide a token through the service environment and never write it to
  a journal, result file, process listing, or publication artifact.
- Keep the five-minute application polling interval identical.
- Keep HikariCP and Agroal at minimum 1 and maximum 4 connections.
- Use separate service users, working directories, logs, and H2 files:

  ```text
  /opt/spring-stars/data/starsdb
  /opt/quarkus-stars/data-quarkus/starsdb
  ```

- Fail preflight if the canonical database paths overlap.
- Disable the Spring H2 console with
  `--spring.h2.console.enabled=false` or an equivalent experiment-specific
  property.
- Do not add a Quarkus H2 console extension or console route.
- Verify that `/h2-console` returns exactly one final `404` on each application
  port when redirects are followed. Any `2xx`, `3xx`, `401`, `403`, or other
  response means that the route is present or the check is inconclusive.

The applications may use idiomatic framework components, but functional
differences that affect the workload or resulting dashboard must be recorded
in the journal.

## StatLite targets

The deployed `statlite.yaml` should contain:

```yaml
server:
  listen: "127.0.0.1:9090"

storage:
  sqlite_path: "/var/lib/statlite/spring-vs-quarkus.sqlite"
  retention_days: 7

polling:
  interval: "30s"
  timeout: "10s"

targets:
  - name: "spring-stars"
    type: "spring"
    url: "http://127.0.0.1:8080/actuator"
    metrics_source: "prometheus"

  - name: "quarkus-stars"
    type: "quarkus"
    url: "http://127.0.0.1:8081/q/metrics"

  - name: "statlite-self"
    type: "statlite-metrics"
    url: "http://127.0.0.1:9090/statlite/metrics"
```

Spring uses its Prometheus source for application metrics while retaining
Actuator health collection. The Quarkus target collects StatLite's supported
request, duration, process CPU, heap, process-start, and optional uptime
concepts, plus Quarkus SmallRye aggregate health when `/q/health` is
available. Its datasource readiness check is normalized into
`db_health_status`. The `statlite-self` target is the authoritative source for
the VM host CPU, memory, and StatLite SQLite-filesystem data.

Use the current StatLite `v0.4.0-dev` development build. This experiment
depends on the Quarkus integration introduced for StatLite 0.4.0, so older
releases, including `v0.3.x`, must not be used. Record the exact Git commit
used for the run. Artifact hashes are intentionally omitted from this curated
public package.

## Experiment files

```text
spring-vs-quarkus/
  2026-09-01-spring-vs-quarkus-side-by-side-experiment.md
  2026-09-01-spring-vs-quarkus-side-by-side-journal.md
  README.md
  provision.sh
  snapshot.sh
  observe-60m.sh
  statlite.yaml
  services/
    spring-stars.service
    quarkus-stars.service
    statlite.service
  springboot-stars/
  quarkus-stars/
  results/ (selected text evidence)
  screenshots/
    spring.jpg
    quarkus.jpg
    selfmon-part2.jpg
```

Uncompressed runtime databases, WAL files, Maven targets, service logs, and
disposable replay copies should remain ignored. SQLite databases from the
completed observations are retained with the private experiment and are
intentionally omitted from this public package.

## Phase 1: build and verify host artifacts

The checkboxes below preserve the planned procedure. The execution results,
corrections, and final evidence are recorded in the journal and selected result
summaries in this public package.

Progress:

- [ ] Build and test the Spring Boot application.
- [ ] Build and test the Quarkus application.
- [ ] Build the StatLite `v0.4.0-dev` artifact and record its exact commit.
- [ ] Verify artifact names and sizes, then stage the deployable artifacts on the host.

Build outside the constrained VM:

```sh
cd ../springboot-stars
mvn-lite test
mvn-lite -DskipTests package

cd ../quarkus-stars
mvn-lite test
mvn-lite -DskipTests -Dquarkus.analytics.disabled=true package
```

Record the commands, compact test summaries, artifact names, and sizes in the
journal. Stage the Spring executable JAR and the complete Quarkus
`target/quarkus-app/` runner tree on the host for transfer after the VM is
provisioned. The Quarkus runner JAR by itself is not the deployable
application.

Build the Linux StatLite `v0.4.0-dev` artifact from the selected commit and
verify its version before enabling its service. Record the exact commit in the
journal.

## Phase 2: create and provision the VM

Progress:

- [ ] Create the fresh `statlite-svq-512` VM with 512 MiB RAM, 1 vCPU, and 5 GiB disk.
- [ ] Record the initial VM identity, image, memory, disk, and filesystem state.
- [ ] Create and enable exactly 256 MiB of persistent swap before package installation.
- [ ] Provision runtime packages, service users, directories, and service units without starting services.

Create a fresh VM rather than resizing or reusing a previous experiment VM:

```sh
multipass launch 24.04 \
  --name statlite-svq-512 \
  --cpus 1 \
  --memory 512M \
  --disk 5G
```

Record the complete `multipass info` output before provisioning. Create and
enable exactly 256 MiB of persistent swap before installing the JDK and other
runtime packages. Record `free -h`, `swapon --show`, `df -h /`, the Ubuntu
release, kernel, and architecture before and after provisioning.

Provision only runtime packages in the VM. Create unprivileged `spring-stars`,
`quarkus-stars`, and `statlite` users; install artifacts under `/opt`; place
configuration under `/etc/statlite`; and place writable data under the owning
service's directory. Transfer the staged Spring and Quarkus artifacts and the
StatLite artifact into the VM during this phase, after the destination
directories and ownership have been created.

Provisioning installs and enables service units but does not start them.

## Phase 3: preflight and startup

Progress:

- [ ] Verify VM resources, JDK 25, StatLite `v0.4.0-dev`, JVM flags, paths, and listeners.
- [ ] Verify both H2-console routes are exactly one final `404` with no redirects.
- [ ] Start Spring, Quarkus, and StatLite in the documented order and record readiness.
- [ ] Verify all required endpoints and all three StatLite targets before starting the clock.
- [ ] Review preflight evidence and record any corrections before timed observation.

Before starting the timed run, check and record:

- 512 MiB configured RAM and the observed guest-visible amount;
- exactly 256 MiB configured swap;
- adequate filesystem headroom;
- the expected Ubuntu, architecture, Java, and StatLite identities;
- identical effective JVM flags for both applications;
- distinct canonical H2 database paths;
- H2 consoles absent on both application ports;
- writable application and StatLite data directories;
- loopback-only listeners;
- zero service restarts before the measured startup.

If an important invariant is wrong, fix it before starting the clock and add
the correction to the journal. A minor warning can remain part of the run when
it is clearly recorded and does not make the comparison ambiguous.

Start services in this fixed order:

1. `spring-stars.service`;
2. `quarkus-stars.service`;
3. `statlite.service`.

For each service, record the command, start timestamp, time to readiness, main
PID, restart count, effective command line, first successful application poll,
and settled RSS. Quarkus readiness is verified through its dashboard,
`/q/metrics`, and `/q/health`. The original fixture omitted SmallRye Health;
the health-enabled rerun added `quarkus-smallrye-health` and verified that
StatLite records both `health_status` and `db_health_status`.

Before starting the one-hour clock, verify:

```text
200  http://127.0.0.1:8080/
200  http://127.0.0.1:8080/actuator/health
200  http://127.0.0.1:8080/actuator/prometheus
200  http://127.0.0.1:8081/
200  http://127.0.0.1:8081/q/metrics
200  http://127.0.0.1:8081/q/health
200  http://127.0.0.1:9090/
200  http://127.0.0.1:9090/healthz
200  http://127.0.0.1:9090/api/summary
200  http://127.0.0.1:9090/statlite/metrics
exactly one final 404, no redirects  http://127.0.0.1:8080/h2-console
exactly one final 404, no redirects  http://127.0.0.1:8081/h2-console
```

Use this redirect-aware assertion in preflight and preserve its complete output
in `preflight.txt`:

```sh
assert_h2_console_absent() {
  endpoint="$1"
  headers="$(mktemp)"
  if ! curl -sS --max-time 5 --location \
      --dump-header "$headers" --output /dev/null "$endpoint"; then
    cat "$headers"
    rm -f "$headers"
    return 1
  fi
  cat "$headers"
  if awk '$1 ~ /^HTTP\// { count++; if ($2 != 404) bad=1 }
      END { exit (count == 1 && bad == 0) ? 0 : 1 }' "$headers"; then
    printf 'H2 console absent: %s\n' "$endpoint"
    rm -f "$headers"
    return 0
  fi
  printf 'H2 console exposed or check inconclusive: %s\n' "$endpoint" >&2
  rm -f "$headers"
  return 1
}

assert_h2_console_absent http://127.0.0.1:8080/h2-console
assert_h2_console_absent http://127.0.0.1:8081/h2-console
```

The StatLite summary must list `spring-stars`, `quarkus-stars`, and
`statlite-self`, each with a successful poll. For the health-enabled rerun,
the Quarkus record must include `health_status: UP` and
`db_health_status: UP`.

## Phase 4: fixed one-hour observation

Progress:

- [ ] Start the host-owned observation clock after preflight review.
- [ ] Capture the settled, post-poll, bounded-traffic, and post-workload checkpoints.
- [ ] Record endpoint results, process/resource snapshots, target polling, and application polling.
- [ ] Capture the +60-minute checkpoint, service journal, and kernel evidence.

The host-side `observe-60m.sh` owns the clock and writes one timestamped result
directory. Start the clock only after the operator has reviewed the recorded
preflight and resolved material problems.

Required checkpoints are:

1. `preflight.txt` before the observation;
2. `side-by-side-settled.txt` at the start of the clock;
3. `after-several-polls.txt` at approximately +90 seconds;
4. `bounded-traffic.txt` immediately after that checkpoint;
5. `after-workload.txt` at approximately +3 minutes;
6. `end-of-60-minute-observation.txt` at +60 minutes;
7. Private `services-journal.txt` and `kernel-tail.txt` after the final
   checkpoint; publish only the selected evidence appropriate for the curated
   result package.

The bounded workload is sequential and fixed. It exercises both application
dashboards, Spring health and metrics, Quarkus metrics, the StatLite dashboard,
StatLite health, all three StatLite target dashboard API views, and StatLite
self metrics. Record every HTTP status and URL. Do not include concurrency or
an unbounded load generator.

Each snapshot records at minimum:

- VM identity, release, kernel, architecture, uptime, and load;
- guest memory, available memory, swap configuration, and actual swap use;
- root filesystem headroom;
- Spring, Quarkus, StatLite, and combined RSS, VSZ, CPU, elapsed time, and
  command lines;
- systemd state, PIDs, start timestamps, exit status, and restart counts;
- Spring H2, Quarkus H2, and StatLite SQLite sizes;
- endpoint checks and StatLite target polling status;
- recent service logs and kernel OOM evidence where applicable.

## Health-enabled rerun

The original run was repeated after adding `quarkus-smallrye-health` to the
Quarkus fixture. The rerun used the existing `statlite-svq-512` VM, preserved
the previous live StatLite database and application directories, and deployed
fresh Spring, Quarkus, and Linux StatLite artifacts. Its timed result is
`results/observation-20260901-190650/`.

The timed clock ran from `2026-09-01T19:06:52-0700` through the +60-minute
checkpoint at `2026-09-01T20:06:52-0700`. All required endpoint checks returned
HTTP 200, including `/q/health`; both H2 console checks returned exactly one
final 404; and all three services reported `NRestarts=0`. The final StatLite
target records showed Spring `UP/UP`, Quarkus `UP/UP`, and StatLite self
`UP/UP` for `health_status/db_health_status`. The direct final Quarkus payload
contained `Database connections health check: UP` with `<default>: UP`.

The final checkpoint recorded 452 MiB guest-visible RAM, 221 MiB swap used,
Spring RSS 62956 KiB, Quarkus RSS 159740 KiB, StatLite RSS 14208 KiB, and
combined RSS 236908 KiB. The StatLite data directory measured 4.0M because it
also contained preserved prior-run backups. The Quarkus process remained
healthy despite the
live unauthenticated GitHub API returning rate-limit 403 responses during
application poll cycles. The result is therefore a qualified success, with
the upstream API limitation documented in the journal.

The SQLite backup passed `PRAGMA quick_check` and is retained with the private
experiment. The public package uses the selected text checkpoints and report
instead of publishing the database.

Result hierarchy:

```text
Health-enabled rerun
  -> authoritative final comparison
  -> final Spring/Quarkus memory footprint
  -> final supported health behavior

Earlier one-hour run
  -> supporting viability evidence

Memory-residency follow-up
  -> supporting explanation of RSS/swap dynamics
  -> not the final framework comparison
```

The periodic snapshot helper used for this rerun retained the earlier
endpoint list and therefore did not include `/q/health` in every intermediate
snapshot. Quarkus health was verified separately during preflight and bounded
traffic, directly through SmallRye Health, and continuously through StatLite's
recorded `health_status` and `db_health_status`. This does not affect the
process memory measurements.

## Phase 5: one-hour memory residency follow-up

The first run established that both JVM applications and StatLite can remain
operational together for one hour. This deliberately narrow follow-up answers
one question: why did Quarkus fall from approximately 136 MiB to 85 MiB RSS
while Spring rose from approximately 109 MiB to 142 MiB?

This is a follow-up on the same VM, not a fresh-VM reproduction. Do not
reprovision or retune anything. Reuse the same VM, binaries, JDK, JVM flags,
service configuration, ports, swap, polling intervals, and StatLite
`v0.4.0-dev` commit. Preserve the first result directory exactly as-is.

Before the follow-up:

- [x] Optionally provide an authenticated GitHub token through the service
  environment without writing it to the repository, journal, logs, or process
  artifacts. (Not provided; the live unauthenticated API was retained.)
- [x] Stop all three services and record that the first run is preserved.
- [x] Start fresh Spring, Quarkus, and StatLite processes in the same order.
- [x] Record the same-VM identity and unchanged runtime configuration.

Extend `snapshot.sh` only with the following Spring and Quarkus process
measurements:

```text
/proc/<pid>/status: VmRSS, VmSwap, RssAnon, RssFile
/proc/<pid>/smaps_rollup: Rss, Pss, Pss_Anon, Pss_File, Swap, SwapPss
```

Keep the existing process RSS, JVM heap from StatLite, guest memory, total swap,
service state, and filesystem measurements. Do not add GC logging, JFR, perf,
heap dumps, or other instrumentation.

Use the same small bounded request sequence as Phase 4. The follow-up
checkpoints are:

1. [x] settled after startup;
2. [x] approximately +90 seconds;
3. [x] approximately +3 minutes;
4. [x] approximately +15 minutes;
5. [x] approximately +30 minutes;
6. [x] +60 minutes.

The extra 15- and 30-minute checkpoints are intended to show when residency
starts changing. No additional workload is required beyond the bounded
sequence.

Summarize the follow-up with this compact comparison:

| Metric | Spring settled | Spring 60m | Quarkus settled | Quarkus 60m |
| --- | ---: | ---: | ---: | ---: |
| RSS | 114308 KiB | 157808 KiB | 148016 KiB | 85448 KiB |
| PSS | 108050 KiB | 152049 KiB | 141748 KiB | 79683 KiB |
| VmSwap | 102804 KiB | 67516 KiB | 29504 KiB | 93076 KiB |
| Pss_Anon | 102068 KiB | 148164 KiB | 136324 KiB | 76244 KiB |
| Pss_File | 5982 KiB | 3885 KiB | 5424 KiB | 3439 KiB |
| JVM heap used | 43591048 bytes | 50348152 bytes | 27974608 bytes | 33094312 bytes |

Interpretation:

- RSS down, PSS down, and swap low indicates genuine memory shedding or
  decommitment.
- RSS down with VmSwap or SwapPss up indicates Linux moved cold Quarkus memory
  out of RAM, producing a smaller resident working set without necessarily a
  smaller total footprint.
- A substantial heap decline indicates JVM or GC behavior contributes.
- Similar heap with changing RSS or PSS indicates native, non-heap, or
  file-backed residency dominates.

The follow-up must not rewrite or merge the first result. Store its raw output
under a separate `results/memory-residency-YYYYMMDD-HHMMSS/` directory and
label its conclusion as a follow-up to the original qualified run.

## Post-observation update: approximately four hours later

At 2026-09-01T16:09:25-07:00 (2026-09-01T23:09:25Z), approximately four hours
after the Phase 5 processes started, the same VM was still running all three
services. The later snapshot recorded 452 MiB guest-visible RAM, 353 MiB used,
99 MiB available, 215 MiB swap used, and a 0.07/0.10/0.09 load average.
Spring was 128556 KiB RSS / 122510 KiB PSS, Quarkus 106888 KiB RSS /
100821 KiB PSS, StatLite 12312 KiB RSS, and the combined process RSS was
247756 KiB. The latest successful StatLite polls immediately before the
snapshot were Spring at 16:09:14.483 PDT, Quarkus at 16:09:09.943 PDT, and
StatLite self at 16:09:08.055 PDT. All nine health, dashboard, and metrics
endpoint checks returned HTTP 200; systemd reported `NRestarts=0` for every
service. Application data directories were 48 KiB for Spring and 36 KiB for
Quarkus; the StatLite data directory was 1.6 MiB.

The capture and database timestamps were preserved explicitly for correlation:

| Event | PDT | UTC |
| --- | --- | --- |
| Evidence capture started | 2026-09-01 16:09:23 | 2026-09-01 23:09:23 |
| VM/process snapshot | 2026-09-01 16:09:25 | 2026-09-01 23:09:25 |
| Evidence capture finished | 2026-09-01 16:09:26 | 2026-09-01 23:09:26 |
| SQLite backup and gzip file mtime | 2026-09-01 16:09:49.524405809 | 2026-09-01 23:09:49.524405809 |
| Gzip staged for transfer | 2026-09-01 16:09:49.666409888 | 2026-09-01 23:09:49.666409888 |

The backup passed `PRAGMA quick_check` at the recorded backup point. The
database snapshot and complete capture remain private; the public package
retains the surrounding text evidence in the selected result directories.

The service journal through the snapshot records intermittent upstream
failures at 13:45, 13:55, 14:10, 15:36, and 15:54 PDT (rate limiting,
timeout, and connection reset). The applications remained running and later
poll cycles recovered; these events are application/upstream behavior rather
than VM or process restarts.

## Running VM update: 2026-09-02

A fresh read-only snapshot of the still-running `statlite-svq-512` VM was taken
at 2026-09-02T09:00:37-07:00. The VM has 452 MiB guest-visible RAM and 256 MiB
swap. Memory pressure is high: 418 MiB RAM is used, only 33 MiB is available,
and 255.9 MiB of swap is used. Root storage is 80% full, with 782 MiB
available. The one-minute, five-minute, and fifteen-minute load averages were
1.84, 1.52, and 1.27 on the single vCPU.

| Process | RSS | PSS | VmSwap | JVM/application heap sample |
| --- | ---: | ---: | ---: | ---: |
| Spring Boot | 163344 KiB | 160855 KiB | 49664 KiB | 48683800 bytes JVM heap |
| Quarkus | 99936 KiB | 97443 KiB | 71740 KiB | 25907984 bytes JVM heap |
| StatLite | 4680 KiB process RSS | not collected | not collected | 1449320 bytes runtime heap |
| Spring + Quarkus RSS | 267960 KiB | not applicable | not applicable | not applicable |

Both application processes are running with the same constrained JVM profile
(`-Xmx80m`, SerialGC, compact object headers). Spring currently has the larger
resident and proportional footprint. Quarkus has the smaller RSS and PSS, but
more of its process is swapped out. The combined application RSS is 261.7 MiB,
so the two applications account for most of the guest's resident memory before
the guest cache and other services are included.

Spring and Quarkus were restarted by systemd at approximately 07:58 PDT on
2026-09-02, while StatLite has remained up since 2026-09-01T19:06:29-07:00.
All three services are active, report `NRestarts=0`, and the nine checked
application, dashboard, health, and metrics endpoints returned HTTP 200.
The latest StatLite polls in this snapshot were successful with health and
datasource health both `UP`:

| Target | Latest poll | Poll ID | Status |
| --- | --- | ---: | --- |
| `spring-stars` | 2026-09-02T09:00:26 PDT | 1704 | `ok / UP / UP` |
| `quarkus-stars` | 2026-09-02T09:00:21 PDT | 1703 | `ok / UP / UP` |
| `statlite-self` | 2026-09-02T09:00:18 PDT | 1702 | `ok / UP / UP` |

The live database was backed up separately at approximately 08:59 PDT and
passed `PRAGMA quick_check`. It remains private. The existing screenshot
captures use a disposable replay of that earlier history and are documented in
the journal; the VM continued polling after the backup.

## Restart and memory-pressure finding: 2026-09-02

The 07:58 PDT event was not a VM reboot. `journalctl --list-boots` shows a
single boot continuing from 2026-09-01. The applications were restarted as
services within that boot.

At 07:56:50 PDT, Ubuntu `unattended-upgrades` began installing pending system
updates. During that activity, the 512 MiB guest exhausted both memory and
swap. At 07:57:35 PDT, the kernel reported a global OOM condition with only
204 KiB of swap free and killed the Spring JVM, PID `11557`, which had a
245.0 MiB service memory peak and 156.6 MiB of swap peak. The
`spring-stars.service` unit then scheduled its configured `Restart=on-failure`
recovery at 07:57:40 PDT.

The same unattended-upgrade run subsequently invoked needrestart. Its dpkg log
explicitly requested:

```text
systemctl restart fwupd.service packagekit.service polkit.service
quarkus-stars.service rsyslog.service spring-stars.service ssh.service udisks2.service
```

This explains the Quarkus restart. The original Quarkus process exited with
status 143 at 07:58:19 PDT and systemd started a replacement. Spring was also
gracefully stopped by that service-restart pass at 07:58:30 PDT after its OOM
recovery process had started, then launched again. StatLite remained running.

This is a failed run condition for the constrained VM: the workload exposed
that unattended package maintenance can consume enough memory to trigger an
OOM kill and then recycle both application services. The earlier snapshot's
`NRestarts=0` values are not evidence that no restart occurred; the journal and
unit exit records are authoritative for this incident.

## Follow-up Spring OOM: 2026-09-02 09:40 PDT

After the updated StatLite binary was installed and `statlite.service` was
restarted at 09:36:15 PDT, Spring encountered another guest-wide memory
shortage. At 09:40:09 PDT, the kernel killed Spring PID `14992` and systemd
recorded an `oom-kill` failure. The service had reached a 201.5 MiB memory peak
and a 119.3 MiB swap peak during this instance.

Systemd scheduled the configured `Restart=on-failure` recovery at 09:40:15
PDT. Spring completed startup at 09:41:13 PDT. StatLite's 09:40:46 poll
occurred while port 8080 was unavailable and recorded two consecutive
`connection refused` failures, so the dashboard temporarily showed Spring as
unknown. The first successful post-restart poll at 09:41:16 PDT recorded:

```text
status=ok, health_status=UP, db_health_status=UP
poll_id=1949, app_run_id=7, restart_detected=process.start.time changed
http_requests_total=3, http_404_total=0, http_4xx_total=0, http_5xx_total=0
```

This confirms that the unknown state was a transient, correctly recorded
polling outage caused by Spring's OOM restart. It was not caused by the new
Quarkus collector or by StatLite failing to parse metrics. The VM remains
memory-constrained and this follow-up is additional failed-run evidence.

## Continued maintenance pressure: 2026-09-02 09:55 PDT

A later read-only check showed that the maintenance episode was still active.
The guest had 411 MiB of its 452 MiB visible RAM in use, only 7 MiB free and
about 40 MiB available, while 255 MiB of the 256 MiB swap was used. The
`apt-check` process was consuming approximately 70% CPU, and
`unattended-upgrades` was still running with the dpkg lock held. The package
transaction had therefore not fully cleared when this check was made.

The captured host metric also shows the scale of the change: observed host CPU
averaged about 89% after 07:55 PDT, compared with about 1.2% before that time.
Spring and Quarkus process CPU averaged only about 3% to 4% in the same
post-07:55 database samples. This supports attributing the sustained pressure
to OS maintenance and its memory-constrained side effects rather than to an
application framework comparison. Restarting the VM while the package lock is
held could interrupt `apt`/`dpkg`; a restart would only be considered after
maintenance completes and the final database is captured.

## 2026-09-02 10:57–11:59 continued observation

After maintenance pressure subsided, the VM was checked at 10:57 PDT with
0.00 load, 277 MiB available memory, and 28 MiB swap in use. Spring and
Quarkus were started with the fixed two-`Xmx80m` JDK 25 profile. Spring became
ready after its 13.917-second application startup; Quarkus became ready after
10.386 seconds. The bounded traffic checks for both applications, StatLite,
health, metrics, and dashboard endpoints all returned HTTP 200.

The observation harness ran from 10:59:09 through 11:59:18 PDT. The 3-minute
checkpoint showed 114 MiB available memory, 211 MiB swap in use, Spring RSS of
82 MiB, and Quarkus RSS of 140 MiB. The guest remained responsive with a
0.15 load average and no OOM evidence at that checkpoint.

The result directory does not present the reused Sep 1 preflight as Sep 2
evidence. It is labeled `preflight-reused-20260901.txt`; Sep 2 startup evidence
comes from the service journal, bounded-traffic output, snapshots, and kernel
log below.

At 11:40:29 PDT, the guest exhausted nearly all swap and the kernel killed
Spring PID `21155`. Systemd recorded an OOM-kill failure, a 234.5 MiB service
memory peak, and a 141.1 MiB swap peak. Only 8 KiB of swap was free in the
kernel report. `Restart=on-failure` launched Spring PID `21982` at 11:40:34;
it became healthy again by the 11:41:16 StatLite poll. StatLite recorded one
Spring health-fetch failure during the restart and then resumed successful
polling. Quarkus and StatLite did not restart.

At the final 11:59:11 checkpoint, the guest had 85 MiB available memory and
191 MiB swap in use. Spring was at 64,336 KiB RSS / 59,016 KiB PSS with
138,584 KiB swapped; Quarkus was at 163,068 KiB RSS / 157,767 KiB PSS with
17,028 KiB swapped; StatLite was at 14,808 KiB RSS. The final combined
application RSS was 242,212 KiB. All required endpoints returned HTTP 200,
and the three services were active, but Spring had `NRestarts=1`, so this is
not a successful timed run under the experiment's no-OOM/no-restart criteria.

The run also reproduced the independent external limitation: at 11:56 PDT,
Spring's GitHub poll cycle received rate-limit 403 responses for two of three
repositories. Quarkus continued successful cycles. These API failures are
classified separately from the guest OOM and did not cause a service restart.

The controlled health-enabled 2026-09-01 rerun remains the authoritative
framework comparison. This 2026-09-02 run is additional operational evidence
that the combined two-JVM workload can run for much of an hour on the VM but
does not have enough memory and swap headroom to guarantee one-hour survival.

## Database and replay boundary

Consistent SQLite backups were captured after the controlled and failed
observations and passed `PRAGMA quick_check`. They remain private because the
database is not needed to understand or reproduce the important setup and
conclusions. The public result package instead includes selected checkpoints,
kernel evidence, bounded-traffic output, and the report and journal summaries.

The existing screenshots were retained from a disposable replay of the earlier
24h history. Their provenance and limitation are recorded in the journal; they
do not represent the later Sep 2 OOM or fresh one-hour follow-up.

## Local replay and screenshots

Progress:

- [x] Copy the preserved database to a disposable local replay location.
- [x] Replay with the original target names and the captured `statlite-self` host data.
- [x] Use the existing 24h dashboard captures for the three publication views.
- [x] Record screenshot source metadata and confirm all three images are suitable supplements.

Use a disposable copy of the preserved database for local dashboard replay.
Never run local replay against the immutable backup. Keep target names exactly
the same and ensure replay does not replace the captured VM latest values with
fresh local polls, especially for `statlite-self` host data.

The publication screenshot set uses the existing 24h StatLite dashboard views
and the same target names. These captures represent history through
approximately 08:59 PDT on Sep 2, before the later OOM and fresh observation:

```text
screenshots/spring.jpg
screenshots/quarkus.jpg
screenshots/selfmon-part2.jpg
```

The corresponding dashboard states are:

```text
/?target=spring-stars&range=24h
/?target=quarkus-stars&range=24h
/?target=statlite-self&range=24h
```

The journal records the source history, source database filename, StatLite
version, selected target, range, and known capability differences. The
self-monitoring publication screenshot visibly contains the preserved VM host
data. On the Spring Boot and Quarkus views, `Runtime memory MB` is JVM heap,
not process RSS. The experiment snapshots provide process RSS/PSS
measurements. The existing Quarkus screenshot is not used to make a claim
about the meaning of its Restart card.

## Success and failure criteria

A successful timed run requires:

- both JVM applications and StatLite remain active for the full hour;
- zero unexplained service restarts or kernel OOM kills;
- successful bounded traffic for every required endpoint;
- successful StatLite polling for all three targets throughout the window;
- normal application GitHub polling or deterministic fixture polling;
- no severe sustained paging or loss of VM operability;

After the timed run, preserve the raw observation and compressed SQLite
database for later analysis and replay, then capture the screenshots as
publication supplements. A problem with database capture or screenshot work
does not invalidate an otherwise successful framework observation.

High memory or swap use alone is not failure on this deliberately constrained
machine. Failure includes service crashes, OOM kills, repeated restarts,
unbounded startup, severe sustained thrashing, inability to complete normal
application work, or loss of StatLite polling continuity.

Do not silently tune a failed run. Preserve its result directory and journal
entry first. Any changed heap, swap, JVM flag, framework setting, poll timeout,
or workload becomes a separately labelled follow-up configuration.

## Public selected result layout

```text
results/
  observation-20260901-190650/
    preflight.txt
    final-target-summary.json
    bounded-traffic.txt
    kernel-tail.txt
    controlled-checkpoint-summary.md
  memory-residency-20260901-121042/
    checkpoint-summary.md
    bounded-traffic.txt
    kernel-tail.txt
  observation-20260902-105906/
    failed-follow-up-checkpoint-summary.md
    bounded-traffic.txt
    kernel-tail.txt
```

These are selected text checkpoints and summaries. The private result archive
also contains raw run logs, service journals, database metadata, and SQLite
backups that are intentionally not part of this public export. Never rewrite a
failed or incomplete run to make it appear comparable.

## Publication target

Publish curated, reproducible material under:

```text
https://github.com/PVRLabs/experiments/tree/main/statlite/spring-vs-quarkus
```

The public package should contain both OSS application sources, provisioning
and observation scripts, service units, exact StatLite configuration, version
information, selected checkpoints, a compact comparison report, and the three
screenshots. Do not publish credentials, machine-specific SSH material, raw
service logs containing secrets, disposable databases, Maven targets, or IDE
metadata.
