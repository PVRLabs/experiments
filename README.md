# PVRLabs experiments

A collection of experiments from [PVRLabs](https://github.com/PVRLabs).

## Experiments

- [Monitoring Javalin with its existing Micrometer instrumentation](statlite/javalin-micrometer/)

  A small application-side adapter connects Javalin metrics to StatLite for
  requests, errors, latency, JVM resources, health, and restart history.

- [Monitoring a Pyronaut app with StatLite](statlite/pyronaut-statlite/)

  A Pyronaut Python HTTP app exposed Micronaut/Micrometer Prometheus metrics
  accepted by released StatLite's existing Micronaut target, with no StatLite
  changes.

- [Spring Boot, Quarkus, and Micronaut with JDBC](statlite/spring-quarkus-micronaut-jdbc/)

  Equivalent JDBC applications on Java 25 in a 1 GiB no-swap VM, with
  sequential 15-minute scripted-load windows and a separate shared-host
  observation. Includes curated RSS/CPU data, screenshots, source, and analysis.

- [Spring Boot Stars: JPA versus JDBC](spring-boot/jpa-vs-jdbc-stars/)

  A paired JDK 25 comparison of the conventional Hibernate Stars app and a
  smaller Spring MVC + JDBC version. Both expose Actuator for StatLite 0.5.0;
  raw RSS and startup measurements and reproduction scripts are included.

- [Spring Boot fat JAR vs extracted layout](spring-boot/extracted-layout/)

  A controlled comparison of Spring Boot's executable fat JAR and its official
  extracted runtime layout, measuring startup, first-request latency, and
  settled memory behavior.

- [Spring Boot fat JAR vs extracted layout vs Gradle application distribution](spring-boot/gradle-application-vs-spring-boot/)

  A short three-way follow-up using the same application and constrained VM,
  focused on startup and first-request latency.

- [StatLite on a 256 MB TierHive VPS](statlite/tierhive-recipe-256mb/)

  A manual deployment check of StatLite's native Alpine/OpenRC TierHive
  recipe, monitoring a Spring Boot Actuator application plus the VPS itself
  through StatLite self-monitoring.

- [Spring Boot vs Quarkus under extreme memory pressure](statlite/spring-vs-quarkus/)

  A curated Spring Boot and Quarkus comparison using the same JDK 25,
  `Xmx80m` profile, and 512 MiB VM. Quarkus started larger but developed the
  smaller resident working set under pressure; a later constrained-VM run
  OOM-killed Spring, showing that the configuration could not reliably keep
  both JVM applications alive for an hour.

- [Spring Boot on a low-memory VPS](statlite/spring-boot-low-memory/)

  This experiment tested whether StatLite could provide useful monitoring
  beside a representative Spring Boot application on a severely constrained
  VPS. It found that 256 MB RAM was unstable for the application, while at
  512 MB RAM with a modest swapfile StatLite remained small and healthy and
  the controlled observation completed cleanly.
