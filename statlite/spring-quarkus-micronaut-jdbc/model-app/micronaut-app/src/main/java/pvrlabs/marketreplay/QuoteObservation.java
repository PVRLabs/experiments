package pvrlabs.marketreplay;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record QuoteObservation(long id, Instant fetchedAt, int cycle, int sampleIndex, String marketTime, String symbol, BigDecimal price) {}
