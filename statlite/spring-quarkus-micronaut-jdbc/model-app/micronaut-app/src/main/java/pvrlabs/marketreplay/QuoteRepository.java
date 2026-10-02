package pvrlabs.marketreplay;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import javax.sql.DataSource;
import jakarta.inject.Singleton;
import jakarta.inject.Inject;

@Singleton
public class QuoteRepository {
    private static final String COLUMNS = "id, fetched_at, cycle, sample_index, market_time, symbol, price";
    private final DataSource datasource;

    @Inject
    public QuoteRepository(DataSource datasource) {
        this.datasource = datasource;
    }

    public void initialize() throws SQLException, IOException {
        try (var resource = getClass().getResourceAsStream("/schema.sql")) {
            if (resource == null) throw new IOException("schema.sql is missing");
            String schema = new String(resource.readAllBytes(), StandardCharsets.UTF_8);
            try (Connection connection = datasource.getConnection(); Statement statement = connection.createStatement()) {
                for (String sql : schema.split(";")) {
                    if (!sql.isBlank()) statement.execute(sql);
                }
            }
        }
    }

    public void insert(Instant fetchedAt, QuoteBatch batch) throws SQLException {
        try (Connection connection = datasource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                try (PreparedStatement statement = connection.prepareStatement(
                        "INSERT INTO quote_samples(fetched_at, cycle, sample_index, market_time, symbol, price) VALUES (?, ?, ?, ?, ?, ?)")) {
                    for (FixtureQuote quote : batch.quotes()) {
                        statement.setTimestamp(1, Timestamp.from(fetchedAt));
                        statement.setInt(2, batch.cycle());
                        statement.setInt(3, batch.sampleIndex());
                        statement.setString(4, batch.marketTime());
                        statement.setString(5, quote.symbol());
                        statement.setBigDecimal(6, quote.price());
                        statement.executeUpdate();
                    }
                }
                connection.commit();
            } catch (SQLException | RuntimeException exception) {
                try { connection.rollback(); } catch (SQLException rollback) { exception.addSuppressed(rollback); }
                throw exception;
            } finally {
                connection.setAutoCommit(true);
            }
        }
    }

    public List<QuoteObservation> latest() throws SQLException {
        return query("SELECT " + COLUMNS + " FROM (SELECT " + COLUMNS
                + ", ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY id DESC) AS position "
                + "FROM quote_samples) latest WHERE position = 1 ORDER BY symbol");
    }

    public List<QuoteObservation> history() throws SQLException {
        return query("SELECT " + COLUMNS + " FROM (SELECT " + COLUMNS
                + ", ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY id DESC) AS position "
                + "FROM quote_samples) recent WHERE position <= 390 ORDER BY id");
    }

    public long count() throws SQLException {
        try (Connection connection = datasource.getConnection(); Statement statement = connection.createStatement();
                ResultSet row = statement.executeQuery("SELECT COUNT(*) FROM quote_samples")) {
            row.next();
            return row.getLong(1);
        }
    }

    private List<QuoteObservation> query(String sql) throws SQLException {
        try (Connection connection = datasource.getConnection(); Statement statement = connection.createStatement();
                ResultSet rows = statement.executeQuery(sql)) {
            List<QuoteObservation> result = new ArrayList<>();
            while (rows.next()) result.add(new QuoteObservation(rows.getLong("id"), rows.getTimestamp("fetched_at").toInstant(),
                    rows.getInt("cycle"), rows.getInt("sample_index"), rows.getString("market_time"),
                    rows.getString("symbol"), rows.getBigDecimal("price")));
            return result;
        }
    }
}
