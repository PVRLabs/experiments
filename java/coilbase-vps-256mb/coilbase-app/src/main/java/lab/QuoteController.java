package lab;
import io.avaje.http.api.*;
import java.util.*;
@Controller
public class QuoteController {
    private final QuoteService service;
    public QuoteController(QuoteService service) { this.service=service; }
    @Get("/ready") public Object ready() { return Map.of("status","UP"); }
    @Get("/api/quotes/latest") public Object latest() { return service.latest(); }
    @Get("/api/quotes/history") public Object history(@QueryParam String symbol, @QueryParam String limit) {
        int count;
        try { count=limit==null ? 60 : Integer.parseInt(limit); }
        catch(NumberFormatException e) { throw new IllegalArgumentException("Invalid symbol/limit"); }
        return service.history(symbol,count);
    }
    @Post("/api/quotes/batches") @Produces(statusCode=201)
    public Object batch(Quotes.Batch batch) { return service.insert(batch); }
    @Get("/inspection/state") public Object state() { return service.state(); }
}
