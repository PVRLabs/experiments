package pvrlabs.repository;

import java.io.IOException;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.jdbi.v3.core.Handle;
import org.jdbi.v3.core.Jdbi;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class RepositoryTest {
    static Jdbi fresh() {
        return Jdbi.create("jdbc:h2:mem:" + UUID.randomUUID() + ";DB_CLOSE_DELAY=-1");
    }
    static final class Rows {
        final RepositoryContext db;
        Rows(RepositoryContext db) { this.db = db; }
        void add(int id) { db.useHandle(h -> h.createUpdate("INSERT INTO entries VALUES (:id)").bind("id", id).execute()); }
        int count() { return db.withHandle(h -> h.createQuery("SELECT COUNT(*) FROM entries").mapTo(Integer.class).one()); }
        Handle handle() { return db.withHandle(h -> h); } // Identity/cleanup probe only; never execute after scope.
    }
    static Rows rows(Jdbi jdbi) {
        jdbi.useHandle(h -> h.execute("CREATE TABLE entries(id INT PRIMARY KEY)"));
        return new Rows(new RepositoryContext(jdbi, Dialects.H2));
    }

    @Test void statementSelectionIsImmutableAndExtensible() {
        var original = SqlStatement.of("default");
        var h2 = original.h2("h2");
        var both = h2.postgres("pg");
        assertEquals("default", original.sql("h2"));
        assertEquals("default", h2.sql("postgres"));
        assertEquals("h2", both.sql(" H2 "));
        assertEquals("pg", both.sql("postgres"));
        assertEquals("default", both.sql("unknown"));
        assertEquals("maria", both.override("mariadb", "maria").sql("mariadb"));
        assertEquals("default", both.sql("mariadb"));
        assertThrows(IllegalArgumentException.class, () -> SqlStatement.of(" "));
        assertThrows(NullPointerException.class, () -> SqlStatement.of(null));
        assertThrows(IllegalArgumentException.class, () -> both.override("", "sql"));
        assertThrows(IllegalArgumentException.class, () -> both.h2(""));
    }

    @Test void enumAndStringDialectsShareOverridesAndFallback() {
        var jdbi = fresh();
        for (var dialect : Dialects.values()) {
            var original = SqlStatement.of("default");
            var statement = original.override(dialect, "selected");
            assertEquals("default", original.sql(dialect));
            assertEquals("selected", statement.sql(dialect));
            assertEquals("selected", statement.sql(" " + dialect.name() + " "));
            var fromString = original.override(dialect.name().toLowerCase(java.util.Locale.ROOT), "string");
            assertEquals("string", fromString.sql(dialect));
            assertEquals("selected", new RepositoryContext(jdbi, dialect).sql(statement));
            assertEquals("selected", new RepositoryContext(jdbi, dialect.name()).sql(statement));
        }
        var custom = SqlStatement.of("default").override("custom-db", "custom");
        assertEquals("custom", new RepositoryContext(jdbi, " CUSTOM-DB ").sql(custom));
        assertEquals("default", custom.sql(Dialects.POSTGRES));
        assertThrows(NullPointerException.class, () -> custom.override((Dialects) null, "sql"));
        assertThrows(NullPointerException.class, () -> new RepositoryContext(jdbi, (Dialects) null));
    }

    @Test void convenienceMethodsUseEnumOverrideKeys() {
        var statement = SqlStatement.of("default");
        assertEquals("h2", statement.h2("h2").sql(Dialects.H2));
        assertEquals("pg", statement.postgres("pg").sql(Dialects.POSTGRES));
        // Each API must replace the same immutable override slot in both directions.
        assertEquals("enum", statement.h2("convenience").override(Dialects.H2, "enum").sql("h2"));
        assertEquals("convenience", statement.override(Dialects.H2, "enum").h2("convenience").sql(Dialects.H2));
        assertEquals("enum", statement.postgres("convenience").override(Dialects.POSTGRES, "enum").sql("postgres"));
        assertEquals("convenience", statement.override(Dialects.POSTGRES, "enum").postgres("convenience").sql(Dialects.POSTGRES));
    }

    @Test void sameNamedParametersExecuteAcrossOverrides() {
        var statement = SqlStatement.of("SELECT :id + 0").override(Dialects.H2, "SELECT CAST(:id AS INTEGER)")
                .override(Dialects.POSTGRES, "SELECT :id::integer");
        var jdbi = fresh();
        // H2 accepts this PostgreSQL cast; this is binding validation, not PostgreSQL validation.
        for (var dialect : new String[]{"unknown", "h2", "postgres"}) {
            var db = new RepositoryContext(jdbi, dialect);
            assertEquals(7, db.withHandle(h -> h.createQuery(db.sql(statement)).bind("id", 7).mapTo(Integer.class).one()).intValue());
        }
    }

    @Test void outsideTransactionCommitsAndClosesResources() {
        var rows = rows(fresh());
        rows.add(1);
        assertEquals(1, rows.count());
        var handle = rows.handle();
        assertTrue(handle.isClosed());
        AtomicReference<java.sql.Connection> connection = new AtomicReference<>();
        AtomicReference<java.sql.Statement> statement = new AtomicReference<>();
        rows.db.useHandle(h -> h.createQuery("SELECT 1").map((rs, ctx) -> {
            connection.set(h.getConnection());
            statement.set(ctx.getStatement());
            return rs.getInt(1);
        }).one());
        assertDoesNotThrow(() -> assertTrue(statement.get().isClosed()));
        assertDoesNotThrow(() -> assertTrue(connection.get().isClosed()));
        assertThrows(IllegalStateException.class, () -> rows.db.useHandle(h -> { throw new IllegalStateException(); }));
        rows.add(2); // scope cleared after failure
        assertEquals(2, rows.count());
    }

    @Test void nativeOuterTransactionAndNestedRepositoriesShareConnection() {
        var jdbi = fresh();
        var first = rows(jdbi);
        var second = new Rows(new RepositoryContext(jdbi, Dialects.H2));
        jdbi.useTransaction(outer -> {
            assertSame(outer, first.handle());
            first.add(1);
            second.db.useTransaction(inner -> {
                assertSame(outer, inner);
                assertSame(outer.getConnection(), second.handle().getConnection());
                second.add(2);
            });
            assertFalse(outer.isClosed());
            assertTrue(outer.isInTransaction());
        });
        assertEquals(2, first.count());
    }

    @Test void queryHelperSelectsSqlAndParticipatesWithoutClosingOuterHandle() {
        var jdbi = fresh();
        var rows = rows(jdbi);
        var find = SqlStatement.of("SELECT 99").h2("SELECT id FROM entries WHERE id=:id");
        AtomicReference<java.sql.Statement> statement = new AtomicReference<>();
        assertThrows(IllegalStateException.class, () -> jdbi.useTransaction(outer -> {
            rows.add(7);
            int id = rows.db.query(find, q -> q.bind("id", 7).map((rs, ctx) -> {
                statement.set(ctx.getStatement());
                return rs.getInt(1);
            }).one());
            assertEquals(7, id);
            assertTrue(statement.get().isClosed());
            assertFalse(outer.isClosed());
            assertTrue(outer.isInTransaction());
            throw new IllegalStateException("roll back the surrounding operation");
        }));
        assertEquals(0, rows.count());
        assertThrows(IllegalArgumentException.class, () -> rows.db.query("SELECT 1", q -> {
            throw new IllegalArgumentException("callback failed");
        }));
        assertNull(jdbi.getHandleScope().get());
        assertEquals(1, rows.db.query("SELECT 1", q -> q.mapTo(Integer.class).one()).intValue());
    }

    @Test void escapingCheckedExceptionRollsBackAndCloses() {
        var rows = rows(fresh());
        AtomicReference<Handle> seen = new AtomicReference<>();
        assertThrows(IOException.class, () -> rows.db.useTransaction(h -> {
            seen.set(h);
            rows.add(1);
            rows.db.useTransaction(inner -> { rows.add(2); throw new IOException("failure"); });
        }));
        assertEquals(0, rows.count());
        assertTrue(seen.get().isClosed());
        rows.add(3);
        assertEquals(1, rows.count());
    }

    @Test void caughtInnerApplicationExceptionDoesNotMarkRollbackOnly() {
        var rows = rows(fresh());
        rows.db.useTransaction(h -> {
            rows.add(1);
            assertThrows(IllegalStateException.class, () -> rows.db.useTransaction(inner -> {
                rows.add(2); throw new IllegalStateException("caught by outer");
            }));
            rows.add(3);
        });
        assertEquals(3, rows.count());
    }

    @Test void anotherThreadCommitsIndependentlyOfOuterRollback() throws Exception {
        var rows = rows(fresh());
        var executor = Executors.newSingleThreadExecutor();
        try {
            assertThrows(IllegalStateException.class, () -> rows.db.useTransaction(outer -> {
                rows.add(1);
                executor.submit(() -> {
                    assertNotSame(outer, rows.handle());
                    rows.add(2);
                }).get(5, TimeUnit.SECONDS);
                throw new IllegalStateException("outer rollback");
            }));
            assertEquals(1, rows.count());
            assertEquals(2, rows.db.withHandle(h -> h.createQuery("SELECT id FROM entries").mapTo(Integer.class).one()).intValue());
        } finally {
            executor.shutdownNow();
        }
    }

    @Test void distinctJdbiInstancesEvenOnSameDatabaseDoNotShareTransactions() {
        var url = "jdbc:h2:mem:" + UUID.randomUUID() + ";DB_CLOSE_DELAY=-1";
        var a = rows(Jdbi.create(url));
        var b = new Rows(new RepositoryContext(Jdbi.create(url), Dialects.H2));
        assertThrows(IllegalStateException.class, () -> a.db.useTransaction(outer -> {
            a.add(1);
            assertNotSame(outer, b.handle());
            b.add(2);
            throw new IllegalStateException();
        }));
        assertEquals(1, a.count());
    }

    @Test void separateDatabasesStayIndependent() {
        var a = rows(fresh());
        var b = rows(fresh());
        assertThrows(IllegalStateException.class, () -> a.db.useTransaction(outer -> {
            a.add(1);
            b.db.useTransaction(inner -> { assertNotSame(outer, inner); b.add(2); });
            throw new IllegalStateException();
        }));
        assertEquals(0, a.count());
        assertEquals(1, b.count());
    }

    @Test void manuallyOpenedHandleDoesNotEstablishManagedScope() {
        var jdbi = fresh();
        var rows = rows(jdbi);
        try (var manual = jdbi.open()) {
            manual.useTransaction(h -> {
                assertNotSame(h, rows.handle());
                rows.add(1);
                h.rollback();
            });
        }
        assertEquals(1, rows.count());
    }
}
