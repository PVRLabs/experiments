# Method

The comparison used one Ubuntu 24.04 x86_64 VM configured with 768 MiB RAM,
one vCPU, and 256 MiB persistent swap. Spring Boot and Quarkus used the same
Java distribution and JVM profile:

```text
-Xms16m
-Xmx80m
-Xss256k
-XX:+UseSerialGC
-XX:TieredStopAtLevel=1
-XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

The applications used separate file-backed H2 databases and the same
deterministic loopback fixture. Spring started first, then Quarkus. After both
were ready, one equivalent `GET /` was sent to each application. StatLite then
started with its normal monitoring configuration.

The bounded workload repeated ten times:

1. `GET /` on Spring
2. `GET /` on Quarkus
3. wait one second

Every workload request returned HTTP 200. The observation used these captures:

- `ready-pre-request`
- `after-one-request`
- `post-workload`
- intermediate observation
- five-minute observation
- ten-minute observation

The measured signals were process RSS, per-process swap, JVM heap, host memory,
service state, restart count, application health, and StatLite polling status.
The applications and StatLite were left running after the final capture.
