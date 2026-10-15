package lab;
import java.util.List;
public interface QuoteRepository {
    List<Quote> latest();
    List<Quote> history(String symbol, int limit);
    void insert(QuoteBatch batch);
    QuoteState state();
}
