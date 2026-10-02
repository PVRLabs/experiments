package pvrlabs.marketreplay;

import java.io.IOException;
import java.time.Instant;
import java.time.LocalTime;
import java.util.HashSet;
import java.util.Set;
import jakarta.inject.Singleton;
import jakarta.inject.Inject;
import java.sql.SQLException;

@Singleton
class QuoteSyncService {
    private final QuoteClient client;
    private final QuoteRepository repository;

    @Inject
    public QuoteSyncService(QuoteClient client, QuoteRepository repository) {
        this.client = client;
        this.repository = repository;
    }

    public void pollOnce() throws IOException, InterruptedException, SQLException {
        QuoteBatch batch = client.fetch();
        if (batch == null || batch.quotes() == null || batch.quotes().size() != 3) {
            throw new IOException("fixture response must contain exactly three quotes");
        }
        if (batch.cycle() < 0 || batch.sampleIndex() < 0 || batch.sampleIndex() >= 390
                || !LocalTime.of(9, 30).plusMinutes(batch.sampleIndex()).toString().equals(batch.marketTime())) {
            throw new IOException("fixture response has invalid replay metadata");
        }
        Set<String> symbols = new HashSet<>();
        for (FixtureQuote quote : batch.quotes()) {
            if (quote == null || (quote.symbol() == null || !Set.of("AAPL", "GOOG", "NVDA").contains(quote.symbol()))
                    || !symbols.add(quote.symbol()) || quote.price() == null
                    || quote.price().signum() <= 0 || quote.price().scale() > 4
                    || quote.price().compareTo(new java.math.BigDecimal("100000000")) >= 0) {
                throw new IOException("fixture response must contain one valid price each for AAPL, GOOG, and NVDA");
            }
        }
        repository.insert(Instant.now(), batch);
    }
}
