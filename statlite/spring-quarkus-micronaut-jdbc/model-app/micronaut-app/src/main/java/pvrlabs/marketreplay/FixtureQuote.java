package pvrlabs.marketreplay;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record FixtureQuote(String symbol, BigDecimal price) {}
