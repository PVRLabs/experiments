package lab;

import static lab.jooq.generated.tables.Quotes.QUOTES;

import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.SQLException;
import java.util.Map;

import org.jooq.ExecuteContext;
import org.jooq.impl.DSL;
import org.jooq.impl.DefaultConfiguration;
import org.jooq.impl.DefaultExecuteListener;
import org.jooq.impl.DefaultExecuteListenerProvider;

import com.zaxxer.hikari.HikariDataSource;

public final class JooqRepositoryCheck {
    private static void check(boolean passed, String message) {
        if (!passed) throw new AssertionError(message);
    }

    private static HikariDataSource dataSource(Path directory) {
        var ds = new HikariDataSource();
        ds.setJdbcUrl("jdbc:h2:file:" + directory.resolve("quotes")
            + ";CACHE_SIZE=4096;DB_CLOSE_ON_EXIT=FALSE");
        ds.setUsername("sa");
        ds.setPassword("");
        ds.setMinimumIdle(1);
        ds.setMaximumPoolSize(2);
        ds.setConnectionTimeout(3000);
        ds.setValidationTimeout(1000);
        return ds;
    }

    public static void main(String[] args) throws Exception {
        var directory = Path.of(args[0]).toAbsolutePath();
        Files.createDirectories(directory);
        var sqlFile = directory.resolve("jooq-generated-sql.txt");
        var ds = dataSource(directory);
        var configuration = new DefaultConfiguration().set(ds).set(org.jooq.SQLDialect.H2)
            .set(new DefaultExecuteListenerProvider(new DefaultExecuteListener() {
                @Override public void executeStart(ExecuteContext context) {
                    if (context.query() != null) {
                        try {
                            Files.writeString(sqlFile, context.query().getSQL() + "\n",
                                java.nio.file.StandardOpenOption.CREATE,
                                java.nio.file.StandardOpenOption.APPEND);
                        } catch (java.io.IOException e) {
                            throw new IllegalStateException(e);
                        }
                    }
                }
            }));
        var repository = new JooqQuoteRepository(ds, DSL.using(configuration));
        repository.initialize();
        var dsl = DSL.using(configuration);
        check(repository.state().rows() == 1170, "Fixture row count");
        check(repository.state().maxSequence() == 389, "Fixture maximum sequence");
        check(repository.latest().size() == 3, "Latest quote count");
        var history = repository.history("AAPL", 390);
        check(history.size() == 390, "History size");
        check(history.getFirst().sequence() == 0 && history.getLast().sequence() == 389,
            "History ordering");
        check(history.getLast().price().scale() == 4, "Decimal scale");

        dsl.insertInto(QUOTES, QUOTES.BATCH_SEQ, QUOTES.CYCLE, QUOTES.SAMPLE_INDEX,
                QUOTES.MARKET_TIME, QUOTES.SYMBOL, QUOTES.PRICE)
            .values(999, 1, 0, "09:30", "GOOG", BigDecimal.ONE).execute();
        var beforeFailure = repository.state();
        try {
            repository.insert(new QuoteBatch(999, 1, 0, "09:30", Map.of(
                "AAPL", BigDecimal.ONE, "GOOG", BigDecimal.ONE, "NVDA", BigDecimal.ONE)));
            throw new AssertionError("Expected unique-key conflict");
        } catch (RepositoryFailure failure) {
            check(failure.kind() == RepositoryFailure.Kind.CONFLICT, "Conflict mapping");
        }
        check(repository.state().equals(beforeFailure), "Batch rollback after later-row conflict");

        repository.insert(new QuoteBatch(1000, 1, 1, "09:31", Map.of(
            "AAPL", new BigDecimal("10.2500"),
            "GOOG", new BigDecimal("20.5000"),
            "NVDA", new BigDecimal("30.7500"))));
        var afterInsert = repository.state();
        check(afterInsert.rows() == beforeFailure.rows() + 3, "Committed three-row batch");
        check(repository.latest().stream().allMatch(q -> q.sequence() == 1000),
            "Latest values after batch");
        ds.close();

        ds = dataSource(directory);
        repository = new JooqQuoteRepository(ds, DSL.using(ds, org.jooq.SQLDialect.H2));
        repository.initialize();
        check(repository.state().equals(afterInsert), "State after database reopen");
        ds.close();

        for (String state : new String[] {"23505", "42000", null}) {
            var failure = JooqQuoteRepository.translate(new RuntimeException(new SQLException("test", state)));
            check(failure.kind() == ("23505".equals(state)
                ? RepositoryFailure.Kind.CONFLICT : RepositoryFailure.Kind.UNEXPECTED),
                "SQLState translation " + state);
        }
        var captured = Files.readString(sqlFile).toLowerCase(java.util.Locale.ROOT);
        check(captured.contains("select") && captured.contains("insert into"),
            "Generated SQL capture includes selects and inserts");
        System.out.println("PASS: fixture, mapping, ordering, batch rollback/commit, SQLState translation, restart persistence");
        System.out.println("SQL_CAPTURE=" + sqlFile);
    }
}
