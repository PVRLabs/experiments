# Reanalysis and new reproductions

Run commands from this experiment directory. Analysis needs only Python 3;
building requires JDK 25 and Maven. No third-party Python packages are needed.

## Recompute the recorded results

```sh
python3 reanalyze.py
python3 checks/test_evidence.py
```

The first command regenerates each `analysis.json` and the three comparison
JSONs from included OS CSV, raw HTTP JSONL, phases, readiness and final-state
evidence. It validates main-run completeness/order/boot independence, fixed
inputs, request/state success, sampling coverage and no-swap/OOM evidence.
Run it in a copy or inspect Git diff afterward if preserving original reports
is important. It does not launch applications, access a VM, or query private data.

For one run or a diagnostic incomplete matrix:

```sh
python3 analyze.py results/measured/20261019T204216Z-javalin-mybatis
python3 compare.py --partial results/measured/20261019T204216Z-javalin-mybatis
```

`--partial` permits diagnostic output; it never marks an incomplete matrix
complete or supplies complete ranges. Recorded SQLite integrity success is
included as JSON; the omitted raw SQLite database cannot be rechecked here.

## Build the measured implementations

```sh
mvn -f javalin-jdbi3/pom.xml package dependency:tree -DoutputFile=dependencies.txt
mvn -f javalin-mybatis/pom.xml package dependency:tree -DoutputFile=dependencies.txt
mvn -f javalin-jooq/pom.xml package dependency:tree -DoutputFile=dependencies.txt
python3 checks/inventory.py
python3 checks/verify.py
```

The modules include exact measured application source and fixtures. JARs are
`<module>/target/<module>-1.0.jar`. Inventory writes `reproduction-inventory.json`,
separate from the archived `evidence/measured-build-inventory.json`. Rebuilt
ZIP timestamps/JDK details may change binary hashes; do not attribute archived
results to a changed source or artifact. Functional checks use fresh storage
under ignored module `target/` paths, exercise fixture rollback/recovery and
HTTP/metrics/restart behavior, and need free local sockets. `--variant mybatis`,
`--variant jdbi3` or `--variant jooq` limits `checks/verify.py` for triage.

jOOQ's POM uses `jooq-codegen-maven:3.21.9` with H2 2.4.240 and the included
schema DDL during `generate-sources`. Six schema files are regenerated under
`target/generated-sources/jooq`. `generated-schema/` preserves a snapshot for
inspection, not a second compilation source root. Review regenerated code
against that snapshot; DDL changes are changed experiment inputs.

## Prepare a new VM reproduction

**Exact original VM recreation is currently unavailable.** The measurements
used a locally cloned Alpine guest whose original image is no longer available.
Use a separately provisioned Alpine 3.24.2 x86_64 guest with JDK 25.0.4+7-alpine-r0,
Bash, curl, tar, OpenSSH, sha256sum, sudo, ps/pgrep/getconf, and one CPU/512 MiB,
then disclose any runtime/image differences from the recorded environment.
No unverified replacement image URL or host-specific image path is supplied.

The four `tools/` helpers preserve the shared Lima workflow (macOS Intel,
Lima 2.2+ VZ/plain mode). For a new verified image, create a Lima YAML specifying
`minimumLimaVersion: 2.2.0`, `vmType: vz`, `arch: x86_64`, `plain: true`,
`cpus: 1`, `memory: 512MiB`, `disk: 4GiB`, and its verified image location/digest.
Provision installed tools/runtime outside measurement. Record any changes;
do not claim equivalence if the pinned packages or image cannot be obtained.

