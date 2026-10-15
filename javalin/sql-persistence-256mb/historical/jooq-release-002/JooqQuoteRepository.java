package lab;

import static lab.jooq.generated.tables.Quotes.QUOTES;
import static org.jooq.impl.DSL.count;
import static org.jooq.impl.DSL.max;
import static org.jooq.impl.DSL.sum;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Objects;

import org.jooq.DSLContext;
import org.jooq.Query;
import org.jooq.impl.DSL;
import com.zaxxer.hikari.HikariDataSource;

public final class JooqQuoteRepository implements QuoteRepository {
    private final HikariDataSource dataSource;
    private final DSLContext dsl;

    public JooqQuoteRepository(HikariDataSource dataSource, DSLContext dsl) {
        this.dataSource = Objects.requireNonNull(dataSource);
        this.dsl = Objects.requireNonNull(dsl);
    }

    public void initialize() {
        operation(() -> {
            try (var stream = Objects.requireNonNull(getClass().getResourceAsStream("/schema.sql"));
                 var reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                var sql = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sql.append(line).append('\n');
                }
                for (String command : sql.toString().split(";")) {
                    if (!command.isBlank()) dsl.execute(command);
                }
            } catch (Exception e) {
                throw new IllegalStateException("Could not initialize quote schema", e);
            }
            return null;
        });

        if (operation(() -> dsl.fetchCount(QUOTES)) == 0) loadFixture();
        if (this.<Integer>operation(() -> (Integer) dsl.fetchValue("SELECT 1", Integer.class)) != 1) {
            throw new IllegalStateException("DB probe failed");
        }
        System.out.printf("Hikari min=%d max=%d connectionTimeout=%d validationTimeout=%d idleTimeout=%d maxLifetime=%d keepaliveTime=%d initializationFailTimeout=%d%n",
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getMinimumIdle(),
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getMaximumPoolSize(),
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getConnectionTimeout(),
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getValidationTimeout(),
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getIdleTimeout(),
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getMaxLifetime(),
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getKeepaliveTime(),
            ((com.zaxxer.hikari.HikariDataSource) dataSource).getInitializationFailTimeout());
    }

    private void loadFixture() {
        operation(() -> {
            try (var stream = Objects.requireNonNull(getClass().getResourceAsStream("/quotes.csv"));
                 var reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                reader.readLine();
                Query template = insertTemplate(dsl);
                var batch = dsl.batch(template);
                String line;
                int i = 0;
                while ((line = reader.readLine()) != null) {
                    var row = line.split(",");
                    batch.bind(i / 3, 0, i / 3, row[0], row[1], new BigDecimal(row[2]));
                    i++;
                }
                if (i != 1170) throw new IllegalStateException("Wrong fixture size " + i);
                batch.execute();
                return null;
            } catch (Exception e) {
                throw new IllegalStateException("Could not load quote fixture", e);
            }
        });
    }

    private static Query insertTemplate(DSLContext context) {
        return context.insertInto(QUOTES,
                QUOTES.BATCH_SEQ, QUOTES.CYCLE, QUOTES.SAMPLE_INDEX,
                QUOTES.MARKET_TIME, QUOTES.SYMBOL, QUOTES.PRICE)
            .values((Integer) null, null, null, null, null, null);
    }

    private static Quote map(org.jooq.Record row) {
        return new Quote(
            row.get(QUOTES.BATCH_SEQ), row.get(QUOTES.CYCLE), row.get(QUOTES.SAMPLE_INDEX),
            row.get(QUOTES.MARKET_TIME), row.get(QUOTES.SYMBOL), row.get(QUOTES.PRICE));
    }

    private <T> T operation(java.util.function.Supplier<T> action) {
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
                return new RepositoryFailure(state != null && state.startsWith("23")
                    ? RepositoryFailure.Kind.CONFLICT : RepositoryFailure.Kind.UNEXPECTED, cause);
            }
        }
        return new RepositoryFailure(RepositoryFailure.Kind.UNEXPECTED, cause);
    }

    @Override
    public List<Quote> latest() {
        return operation(() -> {
            var rows = new ArrayList<Quote>(QuoteBatch.SYMBOLS.size());
            for (String symbol : QuoteBatch.SYMBOLS) {
                var row = dsl.select(QUOTES.BATCH_SEQ, QUOTES.CYCLE, QUOTES.SAMPLE_INDEX,
                        QUOTES.MARKET_TIME, QUOTES.SYMBOL, QUOTES.PRICE)
                    .from(QUOTES).where(QUOTES.SYMBOL.eq(symbol))
                    .orderBy(QUOTES.ID.desc()).limit(1).fetchOne();
                if (row != null) rows.add(map(row));
            }
            return rows;
        });
    }

    @Override
    public List<Quote> history(String symbol, int limit) {
        QuoteBatch.validateHistory(symbol, limit);
        return operation(() -> {
            var rows = dsl.select(QUOTES.BATCH_SEQ, QUOTES.CYCLE, QUOTES.SAMPLE_INDEX,
                    QUOTES.MARKET_TIME, QUOTES.SYMBOL, QUOTES.PRICE)
                .from(QUOTES).where(QUOTES.SYMBOL.eq(symbol))
                .orderBy(QUOTES.ID.desc()).limit(limit).fetch(JooqQuoteRepository::map);
            Collections.reverse(rows);
            return rows;
        });
    }

    @Override
    public void insert(QuoteBatch batch) {
        if (batch == null) throw new IllegalArgumentException("Invalid batch");
        batch.validate();
        operation(() -> {
            dsl.transaction(configuration -> {
                DSLContext tx = DSL.using(configuration);
                var inserts = tx.batch(insertTemplate(tx));
                for (String symbol : QuoteBatch.SYMBOLS) {
                    inserts.bind(batch.sequence(), batch.cycle(), batch.sampleIndex(),
                        batch.marketTime(), symbol, batch.prices().get(symbol));
                }
                inserts.execute();
            });
            return null;
        });
    }

    @Override
    public QuoteState state() {
        return operation(() -> {
            var row = dsl.select(count(), max(QUOTES.BATCH_SEQ), sum(QUOTES.PRICE))
                .from(QUOTES).fetchOne();
            return new QuoteState(row.get(0, Integer.class), row.get(1, Integer.class),
                row.get(2, BigDecimal.class));
        });
    }
}
