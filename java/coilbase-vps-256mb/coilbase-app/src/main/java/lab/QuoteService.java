package lab;
import java.util.*;
import pvrlabs.coilbase.RepositoryContext;

public class QuoteService {
    private final QuoteRepository repository;
    private final RepositoryContext db;
    public QuoteService(RepositoryContext db, QuoteRepository repository) { this.db=db; this.repository=repository; }
    public List<Quotes.Quote> latest() { return repository.latest(); }
    public List<Quotes.Quote> history(String symbol,int limit) {
        if (symbol==null || !Quotes.SYMBOLS.contains(symbol) || limit<1 || limit>390) throw new IllegalArgumentException("Invalid symbol/limit");
        return repository.history(symbol,limit);
    }

    public Map<String,Integer> insert(Quotes.Batch batch) {
        Quotes.validate(batch);
        db.transactional(() -> repository.insert(batch));
        return Map.of("sequence",batch.sequence());
    }
    public Map<String,Object> state() { return repository.state(); }
}
