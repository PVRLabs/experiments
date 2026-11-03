package pvrlabs.repository;

import java.util.Objects;
import java.util.function.Function;
import org.jdbi.v3.core.HandleCallback;
import org.jdbi.v3.core.HandleConsumer;
import org.jdbi.v3.core.Jdbi;
import org.jdbi.v3.core.statement.Query;

/**
 * Explicit repository operations over an application-supplied Jdbi instance.
 * Jdbi owns managed handle and transaction lifecycles; the application owns the
 * Jdbi configuration, data source, and its shutdown. Construct the context
 * before opening handles. Construction installs a rollback-only decorator on
 * Jdbi's default local transaction handler; custom handlers and replacement of
 * the handler after initialization are unsupported.
 *
 * <p>Managed callbacks on the same thread and Jdbi instance participate in the
 * same scope. Nested transaction callbacks join rather than create savepoints or
 * independent transactions. Other threads, other Jdbi instances and manually
 * opened handles do not establish that shared scope. Exceptions escaping the
 * outer boundary cause Jdbi to roll back; caught exceptions do not automatically
 * mark it rollback-only. This is not annotation interception or Spring transaction
 * propagation.</p>
 */
public final class RepositoryContext {
    private final Jdbi jdbi;
    private final String dialect;
    private final RollbackAwareTransactions transactions;

    public RepositoryContext(Jdbi jdbi, Dialects dialect) {
        this(jdbi, Objects.requireNonNull(dialect, "dialect").name());
    }

    public RepositoryContext(Jdbi jdbi, String dialect) {
        this.jdbi = Objects.requireNonNull(jdbi, "jdbi");
        this.dialect = SqlStatement.dialectKey(dialect);
        this.transactions = RollbackAwareTransactions.install(jdbi);
    }

    /**
     * Marks the current managed transaction on this thread, without ending it.
     * Repeated marks are harmless. A subsequent commit attempt throws
     * {@link RollbackOnlyException}; Jdbi's managed boundary then rolls back.
     * An exception escaping the boundary remains the original exception.
     *
     * @throws IllegalStateException if there is no active managed transaction or
     *         the installed transaction handler has changed
     */
    public void markRollbackOnly() {
        if (jdbi.getTransactionHandler() != transactions) {
            throw new IllegalStateException("Jdbi transaction handler changed after context initialization");
        }
        var scope = jdbi.getHandleScope().get();
        if (scope == null) throw new IllegalStateException("No managed transaction on this thread");
        transactions.mark(scope.getHandle());
    }

    public String sql(SqlStatement statement) {
        return statement.sql(dialect);
    }

    /**
     * Executes work with a native Jdbi query on a managed handle. The callback
     * binds parameters and consumes results; the query closes before return.
     * Do not return lazy results that require the query or handle to remain open.
     */
    public <T> T query(String sql, Function<Query, T> callback) {
        return jdbi.withHandle(handle -> {
            try (var query = handle.createQuery(sql)) {
                return callback.apply(query);
            }
        });
    }

    public <T> T query(SqlStatement statement, Function<Query, T> callback) {
        return query(sql(statement), callback);
    }

    public <T, X extends Exception> T withHandle(HandleCallback<T, X> callback) throws X {
        return jdbi.withHandle(callback);
    }

    public <X extends Exception> void useHandle(HandleConsumer<X> callback) throws X {
        jdbi.useHandle(callback);
    }

    public <T, X extends Exception> T inTransaction(HandleCallback<T, X> callback) throws X {
        return jdbi.inTransaction(callback);
    }

    /**
     * Runs a void operation in an explicit managed transaction callback. Joins
     * an existing transaction or starts one; Jdbi handles completion. Use
     * {@link #inTransaction(HandleCallback)} when a result or handle is needed.
     */
    public void transactional(Runnable action) {
        Objects.requireNonNull(action, "action");
        useTransaction(ignored -> action.run());
    }

    public <X extends Exception> void useTransaction(HandleConsumer<X> callback) throws X {
        jdbi.useTransaction(callback);
    }
}
