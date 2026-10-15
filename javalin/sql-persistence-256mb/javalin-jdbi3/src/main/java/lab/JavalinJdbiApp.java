package lab;
import com.zaxxer.hikari.HikariDataSource;
import io.javalin.Javalin;
import io.javalin.micrometer.MicrometerPlugin;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics;
import io.micrometer.core.instrument.binder.system.ProcessorMetrics;
import org.jdbi.v3.core.Jdbi;
import java.util.Map;
public final class JavalinJdbiApp {
    public static void main(String[] args) throws Exception {
        var registry = new SimpleMeterRegistry();
        new JvmMemoryMetrics().bindTo(registry); new ProcessorMetrics().bindTo(registry);
        var ds = new HikariDataSource();
        ds.setJdbcUrl("jdbc:h2:file:" + System.getProperty("run.dir") + "/quotes;CACHE_SIZE=4096;DB_CLOSE_ON_EXIT=FALSE");
        ds.setUsername("sa"); ds.setPassword(""); ds.setMinimumIdle(1); ds.setMaximumPoolSize(2);
        ds.setConnectionTimeout(3000); ds.setValidationTimeout(1000);
        var repository = new JdbiQuoteRepository(Jdbi.create(ds)); repository.initialize(ds);
        var controller = new QuoteController(repository);
        var app = Javalin.create(c -> {
            c.jetty.host = "127.0.0.1";
            c.registerPlugin(new MicrometerPlugin(p -> p.registry = registry));
            c.routes.get("/ready", ctx -> ctx.json(Map.of("status", "UP")));
            controller.register(c);
            c.routes.get(StatLiteMetrics.PATH, ctx -> ctx.json(StatLiteMetrics.snapshot(registry, "UP")));
        }).start(8080);
        System.out.println("Jetty thread pool: " + app.jettyServer().server().getThreadPool());
        Runtime.getRuntime().addShutdownHook(new Thread(() -> { app.stop(); ds.close(); registry.close(); }));
    }
}
