# Spring Boot extracted layout on 256 MB

Curated public package for an engineering experiment comparing a Spring Boot
executable fat JAR with the official extracted layout on one constrained
Alpine VM.

The extracted layout reduced median Spring startup by 23.3% and median
first-request latency by 34.1% in this setup. Later-request latency, RSS, and
swap did not show a material winner. This is a result for one application,
JDK, VM, and JVM profile—not a universal benchmark claim.

## Contents

- `src/`, `pom.xml`, and `experiment/`: deterministic local H2-backed fixture
  and database reset inputs.
- [`results/phase-7-analysis.md`](results/phase-7-analysis.md): final
  individual-run table and derived summary.
- `statlite-operational-*.webp`: selected operational screenshots.
- The article draft remains in the private experiment record by design.
- [`EXPERIMENT.md`](EXPERIMENT.md): methodology, thresholds, limitations, and
  reproduction outline.

Private raw runs, VM logs, generated JARs, databases, and operator notes are
not mirrored here.

## Reproduction outline

Build with Java 25 and Maven:

```sh
mvn clean package -DskipTests
java -Djarmode=tools -jar target/stars-0.0.1-SNAPSHOT.jar \
  extract --destination target/extracted
```

To run the deterministic local experiment configuration, reset the included
fixture before each launch and use the same profile and JVM flags for both
layouts. The reset helper needs a standalone H2 2.4.240 JAR:

```sh
mvn dependency:copy \
  -Dartifact=com.h2database:h2:2.4.240 \
  -DoutputDirectory=tools -Dmdep.stripVersion=true

rm -rf data
./experiment/reset-database.sh tools/h2.jar "$PWD/data/starsdb"
java -Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC \
  -XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m \
  -XX:+UseCompactObjectHeaders -jar target/stars-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=experiment --server.port=8080
```

Stop that process, reset the fixture again, and run the extracted application
JAR with the identical command (changing only the JAR path):

```sh
./experiment/reset-database.sh tools/h2.jar "$PWD/data/starsdb"
java -Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC \
  -XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m \
  -XX:+UseCompactObjectHeaders -jar target/extracted/stars-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=experiment --server.port=8080
```

Open `http://127.0.0.1:8080/` to inspect the deterministic dashboard. Run the
two layouts one at a time. Reproducing the exact 256 MiB timing environment
still requires the private VM harness.

The measured comparison used Alpine 3.23.4, one vCPU, 256 MiB RAM, 512 MiB
swap, OpenJDK 25.0.4, and six fresh starts per layout in alternating pairs.
Exact constrained-VM reproduction requires the private provisioning harness;
this package provides the application and experiment inputs without claiming
to reproduce the private VM archive from a clean checkout.
