package pvrlabs.marketreplay;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import pvrlabs.repository.Repository;
import pvrlabs.repository.RepositoryContext;
import pvrlabs.repository.SqlStatement;

final class QuoteRepository extends Repository {
    private static final String COLUMNS = "id, fetched_at, cycle, sample_index, market_time, symbol, price";
    private static final SqlStatement LATEST = SqlStatement.of("SELECT " + COLUMNS + " FROM (SELECT " + COLUMNS
            + ", ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY id DESC) AS position "
            + "FROM quote_samples) latest WHERE position = 1 ORDER BY symbol");
    private static final SqlStatement HISTORY = SqlStatement.of("SELECT " + COLUMNS + " FROM (SELECT " + COLUMNS
            + ", ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY id DESC) AS position "
            + "FROM quote_samples) recent WHERE position <= 390 ORDER BY id");
    private static final String INSERT = "INSERT INTO quote_samples"
            + "(fetched_at, cycle, sample_index, market_time, symbol, price) "
            + "VALUES (:fetchedAt, :cycle, :sampleIndex, :marketTime, :symbol, :price)";

    QuoteRepository(RepositoryContext db) {
        super(db);
    }

    void insert(Instant fetchedAt, QuoteBatch batch) {
        db.transactional(() -> {
            for (FixtureQuote quote : batch.quotes()) {
                db.useHandle(handle -> handle.createUpdate(INSERT)
                        .bind("fetchedAt", Timestamp.from(fetchedAt))
                        .bind("cycle", batch.cycle())
                        .bind("sampleIndex", batch.sampleIndex())
                        .bind("marketTime", batch.marketTime())
                        .bind("symbol", quote.symbol())
                        .bind("price", quote.price())
                        .execute());
            }
        });
    }

    List<QuoteObservation> latest() {
        return db.query(LATEST, query -> query.map((rs, ctx) -> map(rs)).list());
    }

    List<QuoteObservation> history() {
        return db.query(HISTORY, query -> query.map((rs, ctx) -> map(rs)).list());
    }

    long count() {
        return db.query("SELECT COUNT(*) FROM quote_samples", query -> query.mapTo(Long.class).one());
    }

    private static QuoteObservation map(ResultSet row) throws SQLException {
        return new QuoteObservation(
                row.getLong("id"),
                row.getTimestamp("fetched_at").toInstant(),
                row.getInt("cycle"),
                row.getInt("sample_index"),
                row.getString("market_time"),
                row.getString("symbol"),
                row.getBigDecimal("price"));
    }
}
