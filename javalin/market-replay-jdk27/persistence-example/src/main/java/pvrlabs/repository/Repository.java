package pvrlabs.repository;

import java.util.Objects;

/**
 * Optional base class storing a shared {@link RepositoryContext}. A repository
 * can use composition instead. This class does not create or close a data source,
 * execute SQL, discover repositories, or define transaction boundaries.
 */
public abstract class Repository {
    protected final RepositoryContext db;

    protected Repository(RepositoryContext db) {
        this.db = Objects.requireNonNull(db, "db");
    }
}
