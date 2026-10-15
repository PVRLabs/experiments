package lab;
import java.math.BigDecimal;
public record Quote(int sequence, int cycle, int sampleIndex, String marketTime, String symbol, BigDecimal price) {}
