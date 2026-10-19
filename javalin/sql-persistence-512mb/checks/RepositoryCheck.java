import lab.*;
import com.zaxxer.hikari.HikariDataSource;
import org.jdbi.v3.core.Jdbi;
import java.math.BigDecimal;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;
import java.net.URI;
import java.net.http.*;
import io.javalin.Javalin;
public final class RepositoryCheck {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    public static void main(String[] args) throws Exception {
        for (String state : new String[]{"23505", "42000", null}) {
            var failure = JdbiQuoteRepository.translate(new RuntimeException(new SQLException("test", state)));
            check(failure.kind() == ("23505".equals(state) ? RepositoryFailure.Kind.CONFLICT : RepositoryFailure.Kind.UNEXPECTED), "Wrapped state " + state);
        }
        check(JdbiQuoteRepository.translate(new RuntimeException()).kind() == RepositoryFailure.Kind.UNEXPECTED, "Unclassified error");
        try (var ds = new HikariDataSource()) {
            ds.setJdbcUrl("jdbc:h2:file:" + args[0] + "/quotes;CACHE_SIZE=4096;DB_CLOSE_ON_EXIT=FALSE");
            ds.setUsername("sa"); ds.setPassword(""); ds.setMinimumIdle(1); ds.setMaximumPoolSize(2);
            ds.setConnectionTimeout(3000); ds.setValidationTimeout(1000);
            var jdbi = Jdbi.create(ds); var repo = new JdbiQuoteRepository(jdbi); repo.initialize(ds);
            check(repo.state().rows() == 1170, "Seed");
            jdbi.useHandle(h -> h.execute("INSERT INTO quotes(batch_seq,cycle,sample_index,market_time,symbol,price) VALUES(999,1,0,'09:30','GOOG',1)"));
            var before = repo.state();
            try { repo.insert(new QuoteBatch(999,1,0,"09:30",Map.of("AAPL",BigDecimal.ONE,"GOOG",BigDecimal.ONE,"NVDA",BigDecimal.ONE))); throw new AssertionError("Expected conflict"); }
            catch (RepositoryFailure expected) { check(expected.kind() == RepositoryFailure.Kind.CONFLICT, "Conflict category"); }
            check(repo.state().equals(before), "Partial batch rollback");
            check(repo.history("AAPL",60).size() == 60, "Valid history");
            try { repo.history(null,60); throw new AssertionError("Missing symbol"); } catch (IllegalArgumentException expected) {}
        }
        for (var kind : RepositoryFailure.Kind.values()) {
            QuoteRepository broken = new QuoteRepository() {
                public List<Quote> latest() { throw new RepositoryFailure(kind, new SQLException("test", (String)null)); }
                public List<Quote> history(String s,int l) { return latest(); }
                public void insert(QuoteBatch b) { latest(); }
                public QuoteState state() { return null; }
            };
            var controller = new QuoteController(broken);
            var app = Javalin.create(c -> { c.jetty.host="127.0.0.1"; controller.register(c); }).start(8081);
            try (var client = HttpClient.newHttpClient()) {
                var response = client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:8081/api/quotes/latest")).GET().build(), HttpResponse.BodyHandlers.ofString());
                check(response.statusCode() == (kind == RepositoryFailure.Kind.CONFLICT ? 409 : 500), "HTTP failure status");
                check(response.body().equals(kind == RepositoryFailure.Kind.CONFLICT ? "{\"error\":\"conflict\"}" : "{\"error\":\"persistence_error\"}"), "HTTP failure payload");
            } finally { app.stop(); }
        }
        System.out.println("PASS: seed, partial batch rollback, history, wrapped/null SQLState, portable HTTP 409/500");
    }
}
