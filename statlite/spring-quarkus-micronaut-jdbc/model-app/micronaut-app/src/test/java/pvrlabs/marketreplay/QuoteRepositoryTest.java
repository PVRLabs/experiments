package pvrlabs.marketreplay;

import static org.junit.jupiter.api.Assertions.*;
import java.math.BigDecimal;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class QuoteRepositoryTest {
    private QuoteRepository repository;

    @BeforeEach
    void database() throws Exception {
        JdbcDataSource datasource = new JdbcDataSource();
        datasource.setURL("jdbc:h2:mem:" + java.util.UUID.randomUUID() + ";DB_CLOSE_DELAY=-1");
        datasource.setUser("sa");
        repository = new QuoteRepository(datasource);
        repository.initialize();
    }

    private List<FixtureQuote> quotes() {
        return List.of(new FixtureQuote("AAPL", new BigDecimal("331.61")),
                new FixtureQuote("GOOG", new BigDecimal("341.91")),
                new FixtureQuote("NVDA", new BigDecimal("229.32")));
    }

    @Test
    void rollsBackAllRowsWhenThirdInsertFails() throws Exception {
        var valid = quotes();
        var batch = new QuoteBatch(0, "09:30", 0,
                List.of(valid.get(0), valid.get(1), new FixtureQuote("NVDA", null)));
        assertThrows(SQLException.class, () -> repository.insert(Instant.now(), batch));
        assertEquals(0, repository.count());
        repository.insert(Instant.now(), new QuoteBatch(0, "09:30", 0, valid));
        assertEquals(3, repository.count());
    }

    @Test
    void boundsHistoryPerSymbolAcrossCycleAndKeepsNewestRows() throws Exception {
        for (int index = 0; index < 391; index++) {
            repository.insert(Instant.now(), new QuoteBatch(index / 390,
                    java.time.LocalTime.of(9, 30).plusMinutes(index % 390).toString(), index % 390, quotes()));
        }
        assertEquals(1173, repository.count());
        var history = repository.history();
        assertEquals(1170, history.size());
        for (String symbol : List.of("AAPL", "GOOG", "NVDA")) {
            var rows = history.stream().filter(row -> symbol.equals(row.symbol())).toList();
            assertEquals(390, rows.size());
            assertEquals(1, rows.getFirst().sampleIndex());
            assertEquals(1, rows.getLast().cycle());
            assertEquals(0, rows.getLast().sampleIndex());
        }
        var latest = repository.latest();
        assertEquals(List.of("AAPL", "GOOG", "NVDA"), latest.stream().map(QuoteObservation::symbol).toList());
        assertTrue(latest.stream().allMatch(row -> row.cycle() == 1 && row.sampleIndex() == 0));
    }
}
