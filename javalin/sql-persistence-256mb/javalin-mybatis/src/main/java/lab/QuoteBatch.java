package lab;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Set;
public record QuoteBatch(Integer sequence, Integer cycle, Integer sampleIndex, String marketTime, Map<String, BigDecimal> prices) {
    public static final List<String> SYMBOLS = List.of("AAPL", "GOOG", "NVDA");
    public void validate() {
        if (sequence == null || sequence < 390 || cycle == null || cycle < 1 || sampleIndex == null || sampleIndex < 0 || sampleIndex > 389 || marketTime == null || !marketTime.matches("(?:09:[3-5][0-9]|1[0-5]:[0-5][0-9])") || prices == null || !prices.keySet().equals(Set.copyOf(SYMBOLS)))
            throw new IllegalArgumentException("Invalid batch");
        for (var price : prices.values())
            if (price == null || price.signum() <= 0 || price.scale() > 4 || price.compareTo(new BigDecimal("100000000")) >= 0)
                throw new IllegalArgumentException("Invalid price");
    }
    public static void validateHistory(String symbol, int limit) {
        if (symbol == null || !SYMBOLS.contains(symbol) || limit < 1 || limit > 390)
            throw new IllegalArgumentException("Invalid symbol/limit");
    }
}
