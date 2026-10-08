# Deferred Java error-path fixes

Apply `review-errors.patch` from the experiment directory only after the paired
measurements. The frozen Java source and binaries currently remain unchanged.
The patch rejects null history symbols before List.of().contains, and uses a
null-safe SQL error helper in both applications (Spring has the same latent
SQLState issue). Constraint errors remain 409; unexpected or null-state errors
remain 500 with a non-null error code. Successful request paths are unchanged.

`ReviewErrorPaths.java` checks missing/invalid symbols, valid history, constraint,
unexpected and null SQL states. It was compiled and run against a temporary
candidate source tree, with the frozen Javalin JAR supplying dependencies.
Candidate Javalin and Spring handlers were also compiled separately. No candidate
classes enter the measured bundle. Apply and rerun these checks after measurement.
