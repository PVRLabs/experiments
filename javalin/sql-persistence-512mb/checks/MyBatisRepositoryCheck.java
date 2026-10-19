package lab;

import java.math.BigDecimal;
import java.nio.file.Path;
import java.sql.SQLException;
import java.util.Map;

import org.apache.ibatis.mapping.Environment;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.session.LocalCacheScope;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory;

import com.zaxxer.hikari.HikariDataSource;

public final class MyBatisRepositoryCheck {
    private static void check(boolean passed, String message) {
        if (!passed) throw new AssertionError(message);
    }

    private static SqlSessionFactory factory(HikariDataSource ds) {
        var environment = new Environment("h2", new JdbcTransactionFactory(), ds);
        var configuration = new Configuration(environment);
        configuration.setLocalCacheScope(LocalCacheScope.STATEMENT);
        configuration.addMapper(QuoteMapper.class);
        return new SqlSessionFactoryBuilder().build(configuration);
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
        for (String state : new String[] {"23505", "42000", null}) {
            var failure = MyBatisQuoteRepository.translate(
                new RuntimeException(new SQLException("test", state)));
            check(failure.kind() == ("23505".equals(state)
                ? RepositoryFailure.Kind.CONFLICT
                : RepositoryFailure.Kind.UNEXPECTED), "SQLState " + state);
        }

        var directory = Path.of(args[0]).toAbsolutePath();
        var ds = dataSource(directory);
        var repository = new MyBatisQuoteRepository(factory(ds));
        repository.initialize(ds);
        check(repository.state().rows() == 1170, "Fixture row count");
        check(repository.latest().size() == 3, "Latest quote count");
        check(repository.history("AAPL", 390).size() == 390, "History size");
        check(repository.history("AAPL", 390).getLast().sequence() == 389,
            "History ordering");

        try (var session = factory(ds).openSession()) {
            session.getMapper(QuoteMapper.class).insert(
                999, 1, 0, "09:30", "GOOG", BigDecimal.ONE);
            session.commit();
        }
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
        repository = new MyBatisQuoteRepository(factory(ds));
        repository.initialize(ds);
        check(repository.state().equals(afterInsert), "State after database reopen");
        ds.close();
        System.out.println("PASS: fixture, mapping, ordering, batch rollback/commit, SQLState translation, restart persistence");
    }
}