Download StatLite v0.6.0's linux_amd64 binary from its
[release](https://github.com/PVRLabs/statlite/releases/tag/v0.6.0), verify the
release archive checksum, inspect/extract it, and supply its executable to the
bundle tool. Expected binary SHA-256:
`d95290cb37270d303460ad02489befa7efe8e9f091a650eca9a821eac2555f91`.
This checksum verifies an external artifact, not ordinary files stored in Git.

After the builds and checks above, use new names throughout:

```sh
python3 prepare-bundle.py reproduction-001 --statlite /tmp/statlite-linux-amd64
# Supply your own verified/provisioned YAML as described above.
tools/vm.sh create javalin-512-new /tmp/verified-alpine-512.yaml
tools/vm.sh start javalin-512-new
tools/vm.sh exec javalin-512-new sudo sh -s < setup-guest.sh
tools/prepare.sh javalin-512-new prepared-bundles/reproduction-001 /opt/sql512/reproduction-001 results/preparation/env-new
```

`setup-guest.sh` verifies Alpine, removes swap fstab entries, disables active
swap and prepares the experiment directory. It does not install/upgrade Java
or reconstruct the missing image. `prepare-bundle.py` compiles repository and
fixture checkers and records new source/JAR identities in its own preparation
record. `tools/prepare.sh` deploys into a new guest path, verifies artifact
checksums and captures environment. Preparation is outside measured execution.

Open the app tunnel in a persistent terminal:

```sh
tools/vm.sh tunnel javalin-512-new 18080 8080
```

In another terminal, run a short isolated smoke:

```sh
python3 run.py javalin-mybatis --vm javalin-512-new --release /opt/sql512/reproduction-001 --preparation prepared-bundles/reproduction-001/preparation.json --smoke
```

Repeat smoke for Jdbi and jOOQ, with their own variant arguments; verify
repository/fixture checks before isolated headroom measurements using the
guest `check` action with a newly created separate preparation directory.
Also smoke monitored mode before the measured series: open the 19090→9090
monitor tunnel and add `--monitored --smoke`. Smoke monitoring stops normally;
its optional dashboard inspection is not a gate. Never reuse preparation output
as result data or run preparation work concurrently with a measured variant.

## New measured series

Before **each** measured run, close tunnels, stop/start the guest, wait for
startup, then recreate the app tunnel. Check time, no swap/competing app/monitor,
fixed artifacts and settings. Keep the physical host awake. Use fresh databases
(the runner creates new run directories) and the same new preparation record
for the entire series.

```sh
python3 run.py javalin-jdbi3 --vm javalin-512-new --release /opt/sql512/reproduction-001 --preparation prepared-bundles/reproduction-001/preparation.json
```

Repeat in order Jdbi/MyBatis/jOOQ, then jOOQ/MyBatis/Jdbi, with a reboot before
every invocation. Defaults are the recorded 30 s baseline/idle/recovery and
1,500 requests at 5/s. No StatLite during these six runs. The runner records
actual resources and boot ID, verifies deployment checksums/preparation identity,
collects results and exits unsuccessfully on invalid evidence. Preserve completed
runs and diagnose failed phases rather than rerunning valid data unnecessarily.
Do not overwrite or edit the archived measured run directories.

After all six, compare them with `python3 compare.py <six-new-run-directories>`.
Present measurements and code/setup tradeoffs, then obtain explicit operator
selection for one monitored candidate. The archived selection was MyBatis;
any new selection should be recorded rather than inferred from that history.

For the selected monitored repeat, reboot/reset again, open both tunnels and
record the rationale (substitute the new explicit operator selection):

```sh
tools/vm.sh tunnel javalin-512-new 19090 9090
python3 run.py javalin-mybatis --vm javalin-512-new --release /opt/sql512/reproduction-001 --preparation prepared-bundles/reproduction-001/preparation.json --monitored --selection 'Operator rationale for this reproduction'
```

The runner pauses at cutoff with services running. Verify guest port 9090 and
host `http://127.0.0.1:19090/`, give actual phase times and the one-hour view,
and wait for operator inspection completion or explicit skip. Label post-cutoff
status as live inspection. After confirmation, finish using the same VM/release:

```sh
python3 run.py javalin-mybatis --vm javalin-512-new --release /opt/sql512/reproduction-001 --preparation prepared-bundles/reproduction-001/preparation.json --finish results/measured/NEW_RUN_DIRECTORY
```

Close the exact tunnels afterward. Stop the VM if no longer needed, preserving
its guest evidence. `--finish` stops services before collecting monitoring
storage. New raw H2/SQLite databases and logs are local archives, not intended
public Git artifacts. A full measured series was not rerun during curation;
public reanalysis of the archived evidence was verified independently.
