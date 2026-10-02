# Reproducing the experiment

Reanalyze existing measurements without a VM or Java:

```sh
python3 analyze.py
```

For a new run, use included `model-app` sources, fixture, `bundle.sh`, `runner.py`,
and pinned `vm.yaml`. The application README documents the shared contract.
This reproduces the procedure; fresh builds and a different host can yield
different artifacts and results. Preserve new hashes and environment details.

## Recorded environment

- Host: Intel Core i9-9980HK, macOS 15.6.1, 32 GiB RAM.
- Lima 2.2.0, VZ x86_64, Ubuntu 24.04, 2 vCPUs, 1 GiB RAM, 6 GiB disk, no swap.
- Ubuntu release-20260705 image, SHA-256
  `ffe6203da54deeb6db5d2a98a83f9ec8e55f149d3f7ba622e1abe5fa966ee3d6`.
- Temurin 25.0.4.1+1-LTS Linux x64; archive SHA-256
  `dbb698396d478e7fa2b1e50f4103324b2a99b90569ee27c33f2261f9215cf41e`.
- JVM flags: `-Xms32m -Xmx192m -XX:+UseG1GC -XX:ActiveProcessorCount=2`.
- StatLite feature candidate `4220d5fd0bbd3a07fea72eb46c2461e92b96f9f1`,
  Go 1.27.1, Linux amd64 binary SHA-256
  `cf537068441797cc16c2cce918ee4f5429a2b5bdec087df5ed249fd9493b5d58`.

The feature candidate was pre-release dogfooding, not a released StatLite version.
It may not be obtainable from a public checkout. A later public release is a
changed input: record its identity and label the run accordingly. No StatLite
binary or JDK archive is redistributed here.

## Preparation and execution

1. Install Java 25 and Maven on a build machine. In each of `model-app/spring-app`,
   `model-app/quarkus-app`, and `model-app/micronaut-app`, run `mvn package`.
   Keep the complete Quarkus `target/quarkus-app` directory.
2. Prepare a Linux amd64 StatLite binary. If building from available source,
   use `GOOS=linux GOARCH=amd64 go build -o /tmp/statlite ./cmd/statlite` in
   its repository and record the revision, Go version, and binary hash.
3. Run `bash bundle.sh /path/to/linux-amd64/statlite /tmp/jdbc-bundle-new`.
   The output directory must be new. This packages apps, fixture, and runner.
4. Create a Linux guest from the supplied Lima configuration. Install the exact
   JDK at `/opt/jdbc-jdk` (or specify `--java`), confirm no swap, check host/guest
   clock agreement, and transfer the bundle to a new persistent guest directory.
   Generate and verify a SHA-256 manifest before starting. Record the resolved
   guest configuration, runtime versions, and application/dependency hashes.
5. Confirm ports 8081–8083, 8090, and 9090 are free. Launch in a persistent guest
   shell/service, with a new output path:

   ```sh
   python3 -u /path/to/bundle/runner.py \
     --bundle /path/to/bundle --output /path/to/new-results
   ```

The default duration is 900 seconds per window. The runner first checks each
app and StatLite integration using separate preparation databases/storage,
then launches new JVMs for the timed windows. A shorter `--duration` is rehearsal
only. The fixture stays running with its default 60-second replay. Its fixed
starting position changes across sequential runs; do not reset it between them.
Each app polls on startup and every 60 seconds after completion using a common
JDK scheduled executor. Browser/API behavior, SQL, and fixture data are shared;
framework HTTP, JSON, and JDBC integration implementations differ naturally.

StatLite listens on guest loopback 9090, sampling targets every 10 seconds in
measurement (2 seconds in smoke). Process RSS sampling is every 5 seconds and
collector status sampling every 10 seconds. Readiness is external health UP
plus an initial persisted three-row batch, with a 30-second launch timeout.

Each individual 15-minute window requests latest/history sequentially every
5 seconds, increased to every second in minutes 7–10. After those runs, all
three start with fresh databases and run for 15 minutes with no scripted traffic.
Normal synchronization and metrics/health polling continue.

`inspection-ready.txt` marks the end of measurement. The runner deliberately
keeps apps alive afterward. Record subsequent browser access separately; stop
the runner and its children cleanly before collecting databases. The recorded
run opened the dashboard during the shared window; that deviation is disclosed
in the result. Preserve all completed phases if a later phase fails.
