# Original measured jOOQ source

These two Java files match the original preparation manifest. No session logs
are included. The repository has the original nontransactional fixture loader;
keep it separate from the corrected, unmeasured working module.

For historical reproduction, copy `javalin-jooq/` to a new directory, replace
`src/main/java/lab/JooqQuoteRepository.java` with this historical file and build
using Java 25 and Maven. Use this directory's checker with that build.
See [full commands](../../reproduction-guide.md).

[Historical rebuild verification](rebuild-verification.json) matched all application
inputs, resolved dependencies and generated source hashes. Every shaded-JAR entry
had identical contents, with only ZIP timestamps differing. The original checker
compiled to identical classes. The archived JAR hash is
`4ef0e678f3ad256abf6e51a27f212f20d60cafa432206c95dbebb5031d217fb8`.
