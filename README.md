# PVRLabs experiments

A collection of experiments from [PVRLabs](https://github.com/PVRLabs).

## Experiments

- [Spring Boot on a low-memory VPS](statlite/spring-boot-low-memory/)

  This experiment tested whether StatLite could provide useful monitoring
  beside a representative Spring Boot application on a severely constrained
  VPS. It found that 256 MB RAM was unstable for the application, while at
  512 MB RAM with a modest swapfile StatLite remained small and healthy and
  the controlled observation completed cleanly.
