package pvrlabs.marketreplay;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record QuoteBatch(int cycle, String marketTime, int sampleIndex, List<FixtureQuote> quotes) {}
