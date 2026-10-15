# Jdbi repository preparation checks

`RepositoryCheck.java` checks fixture loading, history, a conflict in a later row
of a request batch (earlier rows must roll back), wrapped/null/unclassified
SQLState translation and exact controller HTTP 409/500 responses on port 8081.
Use fresh storage, with no measured application running on that port.

From the experiment directory, after building the Jdbi module:

```sh
mkdir -p /tmp/persistence-jdbi-check/classes /tmp/persistence-jdbi-check/db
javac -cp javalin-jdbi3/target/javalin-jdbi3-1.0.jar -d /tmp/persistence-jdbi-check/classes checks/jdbi3/RepositoryCheck.java
java -cp javalin-jdbi3/target/javalin-jdbi3-1.0.jar:/tmp/persistence-jdbi-check/classes RepositoryCheck /tmp/persistence-jdbi-check/db
```

Choose a new directory on repeats. The same commands can run inside the prepared
Alpine guest after transferring the source/build. The separate complete smoke
also checks real routes, invalid JSON/input, monitoring exclusions and persistence
reopening. See [reproduction](../../reproduction-guide.md) and the
[curated execution record](../../experiment-design.md). These are preparation checks,
not measured workload traffic.
