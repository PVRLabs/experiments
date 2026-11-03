package pvrlabs.repository;

import java.sql.SQLException;
import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;
import org.jdbi.v3.core.Handle;
import org.jdbi.v3.core.Jdbi;
import org.jdbi.v3.core.transaction.DelegatingTransactionHandler;
import org.jdbi.v3.core.transaction.LocalTransactionHandler;
import org.jdbi.v3.core.transaction.TransactionHandler;

/**
 * Decorates Jdbi's default local handler with a per-handle rollback-only marker.
 * A marked commit is rejected; rollback clears the marker. Jdbi still performs
 * begin, rollback, and managed callback cleanup. Installation is shared by
 * contexts using the same Jdbi instance and must precede opening handles.
 * Custom handlers and changing the handler after installation are unsupported.
 * This internal mechanism does not propagate transactions between threads or
 * provide savepoints, independent nested transactions, or automatic marking of
 * caught exceptions.
 */
final class RollbackAwareTransactions extends DelegatingTransactionHandler {
    private final Set<Handle> marked;

    private RollbackAwareTransactions(TransactionHandler delegate, Set<Handle> marked) {
        super(delegate);
        this.marked = marked;
    }

    static RollbackAwareTransactions install(Jdbi jdbi) {
        synchronized (jdbi) {
            var delegate = jdbi.getTransactionHandler();
            if (delegate instanceof RollbackAwareTransactions installed) return installed;
            if (jdbi.getHandleScope().get() != null) {
                throw new IllegalStateException("Create RepositoryContext before opening managed handles");
            }
            if (delegate.getClass() != LocalTransactionHandler.class
                    && delegate.getClass() != LocalTransactionHandler.binding().getClass()) {
                throw new IllegalArgumentException("Rollback-only support requires Jdbi's default local transaction handler");
            }
            var handler = new RollbackAwareTransactions(delegate,
                    Collections.synchronizedSet(Collections.newSetFromMap(new WeakHashMap<>())));
            jdbi.setTransactionHandler(handler);
            return handler;
        }
    }

    @Override
    public TransactionHandler specialize(Handle handle) throws SQLException {
        return new RollbackAwareTransactions(getDelegate().specialize(handle), marked);
    }

    void mark(Handle handle) {
        if (!handle.isInTransaction()) throw new IllegalStateException("No active transaction");
        marked.add(handle);
    }

    @Override
    public void commit(Handle handle) {
        if (marked.contains(handle)) throw new RollbackOnlyException();
        super.commit(handle);
    }

    @Override
    public void rollback(Handle handle) {
        try {
            super.rollback(handle);
        } finally {
            marked.remove(handle);
        }
    }
}
