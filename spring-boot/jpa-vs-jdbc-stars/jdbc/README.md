# Star Pulse JDBC app

## Quick start on Linux

Install JDK 25, Maven, and Git. Then build and run directly from this public
repository:

```sh
git clone https://github.com/PVRLabs/experiments.git
cd experiments/spring-boot/jpa-vs-jdbc-stars/jdbc
java -version
mvn -DskipTests package
cp target/stars-jdbc-0.0.1-SNAPSHOT.jar stars-jdbc.jar
java -Djarmode=tools -jar stars-jdbc.jar extract --destination extracted
./run.sh
```

If you use [`mvn-lite`](https://github.com/ejboy/agent-scripts), run
`mvn-lite -DskipTests package` in place of the Maven command above.

Open <http://127.0.0.1:8080/> for the dashboard or
<http://127.0.0.1:8080/actuator/health> for health. The app first polls after
three seconds, then every ten minutes. It keeps its H2 database in `./data/`.
The run script enables compact object headers, prefers the extracted layout,
and falls back to the fat JAR. The memory comparison measured fat JARs for both
variants; extraction is a separate deployment choice.

## Repositories and monitoring

The default repositories are `PVRLabs/statlite`, `PVRLabs/aibadger`, and
`scriptella/scriptella-etl`. Set `APP_GITHUB_REPOS` to change the list (one to
five `owner/name` values), and optionally set `GITHUB_TOKEN`. The app polls
every ten minutes, records every successful observation, and continues after
individual GitHub failures. `POST /refresh` polls on demand.

The dashboard is at `/`. Actuator exposes `/actuator/health`,
`/actuator/metrics`, and `/actuator/prometheus`. Install StatLite v0.5.0 on the
same host, then run this in a second terminal from the `jdbc/` directory:

```sh
statlite --version
statlite --config ./statlite.yaml
```

Open <http://127.0.0.1:9091/> to see the Spring target. The sample YAML also
monitors StatLite itself. Adjust ports and the SQLite path in the YAML if
needed. Preserve `data/` and `statlite-stars.sqlite` across restarts or updates.
