package lab;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service
public class QuoteService {
    private final QuoteRepository repository;

    public QuoteService(QuoteRepository repository) {  this.repository=repository; }
    public List<Quotes.Quote> latest() { return repository.latest(); }
    public List<Quotes.Quote> history(String symbol,int limit) {
        if (symbol==null || !Quotes.SYMBOLS.contains(symbol) || limit<1 || limit>390) throw new IllegalArgumentException("Invalid symbol/limit");
        return repository.history(symbol,limit);
    }
    @Transactional
    public Map<String,Integer> insert(Quotes.Batch batch) {
        Quotes.validate(batch);
        repository.insert(batch);
        return Map.of("sequence",batch.sequence());
    }
    public Map<String,Object> state() { return repository.state(); }
}
