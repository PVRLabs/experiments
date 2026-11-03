# Jdbi persistence example

This source extract accompanies the [Javalin JDK 27 experiment](../README.md).
It explores explicit persistence conventions for an application that needs
repositories and transactions alongside a lightweight HTTP stack. It is an
experiment, not an announced framework or a stable library API.

[Jdbi Core](https://jdbi.org/releases/3.55.0/) already provides SQL execution,
parameter binding, mapping, managed handles and transaction callbacks. This
prototype adds an optional repository base, a shared context with a query
convenience method, optional dialect-specific SQL selection, a void transaction
callback and an explicit rollback-only marker. Jdbi still owns transaction and
handle lifecycle. Plain Jdbi can accomplish the same basic work without this
layer; the question is whether these conventions are useful enough to justify
their additional API and constraints.

## Try it

With JDK 17 or later and Maven, run from this directory:

```sh
mvn verify
```

The standalone tests use Jdbi Core 3.55.0 and test-only H2 and JUnit. They do
not require a running database. They exercise the extracted persistence behavior,
not MariaDB, the complete application, deployment or benchmark runner.

## Follow the measured code

The measured application's [QuoteRepository](src/test/java/pvrlabs/marketreplay/QuoteRepository.java)
puts all quote inserts in one explicit transaction. Its actual pattern is:

```java
db.transactional(() -> {
    for (FixtureQuote quote : batch.quotes()) {
        db.useHandle(handle -> handle.createUpdate(INSERT)
                .bind("fetchedAt", Timestamp.from(fetchedAt))
                .bind("cycle", batch.cycle())
                .bind("sampleIndex", batch.sampleIndex())
                .bind("marketTime", batch.marketTime())
                .bind("symbol", quote.symbol())
                .bind("price", quote.price())
                .execute());
    }
});
```

This excerpt lives inside `QuoteRepository.insert`; `db`, `INSERT` and the
model records are defined in the included source. Reads use `db.query` and a
row mapper. The [quote test](src/test/java/pvrlabs/marketreplay/QuoteRepositoryTest.java)
uses H2 to show that a failure on a later insert rolls back earlier rows. The
measured path is a repository-scoped batch, not an example of a service
coordinating multiple repositories.

## Design and transaction boundaries

- [RepositoryContext](src/main/java/pvrlabs/repository/RepositoryContext.java)
  wraps an application-supplied Jdbi instance. The application configures and
  closes its data source; construct the context before opening handles.
- [Repository](src/main/java/pvrlabs/repository/Repository.java) is an optional
  base class that stores the context; composition works too.
- [SqlStatement](src/main/java/pvrlabs/repository/SqlStatement.java) selects an
  immutable default or dialect override. It does not detect databases or check
  that overrides have equivalent bindings or behavior.
- [RollbackAwareTransactions](src/main/java/pvrlabs/repository/RollbackAwareTransactions.java)
  adds an explicit marker to Jdbi's default local transaction handler. It is an
  internal adapter; [RollbackOnlyException](src/main/java/pvrlabs/repository/RollbackOnlyException.java)
  reports a rejected commit.

Managed callbacks on the same thread and Jdbi instance can share a transaction;
nested callbacks join it rather than start independent transactions. An
exception escaping the outer boundary causes rollback. Catching an exception
does not automatically mark the transaction: call `markRollbackOnly()` within
the active managed transaction when it must not commit. The marker does not
end the transaction immediately; an attempted commit throws, and the managed
boundary rolls back. Different threads or Jdbi instances and manually opened
handles do not join that scope. Custom transaction handlers, savepoints,
independent nested transactions and annotation interception are outside this
prototype's supported contract. A caught SQL error can also leave the underlying
database transaction unusable, depending on the database.

[RepositoryTest](src/test/java/pvrlabs/repository/RepositoryTest.java) covers
selection, resource cleanup, shared handles, nested callbacks and independent
scopes. [RollbackOnlyTest](src/test/java/pvrlabs/repository/RollbackOnlyTest.java)
exercises caught failures, explicit marking, cleanup and handler constraints.
These tests illustrate coordination across repository contexts; the benchmarked
quote ingestion did not measure a multi-repository service operation.

The core and quote repository preserve the experiment-era implementation. The
H2 quote test was adapted for this standalone extract. The experiment measured
the complete application stack and did not isolate this prototype's memory cost.

Feedback is welcome: does this API make ordinary repository work clearer, or
does it add unnecessary complexity? Are its explicit transaction and
rollback-only semantics understandable and useful? Please include a concrete
use case or counterexample when suggesting a change.
