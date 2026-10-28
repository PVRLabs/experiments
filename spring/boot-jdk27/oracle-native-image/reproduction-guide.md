# Oracle native follow-up reproduction

Use the same hinted Market Replay source, Boot 4.1.1 and dependencies, database
schema/configuration and fixture included here. The compiler is Oracle GraalVM
25.0.4+7.1 (Java build 25.0.4+7-LTS-jvmci-b01), selected by explicit operator
override. The comparison baseline is the independently published HotSpot 27 F
run. This is not a native executable based on JDK 27.

On a separate Ubuntu 24.04 x86_64 builder with Maven, GCC and zlib development
headers, set JAVA_HOME to that verified GraalVM installation and prepend its bin
directory to PATH. From the app directory, build with production defaults:

```sh
mvn -B -ntp -Djava.version=25 -DskipTests -Pnative clean native:compile
```

Retain the executable and any emitted lib*.so files from target together.
The recorded build used a six-GiB/two-vCPU builder, populated Maven cache, default
optimization 2, x86-64-v3, Serial GC and built-in ML-inferred profiles. No custom
PGO or optimization sweep was used. See results/build.json and compiler excerpt.

Deploy the complete package to a separate Ubuntu 24.04 x86_64 VM with 512 MiB,
one vCPU, no swap, UTC and local MariaDB. Apply mariadb-small.cnf, restart MariaDB,
and initialize schema.sql with reset-db.sh (its explicit confirmation is required).
Do not build inside the runtime budget. Use the unchanged minute-by-minute fixture,
Hikari min/max 1/4 and native runtime -Xmx80m with TZ=UTC.

Before measurement, run the application's functional suite on the actual package:
feed deserialization/API/UI, late SQL insert rollback with earlier attempts audited
outside InnoDB, connection release, timeout/database recovery, persistence, UTC
microsecond mapping and restart. The retained functional.json records observations;
the compact public package does not independently reconstruct these live checks.
Use separate test state. Smoke all launch/collection/workload/analysis/shutdown
commands with 2/2/12/2-second phases before the full run.

For measurement, stop the builder, fresh-boot the runtime, restart MariaDB and
reset only the measured schema. Launch after fixture readiness; time health UP
plus three persisted quotes at approximately 50 ms polling. Then use 60 seconds
idle, 120 warm-up, 300 traffic and 60 recovery. Offer five alternating latest/history
requests per second from the host over loopback SSH forwarding, four in flight,
no retries. Run collect-runtime.py in the runtime guest and workload.py on the
host; their --help describes arguments. Sample OS every second and metrics every
ten seconds; StatLite and periodic explicit DB probes stay off. Summarize with
summarize-runtime.py. Each phase needs its recorded phase label; exclude transitions.

For saved-data verification, on the host from this evidence directory:

```sh
python3 analyze.py
```

The analyzer uses only curated files to recheck OS RSS/CPU, host memory, swap/OOM,
request percentiles and outcomes, process identities and ingestion. Startup timing,
functional success and compiler reports are retained observations. Historical F is
an offline snapshot of the linked published baseline; no HotSpot rerun is implied.
Single measurements on separate boots/dates do not estimate variability, capacity,
long-term reliability or isolated compiler effects. Equal heap guards do not imply
equal memory layouts; process RSS and host MemAvailable are separate observations.

## Prepare the dedicated runtime host

Use Ubuntu 24.04 x86_64 and the versions/budgets in [the results](README.md).
Install MariaDB and Python 3, fix OS and DB UTC, disable swap for this dedicated
experiment, and apply `mariadb-small.cnf`. Keep the app and DB within 512 MiB.
The runtime needs no installed JDK. Copy this package's fixture and collector
beside each other; place the complete native payload in a separate directory.

`reset-db.sh` drops and recreates **market_replay** and grants a loopback user
with an empty password for this isolated test VM. Run it only on the dedicated
runtime VM with no app running, with schema.sql beside it.

**Runtime VM — working directory: its copy of the evidence package:**

```sh
cd /path/to/native-evidence
sudo systemctl restart mariadb
sudo bash reset-db.sh --confirm-experiment-reset
```

