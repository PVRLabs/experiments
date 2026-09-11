# Experiment summary

The baseline launched one executable fat JAR. The variant was generated from
that exact JAR with Spring Boot's `jarmode=tools` extraction. Both layouts used
the same application, dependencies, local H2 fixture, VM, JDK, arguments,
endpoint, and guest-local curl client.

The fixed JVM profile was:

```text
-Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC
-XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m
-XX:+UseCompactObjectHeaders
```

Each layout had six fresh starts in alternating pairs. The guest measured one
first request, five sequential follow-ups, and five minutes of stability after
each startup. StatLite was absent from all twelve primary runs. Database reset
used a neutral H2 copy before each launch. No cold-page-cache claim was made.

Both absolute and relative materiality thresholds were fixed before the runs;
the practical rule also required the same direction in at least five of six
planned pairs.

## Result

Extracted won Spring startup and first-request latency in all six planned
pairs. Median Spring startup was 8.476 s versus 11.056 s for fat (-23.3%);
median first request was 1.447709 s versus 2.195665 s (-34.1%). Later-request
median, peak/settled RSS, and swap did not meet the materiality rule. All twelve
runs were stable.

## Operational follow-up

The selected extracted layout then ran for one hour with released StatLite
`v0.4.1` after six clean requests. All 120 scheduled loopback requests
succeeded. This run is separate from the primary comparison. Its recorded
startup is operational context only because that completed run omitted
`-XX:ReservedCodeCacheSize=32m`; the private journal documents the limitation.

The public package excludes the private article draft, raw logs, generated
artifacts, credentials, and the operational SQLite database.
