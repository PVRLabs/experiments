# Reproduce the combined PetClinic migration

## Build and verify the source variants

Run from this directory. Use Maven 3.9.9, Java 25 and Python 3.9 or newer. On a fresh Maven cache, omit `-o` and populate the Mockito artifact before running the Spring suites. The integration suite and packaged probes need loopback server permission. An explicit Mockito startup agent avoids a long attach delay on this JDK.

```sh
record_dir=$PWD
work=$(mktemp -d)
revision=500158f732419217507c7656904b8e6aa1bcc0d6
curl -fLsS "https://codeload.github.com/spring-projects/spring-petclinic/tar.gz/$revision" -o "$work/upstream.tgz"
for variant in baseline phase1 phase2 baseline-probe; do
  mkdir "$work/$variant"
  tar -xzf "$work/upstream.tgz" --strip-components=1 -C "$work/$variant"
done
for variant in phase1 phase2; do
  git -C "$work/$variant" apply --check --whitespace=error "$record_dir/phase1.patch"
  git -C "$work/$variant" apply "$record_dir/phase1.patch"
done
git -C "$work/phase2" apply --check --whitespace=error "$record_dir/phase2.patch"
git -C "$work/phase2" apply "$record_dir/phase2.patch"

mvn -B org.apache.maven.plugins:maven-dependency-plugin:3.10.0:get -Dartifact=org.mockito:mockito-core:5.24.0
mockito="$HOME/.m2/repository/org/mockito/mockito-core/5.24.0/mockito-core-5.24.0.jar"
for variant in baseline phase1; do
  (cd "$work/$variant" && JAVA_TOOL_OPTIONS="-javaagent:$mockito" mvn -o -B verify)
done
(cd "$work/phase2" && mvn -o -B verify)

cp "$record_dir/BaselineRollbackTests.java" "$work/baseline-probe/src/test/java/org/springframework/samples/petclinic/service/"
(cd "$work/baseline-probe" && JAVA_TOOL_OPTIONS="-javaagent:$mockito" mvn -o -B -Dtest=BaselineRollbackTests test)
```

The standalone baseline probe is staged only in its own copy. It verifies rollback after a JPA flush using an independent SQL read and then verifies recovery. The shared repository assertions in the migration patches cover a failed dependent write and an outer CoilBase transaction.

## Check the packaged variants

Finish building before starting a packaged process. The harness launches an independent JAR and H2 file per variant. It starts with initialization enabled, probes HTTP, shuts down for direct SQL checks, then restarts with initialization disabled. The last invocations test compatibility against separate copies of the baseline database.

```sh
h2="$HOME/.m2/repository/com/h2database/h2/2.4.240/h2-2.4.240.jar"
boot_jar=spring-petclinic-4.0.0-SNAPSHOT.jar
jex_jar=petclinic-jex-4.0.0-SNAPSHOT.jar
python3 packaged-check.py "$work/baseline/target/$boot_jar" "$h2" "$work/baseline-http" --port 18094
python3 packaged-check.py "$work/phase1/target/$boot_jar" "$h2" "$work/phase1-http" --port 18095
python3 packaged-check.py "$work/phase2/target/$jex_jar" "$h2" "$work/phase2-http" --port 18096
python3 packaged-check.py "$work/phase1/target/$boot_jar" "$h2" "$work/phase1-existing" --port 18095 \
  --existing-db "$work/baseline-http/petclinic.mv.db"
python3 packaged-check.py "$work/phase2/target/$jex_jar" "$h2" "$work/phase2-existing" --port 18096 \
  --existing-db "$work/baseline-http/petclinic.mv.db" --default-init
```

## Recheck the Jex review fixes

After building the revised Phase 2 patch, run these focused checks against a fresh H2 file.

```sh
python3 packaged-check.py "$work/phase2/target/$jex_jar" "$h2" "$work/phase2-review" \
  --port 18096 --review-regressions
```

The probe exercises empty and partial owner edits, partial pet edits, explicitly blank inputs, and vet Accept headers that mix specific media ranges with wildcards. It independently checks the owner and pet rows after shutdown. The original full packaged run remains in the experiment evidence. The [focused output](results/phase2-review-regressions.txt) applies to the revised Phase 2 patch.
