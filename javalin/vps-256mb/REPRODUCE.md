# Reproduce or reanalyze

Reanalysis needs Python 3 only. Run from this experiment directory:

```sh
python3 checks/test_cpu.py
python3 analyze.py results/run-20261008T212522Z-javalin
python3 analyze.py results/run-20261008T221334Z-spring
```

These commands use only curated CSV/JSON and the included fixture. Analysis
rewrites derived analysis.json, never raw samples. To preserve the checked-in
reports, run on a copy. SHA256SUMS can be verified with `sha256sum -c SHA256SUMS`
(or `shasum -a 256 -c SHA256SUMS` on macOS).

## Build and prepare on the host

Recorded VM execution uses Intel macOS, Lima 2.2+ with VZ/plain mode. Other
architectures/backends have not been validated. Host dependencies: Java 25 JDK,
Maven, Python 3, Bash, curl, tar, OpenSSH and shasum. Host Java is for building
and extraction; application/monitor smoke runs only inside Alpine.

From this experiment directory:

```sh
mvn package -DskipTests
mkdir bundle
cp javalin-app/target/javalin-app-1.0.jar bundle/javalin.jar
cp spring-app/target/spring-app-1.0.jar bundle/spring.jar
curl -fL -o bundle/statlite.tar.gz https://github.com/PVRLabs/statlite/releases/download/v0.6.0/statlite_0.6.0_linux_amd64.tar.gz
curl -fL -o bundle/statlite.tar.gz.sha256 https://github.com/PVRLabs/statlite/releases/download/v0.6.0/statlite_0.6.0_linux_amd64.tar.gz.sha256
```

Verify the downloaded archive's SHA-256 against the release checksum (the checksum
may name the original release filename rather than the local filename). Inspect
its file list with `tar -tzf bundle/statlite.tar.gz`, then extract the `statlite`
executable into `bundle/`. Verify that its SHA-256 is
`d95290cb37270d303460ad02489befa7efe8e9f091a650eca9a821eac2555f91`.
The other measured hashes are in [evidence/inputs.json](evidence/inputs.json).
Rebuilt Java archive metadata can differ; source/fixture hashes are recorded
separately. Do not substitute a PATH-installed monitor.

```sh
python3 bundle.py prepared-bundle
```

This invokes official tools-mode extraction and verifies every library and
application resource against the reproduction Spring executable. It records a
new manifest, rather than claiming the rebuilt archives are the original binaries.

## Set up and deploy Alpine

```sh
tools/vm.sh create javalin-256 vm.yaml
tools/vm.sh start javalin-256
tools/vm.sh exec javalin-256 sudo sh -s < setup-guest.sh
tools/prepare.sh javalin-256 prepared-bundle /opt/vps256/release-003-extracted results/preparation/env-reproduction
```

Wait for boot/SSH readiness if startup briefly refuses connections. The image
URL/SHA-512 is pinned. Runtime setup pins OpenJDK's package; old package availability
can change. If the exact pin is unavailable, record a changed reproduction input
rather than silently claiming equivalence. Current helper/sampler source is the
reviewed version; the original Javalin run used the earlier no-steal sampler.

Open each tunnel in its own persistent terminal:

```sh
tools/vm.sh tunnel javalin-256 18080 8080
tools/vm.sh tunnel javalin-256 19090 9090
```

Then smoke both complete deployments:

```sh
python3 run.py javalin --smoke
python3 run.py spring --smoke
```

Smoke uses separate fresh run directories, includes validation/rollback and
persistence reopening, then stops services and collects storage. Confirm outputs
and analyze the smoke results. Avoid browsing while measured phases run.

## Reset and measure

Stop those exact tunnels with Ctrl-C. Stop/start the VM before each measured
variant, recreate tunnels, inspect the guest and confirm swap near zero, no
Java/StatLite processes, stable clock and matching deployment checksums. Keep the
host awake with `caffeinate -i` in a separate terminal during the run.

```sh
tools/vm.sh stop javalin-256
tools/vm.sh start javalin-256
tools/vm.sh inspect javalin-256
```

After reopening tunnels:

```sh
python3 run.py javalin
```

The runner prints its new local result directory and pauses after the real
measurement cutoff, leaving monitoring/application available. Verify
http://127.0.0.1:19090/ and inspect the recorded historical window. Keep services
and tunnels available until inspection is complete or explicitly skipped. Then:

```sh
python3 run.py javalin --finish results/<new-javalin-run>
python3 analyze.py results/<new-javalin-run>
```

Close exact tunnels, reset the guest, reopen tunnels and repeat with `spring`.
For a targeted Spring-only follow-up, run only that variant after the same reset
and preparation controls. Existing successful Alpine smoke need not be repeated
unless inputs or relevant commands changed. Preserve failed phases and label
method/input deviations. Do not overwrite archived runs or collect live databases.

The recorded source intentionally retains known error-path defects; review the
[deferred fixes](checks/post-measurement/README.md) before using it beyond this
controlled experiment. Applying fixes creates a changed reproduction input.
