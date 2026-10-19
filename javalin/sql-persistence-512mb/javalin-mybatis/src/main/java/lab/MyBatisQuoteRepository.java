package lab;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Objects;
import java.util.function.Supplier;

import org.apache.ibatis.session.ExecutorType;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;

import com.zaxxer.hikari.HikariDataSource;

public final class MyBatisQuoteRepository implements QuoteRepository {
    private final SqlSessionFactory sessions;

    public MyBatisQuoteRepository(SqlSessionFactory sessions) {
        this.sessions = Objects.requireNonNull(sessions);
    }

    public void initialize(HikariDataSource ds) {
        try (var session = sessions.openSession(ExecutorType.SIMPLE, false)) {
            var mapper = session.getMapper(QuoteMapper.class);
            mapper.createTable();
            mapper.createIndex();
            session.commit();
        } catch (RuntimeException e) {
            throw translate(e);
        }

        int count = operation(() -> withMapper(QuoteMapper::count));
        if (count == 0) loadFixture();
        if (operation(() -> withMapper(QuoteMapper::probe)) != 1)
            throw new IllegalStateException("DB probe failed");
        operation(() -> withMapper(mapper -> {
            mapper.h2Settings().forEach(value -> System.out.println("H2 " + value));
            return null;
        }));
        System.out.printf(
            "Hikari min=%d max=%d connectionTimeout=%d validationTimeout=%d idleTimeout=%d maxLifetime=%d keepaliveTime=%d initializationFailTimeout=%d%n",
            ds.getMinimumIdle(), ds.getMaximumPoolSize(), ds.getConnectionTimeout(),
            ds.getValidationTimeout(), ds.getIdleTimeout(), ds.getMaxLifetime(),
            ds.getKeepaliveTime(), ds.getInitializationFailTimeout());
    }

    private void loadFixture() {
        try (var stream = Objects.requireNonNull(getClass().getResourceAsStream("/quotes.csv"));
             var reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            loadFixture(sessions, reader);
        } catch (IOException e) {
            throw new IllegalStateException("Could not load quote fixture", e);
        }
    }

    static void loadFixture(SqlSessionFactory sessions, BufferedReader reader) throws IOException {
        try (var session = sessions.openSession(ExecutorType.BATCH, false)) {
            try {
                var mapper = session.getMapper(QuoteMapper.class);
                reader.readLine();
                String line;
                int i = 0;
                while ((line = reader.readLine()) != null) {
                    var row = line.split(",");
                    mapper.insert(i / 3, 0, i / 3, row[0], row[1], new BigDecimal(row[2]));
                    i++;
                }
                if (i != 1170) throw new IllegalStateException("Wrong fixture size " + i);
                session.flushStatements();
                session.commit();
            } catch (IOException | RuntimeException e) {
                rollback(session, e);
                throw e;
            }
        } catch (RuntimeException e) {
            throw translate(e);
        }
    }

    private <T> T withMapper(java.util.function.Function<QuoteMapper, T> action) {
        try (SqlSession session = sessions.openSession(ExecutorType.SIMPLE, true)) {
            return action.apply(session.getMapper(QuoteMapper.class));
        }
    }

    private <T> T operation(Supplier<T> action) {
        try {
            return action.get();
        } catch (RepositoryFailure e) {
            throw e;
        } catch (RuntimeException e) {
            throw translate(e);
        }
    }

    static RepositoryFailure translate(Throwable cause) {
        var seen = Collections.newSetFromMap(new IdentityHashMap<Throwable, Boolean>());
        for (Throwable t = cause; t != null && seen.add(t); t = t.getCause()) {
            if (t instanceof SQLException sql) {
                String state = sql.getSQLState();
                return new RepositoryFailure(
                    state != null && state.startsWith("23")
                        ? RepositoryFailure.Kind.CONFLICT
                        : RepositoryFailure.Kind.UNEXPECTED,
                    cause);
            }
        }
        return new RepositoryFailure(RepositoryFailure.Kind.UNEXPECTED, cause);
    }

    @Override
    public List<Quote> latest() {
        return operation(() -> withMapper(mapper -> {
            var rows = new ArrayList<Quote>(QuoteBatch.SYMBOLS.size());
            for (var symbol : QuoteBatch.SYMBOLS) {
                var quote = mapper.selectQuotes(symbol, 1);
                if (quote != null) rows.add(quote);
            }
            return rows;
        }));
    }

    @Override
    public List<Quote> history(String symbol, int limit) {
        QuoteBatch.validateHistory(symbol, limit);
        return operation(() -> withMapper(mapper -> {
            var rows = mapper.selectHistory(symbol, limit);
            Collections.reverse(rows);
            return rows;
        }));
    }

    @Override
    public void insert(QuoteBatch batch) {
        if (batch == null) throw new IllegalArgumentException("Invalid batch");
        batch.validate();
        operation(() -> {
            try (SqlSession session = sessions.openSession(ExecutorType.BATCH, false)) {
                try {
                    var mapper = session.getMapper(QuoteMapper.class);
                    for (var symbol : QuoteBatch.SYMBOLS) {
                        mapper.insert(batch.sequence(), batch.cycle(), batch.sampleIndex(),
                            batch.marketTime(), symbol, batch.prices().get(symbol));
                    }
                    session.flushStatements();
                    session.commit();
                    return null;
                } catch (RuntimeException e) {
                    rollback(session, e);
                    throw e;
                }
            }
        });
    }

    @Override
    public QuoteState state() {
        return operation(() -> withMapper(QuoteMapper::state));
    }

    private static void rollback(SqlSession session, Exception failure) {
        try {
            session.rollback();
        } catch (RuntimeException rollbackFailure) {
            failure.addSuppressed(rollbackFailure);
        }
    }
}
