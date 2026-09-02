# Spring Boot, Quarkus, and StatLite side-by-side experiment journal

Date opened: 2026-09-01 PDT

Status: qualified success for the 2026-09-01 controlled comparison; failed constrained-VM follow-up on 2026-09-02.

Plan:
[`2026-09-01-spring-vs-quarkus-side-by-side-experiment.md`](2026-09-01-spring-vs-quarkus-side-by-side-experiment.md)

This journal is the chronological operator record. Preserve commands, relevant
output, errors, retries, interventions, and decisions as they occur. Do not
replace failed output with a later successful command. Add the later command
and explain why it was required.

The original planning template below retains some `pending` placeholders. The
dated execution entries later in this journal are authoritative for what was
actually run, corrected, and observed.

## Run identity

| Field | Recorded value |
| --- | --- |
| Operator | Codex |
| Host and OS | macOS host, x86_64 |
| Multipass version | 1.16.3+mac |
| VM name | `statlite-svq-512` |
| VM image | Ubuntu 24.04.4 LTS |
| Configured RAM | 512 MiB |
| Guest-visible RAM | 452 MiB |
| vCPU | 1 |
| Disk | 5 GiB |
| Swap | 256 MiB persistent |
| JDK | Liberica JRE 25.0.4+9-LTS |
| Spring Boot | 3.5.5 |
| Quarkus | 3.39.1 |
| StatLite | `v0.4.0-dev`, `96a6cd325c27aab3137815d0794c2dc8ca9d510a` |
| Spring source commit | `e2bd34f2ec45cd8434e651dc588f495035badaac` |
| Quarkus source commit | `e2bd34f2ec45cd8434e651dc588f495035badaac` |
| StatLite source commit | `96a6cd325c27aab3137815d0794c2dc8ca9d510a` |
| GitHub source | live unauthenticated API; rate limit reached during run |
| Result directory | `results/observation-20260901-103255` |

Configuration label:

```text
512 MiB RAM / 256 MiB swap / JDK 25 / two Xmx80m JVMs / StatLite
```

Common JVM profile:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

## Versions and source notes

### Repository state

Commands:

```sh
git -C ../springboot-stars status --short
git -C ../springboot-stars rev-parse HEAD
git -C ../quarkus-stars status --short
git -C ../quarkus-stars rev-parse HEAD
git -C ../../../statlite status --short
git -C ../../../statlite rev-parse HEAD
```

Output and notes about existing worktree changes:

```text
Spring and Quarkus tests passed. Spring package and Quarkus runner tree were
built successfully. StatLite tests passed and Linux amd64 binary was built.
The first staged StatLite binary was macOS Mach-O and was rejected during
preflight; a Linux amd64 rebuild replaced it. The first provisioning attempt
had an archive-directory naming mismatch; the corrected retry succeeded.
The first service-unit retry used /usr/bin/java although the pinned JRE was
installed at /opt/jdk-25.0.4+9; units were corrected before the measured run.
Loopback binding was made explicit before the final startup.
```

### Spring build

Commands:

```sh
cd ../springboot-stars
mvn-lite test
mvn-lite -DskipTests package
```

Test output summary, artifact name, and size:

```text
PASS · 13.124 s
Packaged artifact: target/stars-0.0.1-SNAPSHOT.jar, 58 MiB.
```

### Quarkus build

Commands:

```sh
cd ../quarkus-stars
mvn-lite test
mvn-lite -DskipTests -Dquarkus.analytics.disabled=true package
```

Test output summary, runner-tree size, and transferred file list:

```text
PASS · 9.251 s
Packaged Quarkus application tree: target/quarkus-app/, 48 MiB, including
quarkus-run.jar and all dependency/lib files.
```

### StatLite `v0.4.0-dev` build

Source command, exact Git commit, version output, and artifact name:

```text
cd ../../../statlite
GOCACHE=/tmp/statlite-go-cache GOMODCACHE=/tmp/statlite-go-mod-cache \
  GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go test ./...
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o statlite ./cmd/statlite
statlite --version: statlite v0.4.0-dev
Linux amd64 artifact: 17 MiB before transfer
```

The test suite passed. The deployed artifact was a Linux amd64 build of
StatLite `v0.4.0-dev`.

Build or packaging errors and interventions:

