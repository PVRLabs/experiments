package pvrlabs.marketreplay;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

record QuoteBatch(int cycle, String marketTime, int sampleIndex, List<FixtureQuote> quotes) {}

record FixtureQuote(String symbol, BigDecimal price) {}

record QuoteObservation(
        long id,
        Instant fetchedAt,
        int cycle,
        int sampleIndex,
        String marketTime,
        String symbol,
        BigDecimal price) {}
