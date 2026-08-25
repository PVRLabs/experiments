# Alpine 256 MiB deployment kit

This directory contains the fixed deployment and measurement kit for the
Alpine Linux follow-up described in the parent experiment.

The tested shape was:

- Alpine Linux 3.24 on x86_64
- one vCPU and a nominal 256 MiB VPS; the guest exposed 216.9 MiB
- 512 MiB swap enabled before package installation and service startup
- Alpine `openjdk25-jre-headless`, OpenJDK 25.0.4
- StatLite `v0.3.0` Linux amd64 release
- two unprivileged OpenRC services: `stars` and `statlite`
- loopback-only application listeners

The tested Spring JVM profile was:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

The scripts deliberately verify the Java package, Java version, StatLite
version, binary architecture, and StatLite SHA-256 before installing the
services. The exact binary used in the preserved run had SHA-256:

```text
553d6539659759380aaec6a9b0a3e050ecbea59f989b5101b1bd0dd30ce403a4
```

Provisioning requests the exact Alpine package version
`openjdk25-jre-headless-25.0.4_p7-r0`. Alpine package repositories are
mutable; if that version is no longer available, configure the guest to use a
repository snapshot or package archive containing it. Do not remove the pin
and silently substitute a newer JDK, because that would be a separate run.

## Provision

Build the application outside the constrained guest and provide the fat JAR
and matching StatLite binary as inputs. On Alpine, as root:

```sh
./provision.sh /path/to/stars.jar /path/to/statlite-linux-amd64
```

The script installs runtime packages, creates dedicated service users and
directories, enables swap if none is active, installs the OpenRC services, and
leaves both services stopped for inspection.

Start the services after capturing the initial state:

```sh
rc-service stars start
rc-service statlite start
rc-status
```

## Observe

Run the observer from the host after both services are healthy:

```sh
SSH_TARGET=root@example-vps \
SSH_PORT=22 \
./observe-60m.sh
```

It performs a preflight, records independent Linux snapshots, sends the same
bounded endpoint workload used by the preserved run, and captures service
logs and kernel diagnostics at the end of the one-hour window.

The public repository intentionally does not include the raw observation
logs, VM identifiers, SSH details, or private execution diary. The curated
result is summarized in the parent [`EXPERIMENT.md`](../EXPERIMENT.md).
