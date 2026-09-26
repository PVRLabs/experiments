# Star Pulse JDBC app

Build with JDK 25 and Maven: `mvn -DskipTests package`. On the Linux host,
copy the packaged JAR as `stars-jdbc.jar` beside `run.sh` and `statlite.yaml`,
then run `./run.sh`. The script enables compact object headers and creates a
file-backed H2 database under `./data/`.

For deployment, extract the packaged JAR before starting:

```sh
java -Djarmode=tools -jar stars-jdbc.jar extract --destination extracted
./run.sh
```

The run script prefers `extracted/stars-jdbc.jar` and falls back to the fat JAR.
The memory comparison measured fat JARs for both variants; extracted layout is
a separate deployment choice based on the earlier Stars layout experiment.

The default repositories are `PVRLabs/statlite`, `PVRLabs/aibadger`, and
`scriptella/scriptella-etl`. Set `APP_GITHUB_REPOS` to change the list (one to
five `owner/name` values), and optionally set `GITHUB_TOKEN`. The app polls
every ten minutes, records every successful observation, and continues after
individual GitHub failures. `POST /refresh` polls on demand.

The dashboard is at `/`. Actuator exposes `/actuator/health`,
`/actuator/metrics`, and `/actuator/prometheus`. With StatLite v0.5.0 installed,
start the app and run `statlite --config ./statlite.yaml`. Adjust ports and the
SQLite path in the YAML for the host. Preserve both H2 and SQLite files across
restarts.