```text
The initial host build was not Linux-compatible and was rejected in preflight
with Exec format error. It was rebuilt with GOOS=linux, GOARCH=amd64, and
CGO_ENABLED=0 before the measured run.
```

## VM creation

Command:

```sh
multipass launch 24.04 \
  --name statlite-svq-512 \
  --cpus 1 \
  --memory 512M \
  --disk 5G
```

Command output and `multipass info statlite-svq-512`:

```text
pending
```

Initial guest inspection:

```sh
multipass exec statlite-svq-512 -- bash -lc '
set -eu
cat /etc/os-release
uname -a
uname -m
free -h
swapon --show
df -h /
'
```

Output:

```text
pending
```

VM-creation errors and interventions:

```text
none yet
```

## Swap and runtime provisioning

Exact 256 MiB swap creation and persistence commands:

```text
pending
```

Pre-swap and post-swap `free -h`, `swapon --show`, and `df -h /` output:

```text
pending
```

Installed package versions and `java -version`:

```text
pending
```

Provisioned users, directories, ownership, and permissions:

```text
pending
```

Artifact transfer commands and guest-side verification:

```text
pending
```

Linux StatLite platform and version output:

```text
pending
```

Provisioning errors and interventions:

```text
none yet
```

## Effective service configuration

Preserve complete systemd units and the deployed StatLite configuration in the
result directory.

Spring command line:

```text
pending
```

Quarkus command line:

```text
pending
```

StatLite command line:

```text
pending
```

Canonical database paths and collision check:

```text
Spring: pending
Quarkus: pending
StatLite: /var/lib/statlite/spring-vs-quarkus.sqlite
Collision check: pending
```

H2 console verification. The check must follow redirects and accept only a
single final `404` response. Any `2xx`, `3xx`, `401`, `403`, or other response
means that the route is present or the check is inconclusive.

```text
Spring console configuration: pending
Quarkus console configuration: pending
Spring /h2-console redirect-aware status chain: pending
Quarkus /h2-console redirect-aware status chain: pending
```

Record the exact command and complete response headers used for both checks:

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

Configuration errors and interventions:

```text
none yet
```

## Startup chronology

### Spring Boot

Start command and timestamp, time to dashboard, health, Prometheus metrics,
and first application poll:

```text
pending
```

Main PID, restart count, effective JVM command line, settled RSS, and relevant
startup output:

```text
pending
```

### Quarkus

Start command and timestamp, time to dashboard, `/q/metrics`, and first
application poll:

```text
pending
```

Main PID, restart count, effective JVM command line, settled RSS, and relevant
startup output:

```text
pending
```

### StatLite

Start command and timestamp, time to `/healthz`, dashboard, three successful
target polls, and usable series:

```text
pending
```

Main PID, restart count, settled RSS, and relevant collector output:

```text
pending
```

Startup errors and interventions:

```text
none yet
```

## Preflight

Timestamp:

```text
pending
```

| Endpoint | Expected | Actual |
| --- | ---: | ---: |
| Spring dashboard | 200 | pending |
| Spring health | 200 | pending |
| Spring Prometheus | 200 | pending |
| Spring H2 console | exactly one final 404, no redirects | pending |
| Quarkus dashboard | 200 | pending |
| Quarkus metrics | 200 | pending |
| Quarkus H2 console | exactly one final 404, no redirects | pending |
| StatLite dashboard | 200 | pending |
| StatLite health | 200 | pending |
| StatLite summary | 200 | pending |
| StatLite self metrics | 200 | pending |

Resource state, service state, and StatLite target summary:

```text
pending
```

Preflight decision:

```text
pending: proceed or stop
```

## One-hour observation

Result directory and observation start:

```text
pending
```

### Side-by-side settled checkpoint

Timestamp and output summary:

```text
pending
```

### After several StatLite polls

Timestamp and output summary:

```text
pending
```

### Bounded traffic

Command and complete HTTP result summary:

```text
pending
```

### After workload

Timestamp and output summary:

```text
pending
```

### End of 60-minute observation

Timestamp and output summary:

```text
pending
```

