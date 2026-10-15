# jOOQ fixture-loading correction

## Review finding and change

Review found that the measured jOOQ implementation loaded its 1,170-row fixture
with `dsl.batch(template).execute()` outside a transaction. If a later fixture
row failed, earlier rows could remain committed; the next startup checks only
whether the table is nonempty and could then leave an incomplete fixture.

`JooqQuoteRepository.loadFixture()` now runs the full fixture batch through
`DSLContext.transaction()` and uses the transaction-scoped `DSLContext` for the
batch. A failure rolls back the fixture before it can leave partial startup
state.

The preparation checker now creates a separate H2 database, changes the last
fixture row into a duplicate-key conflict after earlier batch rows have been
accepted, verifies the batch failure and an empty table after rollback, then
calls normal initialization and verifies recovery to exactly 1,170 rows. The
checker passed on fresh host storage. The full functional check also passed.

## Relationship to the completed measurement

The one archived VM run used the original, nontransactional fixture loader.
Its successful fixture load and recorded application behavior remain valid for
that exact build. No archived measurement, manifest, or checksum was changed.
The 4.44-second readiness result, runtime measurements, 280 handwritten Java
lines, and 19,188,345-byte shaded JAR describe the original measured artifact.

The corrected source currently has 293 handwritten application Java lines,
excluding the unchanged StatLite adapter, and the rebuilt shaded JAR is
19,188,465 bytes. Those are build/code inventory facts only. The corrected
fixture initialization has not been measured in the Alpine VM, so its startup
time and runtime results are unknown. Any claim about the corrected build's
measured startup or resource consumption requires a separately authorized run.

## Verification and hashes

- `mvn-lite -q -f javalin/sql-persistence-256mb/javalin-jooq/pom.xml clean package dependency:tree -DoutputFile=jooq-review-dependencies.txt` completed successfully.
- `JooqRepositoryCheck` passed using fresh host-side H2 storage. It verified the injected late fixture failure, accepted earlier batch rows, atomic rollback, retry initialization, the ordinary fixture and repository checks, and restart persistence.
- The [recorded correction check](evidence/jooq-fixture-fix/fixture-recovery-check.json) preserves the result and current source/artifact hashes.
- No VM was launched; no smoke run, screenshot, workload, measurement, or public write was performed for this correction.
- The original repository source hash is preserved in the [pre-correction input manifest](evidence/jooq-release-002/input-manifest.json); the measured JAR hash is `4ef0e678f3ad256abf6e51a27f212f20d60cafa432206c95dbebb5031d217fb8`.
- Corrected `JooqQuoteRepository.java` SHA-256: `20c257274039f2e3e4d94769679297becd97024ae64934b5000c44010548b299`.
- Updated `JooqRepositoryCheck.java` SHA-256: `f1959bc0fe51873288b3e981a085c6ef9fde6433463c4471a8bb115bb693ce2a`.
- Corrected shaded JAR: 19,188,465 bytes; SHA-256 `0ad668ef55a4f170e2e2f2d4b06b48b6a34bc6f306906091cba99f715f452c4b`.

The module now ignores Maven's `target/` directory. Generated schema source
hashes and the original measured build hashes remain in their existing evidence
records; transient build output is not experiment evidence.
