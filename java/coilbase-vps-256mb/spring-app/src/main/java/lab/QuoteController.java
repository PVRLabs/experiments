package lab;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@RestController
public class QuoteController {
    private final QuoteService quotes;
    private volatile boolean ready;
    public QuoteController(QuoteService quotes){this.quotes=quotes;}
    @EventListener(ApplicationReadyEvent.class) public void ready(){ready=true;}
    @GetMapping("/ready") ResponseEntity<?> readiness(){return ResponseEntity.status(ready?200:503).body(Map.of("status",ready?"UP":"DOWN"));}
    @GetMapping("/api/quotes/latest") Object latest() throws Exception{return quotes.latest();}
    @GetMapping("/api/quotes/history") Object history(@RequestParam String symbol,@RequestParam(defaultValue="60") int limit) throws Exception{return quotes.history(symbol,limit);}
    @PostMapping("/api/quotes/batches") ResponseEntity<?> batch(@RequestBody Quotes.Batch b) throws Exception{return ResponseEntity.status(201).body(quotes.insert(b));}
    @GetMapping("/inspection/state") Object state() throws Exception{return quotes.state();}
    @ExceptionHandler(IllegalArgumentException.class) ResponseEntity<?> bad(IllegalArgumentException e){return ResponseEntity.badRequest().body(Map.of("error",e.getMessage()));}
    @ExceptionHandler(org.springframework.dao.DuplicateKeyException.class) ResponseEntity<?> conflict(){return ResponseEntity.status(409).body(Map.of("error","conflict"));}
    @ExceptionHandler(java.sql.SQLException.class) ResponseEntity<?> sql(java.sql.SQLException e){return ResponseEntity.status(e.getSQLState()!=null && e.getSQLState().startsWith("23")?409:500).body(Map.of("error","database_error"));}
}
