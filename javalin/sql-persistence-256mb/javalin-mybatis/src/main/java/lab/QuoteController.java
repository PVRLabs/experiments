package lab;
import io.javalin.config.JavalinConfig;
import java.util.Map;
public final class QuoteController {
    private final QuoteRepository repository;
    public QuoteController(QuoteRepository repository) { this.repository = repository; }
    public void register(JavalinConfig config) {
        config.routes.get("/api/quotes/latest", ctx -> ctx.json(repository.latest()));
        config.routes.get("/api/quotes/history", ctx -> {
            String symbol = ctx.queryParam("symbol"); int limit;
            try { limit = ctx.queryParam("limit") == null ? 60 : Integer.parseInt(ctx.queryParam("limit")); }
            catch (RuntimeException e) { throw new IllegalArgumentException("Invalid symbol/limit"); }
            QuoteBatch.validateHistory(symbol, limit);
            ctx.json(repository.history(symbol, limit));
        });
        config.routes.post("/api/quotes/batches", ctx -> {
            QuoteBatch batch;
            try { batch = ctx.bodyAsClass(QuoteBatch.class); }
            catch (Exception e) { throw new IllegalArgumentException("Invalid batch"); }
            if (batch == null) throw new IllegalArgumentException("Invalid batch");
            batch.validate(); repository.insert(batch);
            ctx.status(201).json(Map.of("sequence", batch.sequence()));
        });
        config.routes.get("/inspection/state", ctx -> ctx.json(repository.state()));
        config.routes.exception(IllegalArgumentException.class, (e, ctx) -> ctx.status(400).json(Map.of("error", e.getMessage())));
        config.routes.exception(RepositoryFailure.class, (e, ctx) -> {
            org.slf4j.LoggerFactory.getLogger(QuoteController.class).warn("Persistence failure", e);
            boolean conflict = e.kind() == RepositoryFailure.Kind.CONFLICT;
            ctx.status(conflict ? 409 : 500).json(Map.of("error", conflict ? "conflict" : "persistence_error"));
        });
    }
}