| Measurement | Settled | After polls | After workload | Final |
| --- | ---: | ---: | ---: | ---: |
| Guest used memory | pending | pending | pending | pending |
| Guest available memory | pending | pending | pending | pending |
| Swap used | pending | pending | pending | pending |
| Spring RSS | pending | pending | pending | pending |
| Quarkus RSS | pending | pending | pending | pending |
| StatLite RSS | pending | pending | pending | pending |
| Combined RSS | pending | pending | pending | pending |
| Spring H2 size | pending | pending | pending | pending |
| Quarkus H2 size | pending | pending | pending | pending |
| StatLite SQLite size | pending | pending | pending | pending |
| Spring restarts | pending | pending | pending | pending |
| Quarkus restarts | pending | pending | pending | pending |
| StatLite restarts | pending | pending | pending | pending |

Application polling, StatLite polls and samples, service journal, and kernel
findings:

```text
pending
```

Observation finish:

```text
pending
```

## Error and intervention log

Add one row for every unexpected error, retry, configuration correction,
service restart, timeout, external API failure, or manual intervention.

| Time | Phase | Observation or error | Command or intervention | Result and classification |
| --- | --- | --- | --- | --- |
| See dated entries below | not applicable | The run record includes package maintenance, OOM/restarts, GitHub rate limiting, and preflight corrections. | not applicable | Classified in the relevant dated sections. |

Classify external API failures separately from VM, JVM, framework, and StatLite
failures. Preserve the original command output in the result directory.

## After-run database capture

Consistent SQLite backups were captured after the observations and passed
`PRAGMA quick_check`. They remain private and are intentionally omitted from
this public package. The public result directories retain selected checkpoints
and the journal preserves the database-capture decision without publishing
backup files, paths, or checksums.

## Local replay and screenshots

Disposable replay database path and replay StatLite build:

```text
Disposable copy of the private post-observation backup
spring-vs-quarkus-live-20260902-085809.sqlite.gz; StatLite v0.4.0-dev
```

Method used to prevent local polls from replacing preserved VM latest values:

```text
Use a disposable replay copy rather than the immutable backup. The captures
are 24h context views of the preserved experiment history and host data.
```

```text
Source history: 2026-09-01 controlled run, overnight period, and maintenance
pressure through approximately 08:59 PDT on 2026-09-02; later follow-up data
is not represented in these existing captures
Source database filename: spring-vs-quarkus-live-20260902-085809.sqlite.gz
The source backup is private and is not included in this public package.
StatLite version: v0.4.0-dev, exact commit pending
```

| Target | Dashboard state | File | Verified content |
| --- | --- | --- | --- |
| Spring Boot | `spring-stars`, `24h` | `screenshots/spring.jpg` | 24h history and JVM runtime chart visible |
| Quarkus | `quarkus-stars`, `24h` | `screenshots/quarkus.jpg` | 24h history and JVM runtime chart visible |
| StatLite self | `statlite-self`, `24h` | `screenshots/selfmon-part2.jpg` | 24h host resources and recent events visible |

