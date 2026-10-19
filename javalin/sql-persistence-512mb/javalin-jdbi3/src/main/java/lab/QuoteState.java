package lab;
import java.math.BigDecimal;
public record QuoteState(int rows, int maxSequence, BigDecimal priceSum) {}
