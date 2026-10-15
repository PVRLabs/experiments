# Reanalyze or reproduce

## Reanalyze the recorded runs

Python 3 only, from this experiment directory:

```sh
python3 analyze.py results/run-20261008T235523Z-javalin-jdbi3
python3 analyze.py results/run-20261009T011153Z-javalin-mybatis
python3 analyze.py results/run-20261009T015612Z-javalin-jooq
```

These commands overwrite derived `analysis.json`; use a copy to preserve reports.
They read only the included fixture, OS/HTTP samples, phases, probes and final
state. There is no database, service, Maven or VM dependency for reanalysis.
`python3 article-charts.py --output charts` regenerates the article's SVG charts
from these same samples, with matplotlib installed. It never runs a workload.

## Build application variants

Host prerequisites: Java 25 JDK, Maven, Python 3. From this directory:

```sh
mvn -f javalin-jdbi3/pom.xml clean package
mvn -f javalin-mybatis/pom.xml clean package
mvn -f javalin-jooq/pom.xml clean package
```

Jdbi and MyBatis source are the measured versions. The default jOOQ source has
the later fixture-atomicity correction and was not VM-measured. To rebuild the
original measured implementation without changing the corrected module:

```sh
cp -R javalin-jooq /tmp/persistence-jooq-measured
cp historical/jooq-release-002/JooqQuoteRepository.java /tmp/persistence-jooq-measured/src/main/java/lab/
mvn -f /tmp/persistence-jooq-measured/pom.xml clean package
```

Use a new destination if that temporary directory already exists. JAR filenames
are `target/<module-name>-1.0.jar`. Original artifact sizes/hashes are recorded in
`evidence/` and run manifests. Rebuilt ZIP timestamps may differ; a matching hash
is not promised. The historical rebuild record compared JAR entry contents.

jOOQ's POM runs `jooq-codegen-maven:3.21.9` during `generate-sources`, initializing
an in-memory H2 2.4.240 database from `src/main/resources/schema.sql`. It regenerates
six Java files in `target/generated-sources/jooq`. The `generated-schema/` copy is
inspection evidence, not another Maven source root. Generated-source hashes are
in `evidence/jooq-release-002/code-cost.json`. After DDL changes regenerate and
review the schema model; the result is a changed experiment input.

Original manifest paths are retained for provenance. Prefix
`vps-256mb/javalin-jdbi3/` maps to public `javalin-jdbi3/`;
`sql-persistence-256mb/` maps to this directory. For measured jOOQ source/checker
use `historical/jooq-release-002/`; `vps-256mb/` harness inputs map to this
package's top level or the separate original JDBC/Spring package. Documentation
and relocation edits change harness hashes and are not original artifact claims.

## Functional preparation

See [Jdbi commands](checks/jdbi3/README.md). For MyBatis, compile
`checks/MyBatisRepositoryCheck.java` against its shaded JAR and run
`lab.MyBatisRepositoryCheck` with a new storage directory. For corrected jOOQ,
compile `checks/JooqRepositoryCheck.java` against its shaded JAR and run
`lab.JooqRepositoryCheck` with fresh storage. Historical jOOQ uses the checker
in `historical/jooq-release-002/`. Use `javac -d <new-classes-directory>` and
`java -cp <application.jar>:<classes-directory> <checker-class> <new-db-directory>`.
Jdbi's controller check needs port 8081 free. These commands are preparation,
never measured traffic. The recorded correction check is host-only evidence.

## VM reproduction

Recorded host: Intel macOS and Lima 2.2+ VZ/plain mode. Other architectures and
backends have not been validated. Also requires Bash, curl, tar, OpenSSH and
shasum. The included shared helpers are the public JDBC/Spring helpers;
experiment-specific setup and measurement stay here.

Download and verify the released StatLite 0.6.0 linux_amd64 archive using its
[release checksum](https://github.com/PVRLabs/statlite/releases/tag/v0.6.0), inspect
its tar contents and extract the executable to `/tmp/persistence-statlite`.
The required binary SHA-256 is
`d95290cb37270d303460ad02489befa7efe8e9f091a650eca9a821eac2555f91`.
The bundle tool refuses a different monitor binary.

The example below reproduces Jdbi. Use a new VM name if `javalin-256` exists;
pass the same name with the runner's `--vm` option.

```sh
python3 prepare-bundle.py javalin-jdbi3 prepared-bundles/jdbi-new --statlite /tmp/persistence-statlite
tools/vm.sh create javalin-256 vm.yaml
tools/vm.sh start javalin-256
tools/vm.sh exec javalin-256 sudo sh -s < setup-guest.sh
tools/prepare.sh javalin-256 prepared-bundles/jdbi-new /opt/vps256/release-jdbi-new results/preparation/env-jdbi-new
```

The Alpine image URL and digest are pinned. Old runtime package availability can
change. If a pin is unavailable, record the changed input rather than claiming
an equivalent environment. VM setup and bundle building are outside measurement.

Open both tunnels in separate persistent terminals:

```sh
tools/vm.sh tunnel javalin-256 18080 8080
tools/vm.sh tunnel javalin-256 19090 9090
```

Run the complete short smoke with separate databases and monitoring storage:

```sh
python3 run.py javalin-jdbi3 --smoke --release /opt/vps256/release-jdbi-new --manifest prepared-bundles/jdbi-new/input-manifest.json
```

Check its contract/persistence outputs and analysis before measurement. Close the
exact tunnels, stop/start the VM, verify clock, resources, runtime, absent prior
services, deployment checksums and near-zero swap with `tools/vm.sh inspect` and
guest commands, then reopen tunnels. Keep the host awake for the measured run.
This resets guest state; preflight may warm filesystem pages, as in the originals.

```sh
python3 run.py javalin-jdbi3 --release /opt/vps256/release-jdbi-new --manifest prepared-bundles/jdbi-new/input-manifest.json
```

The public runner leaves every measured variant available at cutoff. Verify
http://127.0.0.1:19090/ and inspect the run's recorded historical window before
stopping monitoring. Avoid extra traffic during measurement. After inspection
is complete or explicitly skipped:

```sh
python3 run.py javalin-jdbi3 --finish results/<new-run-directory>
python3 analyze.py results/<new-run-directory>
```

This stops writers before storage collection. Close those exact tunnels and
stop the VM. Do not overwrite the recorded run directories.

Repeat preparation/reset/smoke/measurement for `javalin-mybatis` and
`javalin-jooq`, giving each a new release, bundle and capture directory. For the
historical jOOQ implementation add `--module /tmp/persistence-jooq-measured` to
`prepare-bundle.py`; it selects the matching original checker. The default uses
the corrected repository and checker and must be reported as a new variant.
The original Jdbi run had an explicit dashboard waiver and automatic shutdown;
the public runner consistently offers inspection for new measurements.

These instructions were reviewed during curation; no VM experiment was rerun for
publication. Original measurements remain the three archived individual runs.
