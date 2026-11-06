# Reproduce or reanalyze

The checked-in CSV/JSON is sufficient for reanalysis with Python 3. From this
experiment directory, run `python3 analyze.py results/RUN_DIRECTORY` for each
recorded run. Analysis rewrites derived analysis.json, leaving raw samples intact;
use a copy if you want to preserve the checked-in reports unchanged.

## Build and deploy

Recorded host: Intel macOS with Lima/VZ, one-vCPU Alpine x86-64 guest. Other
platforms have not been validated. Install a Java 25 JDK, Maven, Python 3, Bash,
OpenSSH, curl, tar and shasum on the host. Maven downloads CoilBase preview 3
from its published PVR Labs repository. Do not silently replace preview 3 or
the pinned runtime/image if reproducing this environment; record changes if
old downloads are unavailable.

```sh
mvn clean verify
mkdir -p downloads
curl -fL -o downloads/statlite.tar.gz https://github.com/PVRLabs/statlite/releases/download/v0.6.0/statlite_0.6.0_linux_amd64.tar.gz
curl -fL -o downloads/statlite.tar.gz.sha256 https://github.com/PVRLabs/statlite/releases/download/v0.6.0/statlite_0.6.0_linux_amd64.tar.gz.sha256
```

Verify the archive against the release checksum, inspect it with `tar -tzf`,
and extract its `statlite` executable to `downloads/`. The measured binary's
SHA-256 is `d95290cb37270d303460ad02489befa7efe8e9f091a650eca9a821eac2555f91`.

```sh
python3 prepare.py prepared-bundles/reproduction-001 --statlite downloads/statlite
tools/vm.sh create coilbase-256 vm.yaml
tools/vm.sh start coilbase-256
tools/vm.sh exec coilbase-256 sudo sh -s < setup-guest.sh
tools/prepare.sh coilbase-256 prepared-bundles/reproduction-001 /opt/vps256/coilbase-release-001 results/preparation/env-reproduction-001
```

Extraction happens on the host. It verifies Spring classes/resources and library
bytes against the built executable JAR and checks CoilBase's library inventory.
Deployment verifies the entire transfer. Rebuilt JAR metadata can differ from
recorded binaries; the source, pinned dependencies and behavior are the useful
reproduction inputs. `evidence/runtime-inputs.json` identifies measured binary
packages; binaries and databases are not distributed here.

## Smoke, reset and measure

Open separate persistent terminals for the app and monitoring tunnels:

```sh
tools/vm.sh tunnel coilbase-256 18080 8080
tools/vm.sh tunnel coilbase-256 19090 9090
```

Smoke each variant using fresh state:

```sh
python3 run.py spring --smoke --vm coilbase-256 --release /opt/vps256/coilbase-release-001 --manifest prepared-bundles/reproduction-001/artifact-manifest.json
python3 run.py coilbase --smoke --vm coilbase-256 --release /opt/vps256/coilbase-release-001 --manifest prepared-bundles/reproduction-001/artifact-manifest.json
```

Analyze each new preparation directory. Smoke checks launching, workload,
monitoring, collection, contract behavior, shutdown and reopening. The additional
host command `python3 smoke.py prepared-bundles/reproduction-001 results/preparation/local-reproduction-001`
checks both packages, including rollback after a conflict on the third symbol.
Preparation results are not measured data.

Before each measured variant, close those exact tunnels, stop/start the VM,
reopen tunnels, and use `tools/vm.sh inspect coilbase-256` to verify no Java or
StatLite processes and near-zero swap. Preserve existing result directories.
Keep the host awake (`caffeinate -i` on macOS in a separate terminal) and avoid
other heavy host work. Hash verification reads release files before the baseline;
this is not cold-disk startup.

Run the same command without `--smoke`; initial recorded order was Spring then
CoilBase. It records baseline 60s, monitor-only 90s, startup, idle 180s, 1,500
requests over 300s, and recovery 120s. At cutoff it leaves services available.
Inspect the dashboard at http://127.0.0.1:19090/ if desired. Inspection was
explicitly skipped for the recorded runs. Stop writers and collect completed
storage before analysis:

```sh
python3 run.py spring --finish results/NEW_SPRING_RUN
python3 analyze.py results/NEW_SPRING_RUN
```

Reset before the CoilBase run, then finish/analyze with `coilbase`. Do not copy
live SQLite as final evidence. Public evidence omits monitoring databases,
operator/private environment captures, generated binaries and incidental logs.
Public reproduction covers the two measured applications.
