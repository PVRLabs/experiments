# PVRLabs experiments

A collection of experiments from [PVRLabs](https://github.com/PVRLabs).

## Experiments

- [StatLite on a 256 MB TierHive VPS](statlite/tierhive-recipe-256mb/)

  A manual deployment check of StatLite's native Alpine/OpenRC TierHive
  recipe, monitoring a Spring Boot Actuator application plus the VPS itself
  through StatLite self-monitoring.

- [Spring Boot on a low-memory VPS](statlite/spring-boot-low-memory/)

  This experiment tested whether StatLite could provide useful monitoring
  beside a representative Spring Boot application on a severely constrained
  VPS. It found that 256 MB RAM was unstable for the application, while at
  512 MB RAM with a modest swapfile StatLite remained small and healthy and
  the controlled observation completed cleanly.

- [Spring Boot vs Quarkus under extreme memory pressure](statlite/spring-vs-quarkus/)

  A curated Spring Boot and Quarkus comparison using the same JDK 25,
  `Xmx80m` profile, and 512 MiB VM. Quarkus started larger but developed the
  smaller resident working set under pressure; a later constrained-VM run
  OOM-killed Spring, showing that the configuration could not reliably keep
  both JVM applications alive for an hour.

- [Spring Boot fat JAR vs extracted layout](spring-boot/extracted-layout/)

  A controlled comparison of Spring Boot's executable fat JAR and its official
  extracted runtime layout, measuring startup, first-request latency, and
  settled memory behavior.
