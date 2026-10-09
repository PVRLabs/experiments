# Reproducing the check and the run

## Reanalyze the published evidence

From this directory:

```sh
python3 analyze.py
```

The script reads `results/run1007a` only. It recomputes connection counts, PostgreSQL cgroup medians, revisit acquisition and request medians, request totals, and sample errors from `series.csv` and `requests.csv`, then compares them with `summary.csv`. It also checks that each published 10-second window has ten connection samples and two cgroup readings. A difference exits non-zero.

`series.csv` is the curated one-second record. Full Prometheus text and per-backend process lists were left in the private archive. `mechanism-check.json` keeps the aggregate counts from that check and omits the backend rows. Window bounds match the runner: initial `-10..0`, A idle while B is busy `58..68`, both quiet `118..128`, and post-revisit `134..144`, in seconds from the workload origin. Medians use the same even-count average as `scripts/summarize.py`. Connection samples are one per second. Cgroup memory was requested every fifth sample, so those windows contain two cgroup readings.

## Run it again

A new run needs JDK 25, Maven, PostgreSQL, and a Linux host where two small JVMs and PostgreSQL can run together. The recorded guest was Ubuntu 24.04, 2 vCPU, 1 GiB, swap off, Temurin 25.0.4.1+1 at a fixed path, with:

```text
-Xms32m -Xmx192m -XX:+UseSerialGC -XX:ActiveProcessorCount=2
```

Build the fixture where Maven is available, then copy the bundle to the Linux host. The `-` argument omits StatLite, so the runner finishes when measurement finishes. To include the optional dashboard, pass a Linux amd64 StatLite binary instead of `-`. The recorded binary is not in this package. Its SHA-256 is in `results/run1007a/environment.json`, the same pre-release candidate recorded in `statlite/spring-quarkus-micronaut-jdbc`.

```sh
scripts/build.sh
scripts/bundle.sh - /tmp/pool-reclaim-bundle
```

On the Linux host, as root, with a `postgres` OS account and `runuser`. Replace `ubuntu` with the non-root account that will own the Java processes. The setup script creates the role and both databases, generates a password, and writes it to a mode `0600` file. It refuses to replace an existing role, database, or config file. The published results do not contain that password.

```sh
sudo python3 /tmp/pool-reclaim-bundle/scripts/setup-postgres.py \
  --guest-user ubuntu \
  --config /etc/pool-reclaim.json \
  --port 5432
```

That file records the JDK as `/opt/jdbc-jdk/bin/java`. If the JDK is elsewhere, change only the `java` field and leave the file mode `0600`. Ports 8081 and 8082 must be free. Each output directory must not already exist. A session name is 1–20 characters from letters, digits, `_`, and `-`.

Smoke uses the separate `pool_reclaim_smoke` database and a shortened timeline. Record mode requires that smoke's preflight, including the clock and VM acknowledgement, and refuses to run if the bundle changed afterward.

```sh
sudo python3 /tmp/pool-reclaim-bundle/scripts/runner.py \
  --mode smoke \
  --session smoke1007 \
  --bundle /tmp/pool-reclaim-bundle \
  --output /var/tmp/pool-reclaim-smoke1007 \
  --config /etc/pool-reclaim.json

sudo python3 /tmp/pool-reclaim-bundle/scripts/ack-preflight.py \
  /var/tmp/pool-reclaim-smoke1007/preflight.json \
  --checked-vm-clock-and-1gib-config

sudo python3 /tmp/pool-reclaim-bundle/scripts/runner.py \
  --mode record \
  --session run1007b \
  --bundle /tmp/pool-reclaim-bundle \
  --output /var/tmp/pool-reclaim-run1007b \
  --config /etc/pool-reclaim.json \
  --preflight /var/tmp/pool-reclaim-smoke1007/preflight.json

python3 /tmp/pool-reclaim-bundle/scripts/summarize.py /var/tmp/pool-reclaim-run1007b
```

Record mode runs `default-1`, `no-reclaim-1`, `reclaim-1`, `reclaim-2`, `no-reclaim-2`, and `default-2`. Expect about 18–21 minutes. The runner checks that unset sizing resolves to 10/10, and that reclaim drops instance A to 1–2 connections while B is still at 10. It must run as root so it can read the PostgreSQL cgroup and `/proc`. Java drops to the configured guest user. The timeline and JVM flags come from `scripts/common.py`.

The host-side VM launcher used for the original session is not part of this package.

Preserve the new jar hash, Java hash, PostgreSQL settings, and summary. A different PostgreSQL build or a busier server will not reproduce the 28.5 versus 57.5 MiB cgroup values exactly. The connection counts are the mechanism check.
