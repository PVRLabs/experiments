# Sequential CoilBase migration skills on Spring PetClinic

Can the JPA migration skill and the Spring Boot migration skill work in sequence on the same application? On H2, the first skill replaced PetClinic's three Spring Data JPA repositories with CoilBase/Jdbi while retaining Spring Boot, Spring MVC, and Thymeleaf. The second phase replaced the Boot and MVC layers with Avaje Jex and reused the same repository source files. The upstream SQL schema and seed resources were identical across all three variants.

## What to read

Fetch individual files as needed. A checkout of this experiments repository is unnecessary.

| Task | Files to read or download |
| --- | --- |
| Understand the sequence and its limits | This README |
| Inspect how Boot retained the new persistence layer | [Phase 1 patch](phase1.patch) |
| Inspect how Jex reused the repositories | [Phase 2 patch](phase2.patch) |
| Verify the workflow and persisted data | [Upstream](results/baseline-packaged.txt), [Phase 1](results/phase1-packaged.txt), [Phase 2](results/phase2-packaged.txt), and [focused Jex review checks](results/phase2-review-regressions.txt) |
| Reproduce the comparison | [Instructions](reproduce.md), both patches, [packaged check](packaged-check.py), and [baseline rollback test](BaselineRollbackTests.java) |

For example, fetch the README directly at `https://raw.githubusercontent.com/PVRLabs/experiments/main/java/coilbase/petclinic-combined/README.md`. Use the same base URL for the individual files listed above. The reproduction instructions fetch the pinned PetClinic source archive separately.

## Result

| Variant | Maven tests passed | Skipped | H2 packaged workflow |
| --- | ---: | ---: | --- |
| Pinned upstream | 77, plus one separate rollback probe | 2 | Passed |
| Phase 1 with Spring Boot and CoilBase/Jdbi | 79 | 2 | Passed |
| Phase 2 with Jex and CoilBase/Jdbi | 28 | 0 | Passed |

The packaged checks exercised owner, pet and visit forms, validation, concurrent duplicate pet submissions, vet HTML/JSON/XML, assets, database health, committed SQL state and restart. Both migrations also opened independent copies of the upstream H2 database. [Baseline rollback](results/baseline-rollback.txt), [Phase 1 on upstream data](results/phase1-upstream-data.txt), [Phase 2 on upstream data](results/phase2-upstream-data.txt).

The original comparison used the first accepted Jex package. The Phase 2 patch includes subsequent review fixes for partial owner and pet edits and for specific media exclusions in Accept headers. The revised package passed its 28 Maven tests and the [targeted packaged checks](results/phase2-review-regressions.txt).

## Scope and reproducibility

- The upstream revision was `500158f732419217507c7656904b8e6aa1bcc0d6`. Both Agent Scripts skills came from commit `eaf395fe4d86496ab17bf3781c434105e79c06dd`. The trial started with upstream source and used neither a historical PetClinic port nor output from a prior skill trial.
- The runs used Temurin 25, Spring Boot 4.1.0, CoilBase 0.1.0-preview5, Jdbi 3.55.0, Avaje Jex 3.6, and H2 2.4.240. The [final dependency tree](results/phase2-dependencies.txt) shows the remaining libraries, including Thymeleaf and Spring Data Commons. The Jex package does not require Spring Boot, Spring MVC, Spring Data JPA, or Hibernate ORM.
- MySQL and PostgreSQL remain unverified. Owner and vet pagination use ID order and ignore caller-supplied sorting. The exercised controllers use unsorted requests. Phase 2 uses application-managed flash cookies and exposes a database health endpoint. Full Actuator parity and Spring property precedence are outside scope.
- Packaged testing caught a missing JAXB runtime during Phase 1 and a form-decoding difference during Phase 2. The patches include the fixes.