The three publication captures use the 24h range because they show the Sep 1
run, overnight period, and maintenance pressure through approximately 08:59
PDT on Sep 2 in one context view. They do not represent the later 09:40 OOM or
the 10:57-11:59 fresh follow-up; those remain in the final observation result
package. `selfmon-p1.jpg` remains repository evidence but is not part of the
article's three-image set. On the Spring Boot and Quarkus views, `Runtime
memory MB` is JVM heap, not process RSS. Process RSS/PSS measurements are from
the experiment snapshots. No interpretation of the Quarkus Restart card is
published from this older screenshot source.

Screenshot issues or recaptures:

```text
none; existing 24h captures are retained for publication
```

## Phase 5 memory residency follow-up

Status: executed; qualified follow-up. The Phase 4 result directory and
compressed database remain preserved unchanged.

Follow-up identity:

| Field | Recorded value |
| --- | --- |
| VM | `statlite-svq-512`, same VM as Phase 4 |
| Configuration | unchanged from Phase 4 |
| Authenticated GitHub token | not provided; live unauthenticated API retained |
| Result directory | `results/memory-residency-20260901-121042` |

Required checkpoints:

| Checkpoint | Spring RSS/PSS | Quarkus RSS/PSS | Spring VmSwap | Quarkus VmSwap | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| settled | 114308 / 108050 KiB | 148016 / 141748 KiB | 102804 KiB | 29504 KiB | startup baseline |
| +90 seconds | 119880 / 112879 KiB | 119556 / 112544 KiB | 97312 KiB | 58712 KiB | before bounded traffic |
| +3 minutes | 122912 / 116169 KiB | 109708 / 102955 KiB | 94000 KiB | 69148 KiB | after bounded traffic |
| +15 minutes | 141528 / 136330 KiB | 96704 / 91496 KiB | 79664 KiB | 79164 KiB | |
| +30 minutes | 143016 / 134429 KiB | 101268 / 92670 KiB | 85000 KiB | 82168 KiB | |
| +60 minutes | 157808 / 152049 KiB | 85448 / 79683 KiB | 67516 KiB | 93076 KiB | final checkpoint |

Compact comparison:

| Metric | Spring settled | Spring 60m | Quarkus settled | Quarkus 60m |
| --- | ---: | ---: | ---: | ---: |
| RSS | 114308 KiB | 157808 KiB | 148016 KiB | 85448 KiB |
| PSS | 108050 KiB | 152049 KiB | 141748 KiB | 79683 KiB |
| VmSwap | 102804 KiB | 67516 KiB | 29504 KiB | 93076 KiB |
| Pss_Anon | 102068 KiB | 148164 KiB | 136324 KiB | 76244 KiB |
| Pss_File | 5982 KiB | 3885 KiB | 5424 KiB | 3439 KiB |
| JVM heap used | 43591048 bytes | 50348152 bytes | 27974608 bytes | 33094312 bytes |

Follow-up interpretation and errors:

```text
The follow-up completed from 2026-09-01T12:10:42-07:00 through
2026-09-01T13:10:49-07:00 on the existing `statlite-svq-512` VM. All six
residency snapshots completed, all 18 bounded HTTP checks returned 200, and
the three services remained active with `NRestarts=0`. The kernel tail had no
OOM-kill evidence. The same unauthenticated GitHub source again hit the
external per-IP rate limit at 12:55 and 13:00; both applications logged the
failures and recovered by 13:05 without a service failure, so this is a
qualified follow-up rather than a clean application-workload run. The bounded
traffic file contains 18 endpoint and dashboard API checks; all returned 200.

Spring RSS and PSS rose from 114308/108050 KiB settled to 157808/152049 KiB
at 60 minutes, while JVM heap rose from 43591048 to 50348152 bytes. Quarkus
RSS and PSS fell from 148016/141748 KiB to 85448/79683 KiB, while its JVM heap
rose from 27974608 to 33094312 bytes. Quarkus's final heap was still smaller
than Spring's in absolute terms (about 33.1 MB versus 50.3 MB), so heap size
can contribute to the cross-framework RSS difference. More specifically, the
Quarkus RSS decline itself was not caused by its heap shrinking: its heap grew
by about 5.1 MB while RSS fell by about 61 MiB. Its `VmSwap` also increased
from 29504 to 93076 KiB, while Spring's fell from 102804 to 67516 KiB. The
evidence points to Linux paging and non-heap/native residency behavior
contributing to the Quarkus RSS decline. This same-VM follow-up does not
isolate framework-only causes.
```

## Final result

The Phase 5 memory-residency follow-up is classified as a qualified follow-up
to the original qualified one-hour run. It preserved the original database
and result directory, completed all scheduled checkpoints, and provides
evidence that the Quarkus RSS decline coincided with increased swapping rather
than reduced JVM heap use.

## Raw evidence index

The public result directories contain selected checkpoints rather than every
capture artifact. The controlled comparison keeps its settled and final
checkpoints, final target summary, bounded-traffic output, and kernel tail.
The Phase 5 directory keeps a curated checkpoint summary plus bounded-traffic
and kernel output. The summary retains the settled and 60-minute values needed
to explain the RSS, heap, and swap relationship.
The later running-VM update and its database backup remain private. The Phase
4 final checkpoint recorded 452 MiB guest-visible RAM, 212 MiB swap used,
Spring RSS 144948 KiB, Quarkus RSS 87440 KiB, StatLite RSS 9672 KiB, and
combined RSS 242064 KiB. Final endpoint checks were all HTTP 200. The kernel
tail contained no OOM kill evidence.

Run classification:

```text
qualified success
```

Evidence-backed conclusion, article-safe observations, and limitations:

```text
The 512 MiB / 256 MiB swap / JDK 25 / two Xmx80m JVMs configuration completed
the one-hour viability observation. Spring Boot, Quarkus, and StatLite stayed
active; final endpoint checks and target-specific dashboard API views returned
200, and all timed checkpoints reported zero systemd restarts. Final combined
RSS was 242064 KiB; final data sizes were Spring H2 40K, Quarkus H2 48K, and
StatLite 328K. The compressed SQLite backup was 77K and passed PRAGMA
quick_check. The live unauthenticated GitHub API hit its rate limit from about
10:42 to 10:57 PDT, causing application poll failures before recovery. This
external API limitation qualifies the run and means the result is not a clean
application-poll success; StatLite target polling remained successful.