This is a local reproduction configuration, not a production credential policy.
Confirm the packaged application ingests quotes, exposes DB health and serves
UI/latest/history before a long run. Test actual transaction failure/recovery and
platform-specific mapping when validating a new artifact. The exact supplemental
fault-injection runner is archived rather than included here; the functional
summary describes the preserved checks and results, not a newly replayed test.

## Collect a new runtime run

Smoke the commands with short phases and separate output first. Reboot before an
accepted run and verify the complete payload; that warms filesystem pages. Reset
DB outside startup timing. Use fresh output/database state, leaving old evidence
intact. The collector launches and stops only its own app/fixture, enforces a
safety deadline and refuses existing output. It uses ports 8080 and 8090; confirm
they are free before launch.

Use three terminals for collection. Keep the first two running while the
third sequences the phases.

**Terminal 1, host — any working directory.** Establish an SSH tunnel before
starting the collector:

```sh
ssh -N -L 18088:127.0.0.1:8080 user@experiment-vm
```

**Terminal 2, runtime VM — working directory: its copy of the evidence package.**
Open an SSH shell into the runtime VM if needed, then run the collector there.
Both `--bundle` and `--output` are paths inside the runtime VM:

```sh
cd /path/to/native-evidence
python3 collect-runtime.py --bundle /path/to/native-payload \
  --output /path/to/native-runs/run-new --max-seconds 900
```

The collector verifies fixture readiness, times native startup, samples raw
process/host evidence, and writes `ready.json` when health and persistence pass.

**Terminal 3, host — working directory: the host copy of the evidence package.**
Wait for the guest ready.json, then sequence phases and run the external driver.
`NATIVE_RUN` is the runtime VM's output path from Terminal 2; the workload
`--output` paths are on the host. All `ssh` invocations below run from the host:

```sh
cd /path/to/native-evidence
NATIVE_GUEST=user@experiment-vm
NATIVE_RUN=/path/to/native-runs/run-new
until ssh "$NATIVE_GUEST" test -f "$NATIVE_RUN/ready.json"; do sleep 1; done
ssh "$NATIVE_GUEST" "printf idle > '$NATIVE_RUN/phase'"
sleep 60
ssh "$NATIVE_GUEST" "printf warmup > '$NATIVE_RUN/phase'"
python3 workload.py --base http://127.0.0.1:18088 --seconds 120 --rate 5 --output /tmp/native-warmup-new
ssh "$NATIVE_GUEST" "printf workload > '$NATIVE_RUN/phase'"
python3 workload.py --base http://127.0.0.1:18088 --seconds 300 --rate 5 --output /tmp/native-load-new
ssh "$NATIVE_GUEST" "printf recovery > '$NATIVE_RUN/phase'"
sleep 60
ssh "$NATIVE_GUEST" touch "$NATIVE_RUN/stop"
```

Check guest errors rather than waiting indefinitely for ready.json. Stop and
preserve evidence if a workload command fails.

**Terminal 2, runtime VM — after the collector exits, stay in its evidence-package
root** and summarize the raw guest output:

```sh
python3 summarize-runtime.py /path/to/native-runs/run-new
```

**Runtime VM:** export symbol counts and ordered AAPL cycle/index rows from its
local MariaDB; require ten rows per symbol and batches 0–9. Inspect kernel logs,
host pressure, graceful shutdown and process/listener cleanup there.

**Host:** retain the workload outputs from Terminal 3 and copy the raw collector
output from the runtime VM before projecting it. Close the exact tunnel with
Ctrl-C in Terminal 1, then stop the runtime VM using your VM manager. Retain workload
outputs on the host and raw collector output as separate records.
These manual SSH steps reproduce the phase method;
the recorded run used the private shared VM helpers for orchestration and export.
Reanalysis `analyze.py` checks the distributed curated dataset, not arbitrary new
raw collector output. The OS CSV projects host MemAvailable/swap/PSI/OOM counters, DB cgroup bytes,
and process PID/start ticks, CPU ticks and RSS from each sample. Request CSVs
retain index, path, epoch, status, success, latency and dispatch lag. Preserve
phase labels and units when projecting a new run; keep its results separate.
