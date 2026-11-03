package pvrlabs.repository;

/**
 * A commit was rejected because a participant explicitly marked the transaction
 * rollback-only. At a Jdbi managed transaction boundary, the rejection causes
 * rollback; marking alone does not immediately end the transaction.
 */
public final class RollbackOnlyException extends RuntimeException {
    public RollbackOnlyException() {
        super("Transaction was marked rollback-only");
    }
}