Operational note: both applications independently polled the same three
repositories every five minutes. Their combined request rate, plus startup
requests, exceeded GitHub's unauthenticated per-IP limit. This is a realistic
deployment failure mode: each application handled the upstream 403 responses
without crashing, retained its existing data, and recovered when the limit
window cleared. Production deployments should use an authenticated token,
coordinate polling, or provide a deterministic local fixture for comparative
experiments.
```

## Publication checklist

- [x] Both OSS application source trees selected for publication.
- [x] Runtime and framework versions recorded.
- [x] Provisioning, snapshot, and observation scripts reviewed.
- [x] Service units and StatLite configuration reviewed.
- [x] Results summary reconciled with raw checkpoints.
- [x] Errors and interventions represented accurately.
- [x] Credentials and machine-specific SSH material excluded.
- [x] Preserved `.sqlite.gz` experiment database retained privately and omitted from this package.
- [x] Three screenshots copied with metadata and captions.
- [x] Public README distinguishes framework metrics capabilities.
- [x] Article claims match the recorded run classification.

## Health-enabled rerun: 2026-09-01

The original side-by-side run was repeated after the Quarkus fixture gained
the `quarkus-smallrye-health` dependency in commit `448968e`. This rerun
specifically verifies that the Quarkus application and datasource health now
appear in the StatLite dashboard data.

### Rerun identity

| Field | Recorded value |
| --- | --- |
| VM | `statlite-svq-512`, existing running VM |
| VM address | private VM address omitted |
| VM image | Ubuntu 24.04.4 LTS |
| Configured RAM / guest-visible RAM | 512 MiB / 452 MiB |
| vCPU / disk | 1 / 5 GiB |
| Swap | 256 MiB persistent; 255 MiB visible to guest |
| JDK | Liberica JRE 25.0.4+9-LTS |
| Spring source | `dd451804eff037ec03eb35e48bfe6a068f2d1969` |
| Quarkus source | `dd451804eff037ec03eb35e48bfe6a068f2d1969` |
| StatLite source | `73e60cb4e21096ab9bfbf4dc833cba38c343ac1b` |
| StatLite version | `v0.4.0-dev` |
| Result directory | `results/observation-20260901-190650` |
| GitHub source | live unauthenticated API; rate limit reached during run |

Common JVM profile:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

### Build and deployment

Build commands:

```sh
cd ../springboot-stars
mvn-lite test
mvn-lite -DskipTests package

cd ../quarkus-stars
mvn-lite test
mvn-lite -DskipTests -Dquarkus.analytics.disabled=true package

