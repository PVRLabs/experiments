# PVRLabs experiments

A collection of experiments from [PVRLabs](https://github.com/PVRLabs).

## Who these experiments are for

Many of our experiments focus on developers building small, self-hosted applications on affordable servers. Think independent developers, solopreneurs, and small teams who want practical software without maintaining complex infrastructure.

For Java applications, we're particularly interested in:

- **256–512 MiB VPS deployments**, sometimes extending to 1 GiB.
- Conventional JVM applications using familiar development and diagnostic tools.
- Useful applications with persistence, monitoring, and enough memory headroom for the operating system.
- Maintainable architectures that can grow, including moving a database or other components to separate infrastructure later.

We're not trying to achieve the smallest possible Java process. GraalVM Native Image can offer substantial startup and memory benefits, but it introduces different build, compatibility, and operational tradeoffs. For now, we're more interested in what ordinary HotSpot deployments can accomplish on modest hardware.

Similarly, Kubernetes optimization, container density, and extreme memory minimization aren't our primary focus.

**This describes our interests, not strict requirements.** The repository also contains experiments outside this area, and we'll continue exploring other technologies when the questions are interesting.

## Experiments

- [Javalin with JDBC and monitoring on 256 MiB](javalin/vps-256mb/)

  Equivalent Javalin and extracted Spring Boot applications on a constrained
  Alpine VM, with file-backed H2 and StatLite. Includes original OS/HTTP samples,
  corrected analyses, screenshots and reproduction code, with paging caveats.

- [Monitoring Javalin with its existing Micrometer instrumentation](statlite/javalin-micrometer/)

  A small application-side adapter connects Javalin metrics to StatLite for
  requests, errors, latency, JVM resources, health, and restart history.

- [Monitoring a Pyronaut app with StatLite](statlite/pyronaut-statlite/)

  A Pyronaut Python HTTP app exposed Micronaut/Micrometer Prometheus metrics
  accepted by released StatLite's existing Micronaut target, with no StatLite
  changes. [PVRLabs experiment page](https://pvrlabs.xyz/java-performance/experiments/pyronaut-statlite.html).

- [Idle PostgreSQL connections and Spring Boot's fixed pool](java/jdbc-pool-reclaim/)

  Two Spring Boot instances either kept 20 PostgreSQL connections after a
  burst or returned to 2. With 2 connections, PostgreSQL cgroup memory was
  about 29 MiB lower than with 20. Hikari's default pool sizing keeps the
  peak because its idle target resolves equal to its maximum. Setting a
  lower idle target released connections only when idle retirement was
  enabled.

- [Spring Boot, Quarkus, and Micronaut with JDBC](statlite/spring-quarkus-micronaut-jdbc/)

  Equivalent JDBC applications on Java 25 in a 1 GiB no-swap VM, with
  sequential 15-minute scripted-load windows and a separate shared-host
  observation. Includes curated RSS/CPU data, screenshots, source, and analysis.
  [Related PVRLabs article](https://pvrlabs.xyz/articles/spring-boot-quarkus-micronaut-jdbc.html).

- [Spring Boot Stars: JPA versus JDBC](spring-boot/jpa-vs-jdbc-stars/)

  A paired JDK 25 comparison of the conventional Hibernate Stars app and a
  smaller Spring MVC + JDBC version. Both expose Actuator for StatLite 0.5.0;
  raw RSS and startup measurements and reproduction scripts are included.
  [PVRLabs experiment page](https://pvrlabs.xyz/java-performance/experiments/spring-boot-jpa-vs-jdbc.html).

- [Spring Boot fat JAR vs extracted layout](spring-boot/extracted-layout/)

  A controlled comparison of Spring Boot's executable fat JAR and its official
  extracted runtime layout, measuring startup, first-request latency, and
  settled memory behavior. [Related PVRLabs article](https://pvrlabs.xyz/articles/spring-boot-extracted-layout.html).

- [Spring Boot fat JAR vs extracted layout vs Gradle application distribution](spring-boot/gradle-application-vs-spring-boot/)

  A short three-way follow-up using the same application and constrained VM,
  focused on startup and first-request latency.
  [PVRLabs experiment page](https://pvrlabs.xyz/java-performance/experiments/gradle-application-vs-spring-boot.html).

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
  [Related PVRLabs article](https://pvrlabs.xyz/articles/spring-boot-vs-quarkus-512mb.html).

- [Spring Boot on a low-memory VPS](statlite/spring-boot-low-memory/)

  This experiment tested whether StatLite could provide useful monitoring
  beside a representative Spring Boot application on a severely constrained
  VPS. It found that 256 MB RAM was unstable for the application, while at
  512 MB RAM with a modest swapfile StatLite remained small and healthy and
  the controlled observation completed cleanly.
  [Related PVRLabs article](https://pvrlabs.xyz/articles/spring-boot-256mb-jdk25.html).
