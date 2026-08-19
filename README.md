# PVRLabs experiments

A collection of experiments from [PVRLabs](https://github.com/PVRLabs).

## Experiments

- [Spring Boot on a low-memory VPS](statlite/spring-boot-low-memory/)

  This experiment tested whether lightweight monitoring could run beside a
  representative Spring Boot application on a severely constrained VPS. It
  found that 256 MB RAM was unstable for this workload, while 512 MB RAM with
  a modest swapfile completed the controlled observation cleanly.