cd ../../../statlite
GOCACHE=/tmp/statlite-go-cache GOMODCACHE=/tmp/statlite-go-mod-cache \
  go-lite test ./...
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o /tmp/svq-statlite ./cmd/statlite
```

The Spring and Quarkus Maven tests passed. The StatLite test suite passed when
run with VM-capable socket access; the host shell could not execute the Linux
binary, and the guest subsequently verified `statlite v0.4.0-dev`.

The Spring and Quarkus packages and the Linux amd64 StatLite binary were
verified before deployment. Artifact checksums are intentionally omitted from
this curated public record.

Before deployment, all three services were stopped. The first database
preservation command reported success but did not leave the expected
timestamped file, so the VM directory was rechecked and the active database
was then moved explicitly to:

```text
/var/lib/statlite/spring-vs-quarkus-previous-20260901-190412.sqlite
```

The old Spring and Quarkus application directories were also retained under
timestamped names. The first preflight failed before service startup because
the Quarkus archive had been extracted one directory too deep. The archive
contents were moved into `/opt/quarkus-stars`, the ownership was corrected,
and preflight was rerun. The rerun also emitted systemd's harmless
daemon-reload warning because deployment stopped before its daemon-reload
step; the effective service commands and artifact paths were verified in the
successful preflight.

### Preflight

The successful preflight ran at `2026-09-01T19:05:52-07:00` and is preserved
in `results/observation-20260901-190650/preflight.txt`. Every required
endpoint returned HTTP 200, including:

```text
http://127.0.0.1:8080/
http://127.0.0.1:8080/actuator/health
http://127.0.0.1:8080/actuator/prometheus
http://127.0.0.1:8081/
http://127.0.0.1:8081/q/metrics
http://127.0.0.1:8081/q/health
http://127.0.0.1:9090/
http://127.0.0.1:9090/healthz
http://127.0.0.1:9090/api/summary
http://127.0.0.1:9090/statlite/metrics
```

Both H2 console checks returned exactly one final 404. The successful
preflight summary recorded these initial StatLite results:

```text
spring-stars:  health_status=UP, db_health_status=UP
quarkus-stars: health_status=UP, db_health_status=UP
statlite-self: health_status=UP, db_health_status=UP
```

The direct Quarkus health response is preserved in
`results/observation-20260901-190650/quarkus-health-final.json` and was:

```json
{"status":"UP","checks":[{"name":"Database connections health check","status":"UP","data":{"<default>":"UP"}}]}
```

Quarkus startup logs also listed the `smallrye-health` feature. The service
PIDs were Spring `11557`, Quarkus `11624`, and StatLite `11683`, all with
`NRestarts=0`.

### Timed observation

The host-owned clock started at `2026-09-01T19:06:52-0700`. It captured the
settled, +90-second, bounded-traffic, +3-minute, and +60-minute checkpoints.
The final checkpoint was captured at `2026-09-01T20:06:56-0700`; the runner
finished at `2026-09-01T20:07:00-0700`.

The result files preserve all endpoint statuses, snapshots, target summaries,
service logs, and kernel output. The final endpoint checks all returned HTTP
200. The final StatLite records were:

```text
spring-stars:  poll_id=366, status=ok, health_status=UP, db_health_status=UP,
              consecutive_poll_failures=0
quarkus-stars: poll_id=365, status=ok, health_status=UP, db_health_status=UP,
              consecutive_poll_failures=0
statlite-self: poll_id=364, status=ok, health_status=UP, db_health_status=UP,
              consecutive_poll_failures=0
