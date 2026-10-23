# Reproduction guide

## Run on Linux

Use a disposable Ubuntu 24.04 machine or VM with sudo, internet access, Go
1.27.1, and capacity comparable to the recorded 2 vCPU, 2 GiB RAM, 12 GiB disk
setup. Ports 80 and 443 must be free. Setup installs Node, Java, Maven and Caddy,
adds local test hostnames, and trusts a local Caddy CA in that machine only.
The apps, admin/metrics and StatLite bind loopback; only Caddy's frontend binds
public interfaces. Use this on a disposable test machine, not an existing
production reverse proxy.

From this directory, build the recorded StatLite source revision:

```sh
mkdir -p run/bin
git clone https://github.com/PVRLabs/statlite.git run/statlite-source
git -C run/statlite-source checkout a4881332e2f27a84749e568a12bd7103f64dd728
(cd run/statlite-source && CGO_ENABLED=0 go build -o ../bin/statlite ./cmd/statlite)
bash scripts/setup.sh
```

Setup pins Node 24.21.0, Express 5.1.0, Caddy 2.11.4 and Spring Boot 4.0.0.
Node/Caddy downloads are checksum-verified and Express has a dependency lockfile.
Ubuntu packages and the base image float; this is not an immutable image.
The checked-in source revision is the tested development build, not a claim
about every published StatLite release.

Optionally check the fixture before the measured workload. Stop any existing
fixture first:

```sh
bash scripts/stop.sh
bash scripts/start.sh --fresh-history
bash scripts/smoke.sh
```

That check takes a little over two minutes. The measured run below starts a
separate observation database, so smoke traffic does not enter its history.

For every measured run, stop the fixture and start with fresh history. The
`--fresh-history` option preserves the previous SQLite database and any WAL,
shared-memory or journal files under a unique ignored `run/history-*/`
directory. It refuses to archive while any recorded service PID is still live.
It does not delete previous evidence or dependency caches. Startup without this
option remains available for dashboard/history inspection.

The checker subtracts totals from rolling one-hour API windows. With reused
history, older observations could expire between snapshots and reduce that
difference, producing a false failure. Start the workload promptly after this
fresh startup and finish within one hour of startup, without other application
traffic. Repeat this stop/fresh-start sequence before each workload.

Run the ten-minute workload and its final 40-second polling wait:

```sh
bash scripts/stop.sh
bash scripts/start.sh --fresh-history
python3 scripts/article-workload.py
# Substitute the directory printed by the workload:
python3 scripts/check-article.py run/article-<UTC timestamp>
```

Each host receives one certificate-verified HTTPS request per second. Five
120-tick phases give Express ordinary 200s, missing-route 404s, deliberate 500s,
250 ms delayed 200s, then ordinary 200s again. Spring receives ordinary 200s
throughout. The harness logs every response and captures metrics at each phase
boundary using read-only APIs. Polling stays at 30 seconds.

Open `http://127.0.0.1:9090` on that machine. For a remote VM, forward its
loopback dashboard, for example `ssh -L 19090:127.0.0.1:9090 user@vm`, then use
`http://127.0.0.1:19090` on your workstation. Inspect all three targets before
stopping. Optional screenshot capture on the workstation requires Python 3 and
an installed `playwright-cli` with its browser:

```sh
bash scripts/capture-dashboard.sh express-via-caddy run/screenshots/express
bash scripts/capture-dashboard.sh spring-via-caddy run/screenshots/spring-caddy
bash scripts/capture-dashboard.sh spring-direct run/screenshots/spring-direct
```

After dashboard inspection:

```sh
bash scripts/stop.sh
```

The database, certificates, logs and rerun output remain under ignored `run/`.
Stop the VM separately if applicable.

## Verify the published evidence without a VM

From this directory, Python 3 alone is sufficient:

```sh
python3 scripts/check-article.py evidence
```

The checker verifies 600 requests per target; 120 Express 404s and 120 Express
5xx responses; no Spring errors; fresh successful polls at every phase boundary;
Express latency rise and recovery; steady Spring latency; and runtime metrics
only for Spring direct. It rewrites `evidence/assertions.json` deterministically.
The [evidence directory](evidence/) contains the complete traffic log, phase
manifest, before/final metric series and boundary collection statuses required
by this check. Selected screenshots have matching dashboard API snapshots.
Bulk intermediate captures, databases, certificates and process logs are omitted.
