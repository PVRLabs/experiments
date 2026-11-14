# CoilBase + Jex + Hibernate

Hibernate provides all application persistence;
Spring Data will not be used.

## CoilBase and Jdbi disclosure

CoilBase 0.1.0-preview4 includes Jdbi transitively. Those libraries remain in
the resolved runtime dependencies; this experiment does not strip them or modify
CoilBase Core to improve the comparison.

The integration leaves `CoilBaseJexApplication.createPrimaryDataSource()`
at its default `null` and manages HikariCP and Hibernate lifecycle explicitly.
In the inspected CoilBase implementation, this skips creation of its Jdbi-backed
`RepositoryContext`. Application repositories use Hibernate directly.
The presence of Jdbi libraries therefore must be distinguished from initializing
or using a Jdbi persistence implementation.

Packaged HTTP refresh and restart checks inspect `/persistence-context`. This
uses CoilBase's `db()` accessor: an initialized context would be returned, while
its documented absent-context exception means none was constructed. Startup also
fails if a context is present. This directly checks instance state rather than
inferring construction from a particular class-loading log. Runtime dependency
trees document the retained libraries; no measured zero-overhead claim is made.

The direct-Jex/Hibernate control is omitted by agreement, with the unused context
absence checked directly during the exercised application lifecycle.