```

Final checkpoint summary:

| Measurement | Value |
| --- | ---: |
| Guest-visible RAM | 452 MiB |
| Swap used | 221 MiB |
| Spring RSS | 62956 KiB |
| Quarkus RSS | 159740 KiB |
| StatLite RSS | 14208 KiB |
| Combined RSS | 236908 KiB |
| Spring H2 data | 44K |
| Quarkus H2 data | 40K |
| StatLite data directory | 4.0M, including preserved prior-run backups |
| Spring / Quarkus / StatLite restarts | 0 / 0 / 0 |

The kernel output contains no OOM-kill evidence. Both applications continued
running when the live unauthenticated GitHub API returned rate-limit 403
responses. Successful and failed application poll cycles are retained in
the private `services-journal.txt`; this external limitation makes the run qualified
rather than a clean application-workload comparison.

### Database capture

After the timed checkpoint, a consistent SQLite backup was created as the
`statlite` user and passed `PRAGMA quick_check`. It remains private. The public
package keeps the selected text checkpoints and this journal's summary rather
than publishing the database or its checksum.

### Rerun classification

```text
qualified success
```

The rerun establishes that the updated Quarkus fixture exposes both
application and datasource health to StatLite: the dashboard data contains
`health_status=UP` and `db_health_status=UP`, backed by the direct SmallRye
Health datasource check. The one-hour VM viability result is qualified solely
by the live unauthenticated GitHub rate limit, which affected application
poll work but did not cause service failure, StatLite polling loss, restarts,
or health loss.

### Evidence hierarchy

The health-enabled rerun is the authoritative final comparison. It provides
the final Spring and Quarkus memory footprints and the final supported health
behavior. The earlier one-hour run is supporting viability evidence. The
memory-residency follow-up is supporting evidence that explains RSS and swap
dynamics on the swapped 512 MiB VM; it is not the final framework comparison.

The periodic snapshot helper used for this rerun retained the earlier
endpoint list and therefore did not include `/q/health` in every intermediate
snapshot. Quarkus health was verified separately during preflight and bounded
traffic, directly through SmallRye Health, and continuously through StatLite's
recorded `health_status` and `db_health_status`. This does not affect the
process memory measurements.

## 2026-09-02 restart and OOM finding

The 07:58 PDT service restart was investigated after the live dashboard showed
Spring and Quarkus start times near 07:59. Correction to the initial
interpretation: the VM did not reboot. `journalctl --list-boots` shows one
continuous boot from 2026-09-01; only services were recycled.

The maintenance episode was Ubuntu's automatic package maintenance, not an
application workload or StatLite activity. `unattended-upgrades` invoked
`apt` and `dpkg` to apply pending updates, including the `util-linux` family,
`zlib1g`, Perl, `cpio`, Bind9, `libssh`, PAM, and Coreutils packages. Package
post-install triggers then ran, and `needrestart` re-executed systemd and
requested restarts for services using updated system components. The observed
host CPU increase coincided with this package installation, post-install work,
and application startup sequence. The host CPU metric does not identify one
exclusive process, so the journal records the timing and mechanism without
attributing all of the CPU usage to `apt` alone.

Evidence from the VM:

```text
07:56:50  unattended-upgrades started
07:57:35  global OOM; free swap was 204 KiB
07:57:35  kernel killed Spring PID 11557
07:57:40  systemd scheduled Spring Restart=on-failure recovery
07:58:10  unattended-upgrade service-restart pass stopped both application units
07:58:19  Quarkus PID 11624 exited with status 143 and was restarted
07:58:30  recovered Spring process was gracefully stopped for the same pass
```

The kernel identified Spring as the OOM victim. At the time, the guest had
512 MiB configured RAM and 256 MiB swap, with only 204 KiB swap remaining.
The OOM report recorded Spring's 245.0 MiB service memory peak and 156.6 MiB
swap peak. The first Spring restart was therefore automatic unit recovery.

The dpkg log then recorded needrestart's explicit service list, including both
`quarkus-stars.service` and `spring-stars.service`. Quarkus was not failing on
its own at that point; it was deliberately stopped and relaunched by the
package-maintenance restart pass. StatLite was not restarted. All services
were healthy again after startup, but this remains a failed constrained-VM
run condition because an unattended upgrade caused an OOM kill and application
restarts.

## 2026-09-02 09:40 follow-up Spring OOM

After the new Linux StatLite binary was installed and `statlite.service` was
restarted at 09:36:15 PDT, Spring suffered another OOM kill:

```text
09:40:09  kernel killed Spring PID 14992; service result was oom-kill
09:40:15  systemd scheduled Restart=on-failure and started Spring
09:40:46  StatLite poll got connection refused on 127.0.0.1:8080
09:41:13  Spring completed startup on port 8080
09:41:16  first successful StatLite poll after restart
```

The kernel report recorded a 201.5 MiB Spring service memory peak and a
119.3 MiB swap peak. The 09:40:46 failed poll was during Spring startup, and
two consecutive connection failures caused the dashboard to display Spring as
unknown. The next successful poll recorded `health_status=UP`,
`db_health_status=UP`, `poll_id=1949`, `app_run_id=7`, and a
`restart_detected` event based on the changed process start time. The new
sample contained three requests and zero 404, 4xx, and 5xx responses.

This was a transient service outage caused by VM memory exhaustion. StatLite
continued running and correctly recovered Spring's status on the next
successful poll. The event is additional failed-run evidence for the
512 MiB RAM and 256 MiB swap configuration.

## 2026-09-02 09:55 continued maintenance pressure

A read-only VM check showed that Ubuntu maintenance was still active after the
Spring recovery:

```text
Guest memory: 411 MiB used, 7 MiB free, 40 MiB available
Swap:         255 MiB used of 256 MiB; 252 KiB free
CPU:          apt-check approximately 70%
Package work: unattended-upgrades still running; dpkg lock held
```

The captured StatLite self-metrics show observed host CPU averaging about 89%
after 07:55 PDT, compared with about 1.2% before 07:55. In those same
post-07:55 database samples, Spring and Quarkus process CPU averaged only
about 3% to 4% each. The high host CPU therefore coincided with the active
Ubuntu package-maintenance and restart episode, not with high application CPU
from either framework. The metric cannot identify every contributing process,
so this is recorded as maintenance-related host pressure rather than an
exclusive `apt` attribution.

The dpkg lock was still held, so restarting the VM at this point was not used.
An immediate reboot could interrupt the package transaction and cause the
maintenance to resume during boot. This check reinforces the operational
finding that the 512 MiB RAM and 256 MiB swap configuration had almost no
headroom for routine OS activity.

## 2026-09-02 10:57–11:59 follow-up observation

The package-maintenance pressure had cleared by the start check. At 10:57 PDT
the VM reported 0.00 load, 277 MiB available memory, and 27.8 MiB of used
swap. Spring and Quarkus were then started with the fixed JDK 25 profile:

```text
Spring PID 21155: service start 10:57:24 PDT; application started in 13.917s
Quarkus PID 21217: service start 10:57:42 PDT; application started in 10.386s
StatLite PID 18797: already active since 09:36:15 PDT
```

All bounded application, health, metrics, StatLite, and dashboard endpoint
checks returned HTTP 200. The observation harness ran from 10:59:09 through
11:59:18 PDT and preserved its raw output under
`results/observation-20260902-105906/`.

The directory's copied Sep 1 preflight is retained only as
`preflight-reused-20260901.txt` and is explicitly historical. It is not used
as evidence for the Sep 2 startup; the service journal, bounded-traffic file,
snapshots, kernel log, and database metadata are the relevant evidence.

The early memory pressure was high but initially stable. At the 3-minute
checkpoint the guest had 114 MiB available memory and 211 MiB used swap; Spring
was 82 MiB RSS and Quarkus was 140 MiB RSS. Load was 0.15 and there was no OOM
evidence at that checkpoint.

At 11:40:29 PDT, the kernel reported a global OOM with only 8 KiB of swap free
and killed Spring PID 21155. Systemd recorded:

```text
spring-stars.service: Failed with result 'oom-kill'
Consumed 29.068s CPU time, 234.5M memory peak, 141.1M memory swap peak
```

The configured `Restart=on-failure` recovery started PID 21982 at 11:40:34.
Spring completed startup at 11:41:12 and StatLite's next successful poll at
11:41:16 recorded the new app run and `restart_detected`. There was one
Spring health-fetch failure while port 8080 was unavailable. Quarkus and
StatLite remained running with no restarts.

Final checkpoint, 11:59:11 PDT:

| Measurement | Value |
| --- | ---: |
| Guest-visible RAM | 452 MiB |
| Available memory | 85 MiB |
| Swap used | 191 MiB |
| Spring RSS / PSS / swap | 64,336 / 59,016 / 138,584 KiB |
| Quarkus RSS / PSS / swap | 163,068 / 157,767 / 17,028 KiB |
| StatLite RSS | 14,808 KiB |
| Combined application RSS | 242,212 KiB |
| Load average (1m) | 0.23 |
| Spring / Quarkus / StatLite restarts | 1 / 0 / 0 |

All final endpoint checks returned HTTP 200. The final StatLite polls were
successful and reported `health_status=UP` and `db_health_status=UP` for all
three targets. The one-hour run nevertheless fails the experiment's strict
survival criterion because Spring was OOM-killed and restarted.

The one-hour database window contains 124 successful and 2 failed Spring
polls, 124 successful and 2 failed Quarkus polls, and 126 successful StatLite
self-polls. The application startup errors and the Spring restart account for
the recorded transient failures. At 11:56 PDT, Spring also received GitHub
rate-limit 403 responses for two repositories; this external API limitation
is separate from the VM OOM and did not restart either application.

### Follow-up database capture

After the final checkpoint, a consistent SQLite backup was created as the
`statlite` user at 12:07:24 PDT and passed `PRAGMA quick_check`. It remains
private. The backup captured the live StatLite history beyond the one-hour
cutoff, including the Spring-before-OOM, Quarkus, and Spring-after-OOM app
runs. Database files and checksums are intentionally omitted from this public
package.

### Follow-up classification

```text
failed constrained-VM run; useful operational evidence
```

The health-enabled 2026-09-01 rerun remains the authoritative framework
comparison. This follow-up demonstrates that the services can run for most of
an hour after maintenance pressure clears, but the combined two-JVM workload
still has insufficient memory and swap headroom for a guaranteed one-hour run
on the 512 MiB / 256 MiB VM.
