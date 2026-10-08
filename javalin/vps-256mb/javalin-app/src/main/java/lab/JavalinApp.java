package lab;
import io.javalin.Javalin;
import io.javalin.micrometer.MicrometerPlugin;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics;
import io.micrometer.core.instrument.binder.system.ProcessorMetrics;
import java.util.Map;
public final class JavalinApp {
    public static void main(String[] args) throws Exception {
        var registry=new SimpleMeterRegistry();new JvmMemoryMetrics().bindTo(registry);new ProcessorMetrics().bindTo(registry);
        var ds=Quotes.dataSource();var quotes=new Quotes(ds);
        var app=Javalin.create(c->{
            c.jetty.host="127.0.0.1";
            c.registerPlugin(new MicrometerPlugin(p->p.registry=registry));
            c.routes.get("/ready",ctx->ctx.json(Map.of("status","UP")));
            c.routes.get("/api/quotes/latest",ctx->ctx.json(quotes.latest()));
            c.routes.get("/api/quotes/history",ctx->ctx.json(quotes.history(ctx.queryParam("symbol"),Integer.parseInt(ctx.queryParamAsClass("limit",String.class).getOrDefault("60")))));
            c.routes.post("/api/quotes/batches",ctx->ctx.status(201).json(quotes.insert(ctx.bodyAsClass(Quotes.Batch.class))));
            c.routes.get("/inspection/state",ctx->ctx.json(quotes.state()));
            c.routes.get(StatLiteMetrics.PATH,ctx->ctx.json(StatLiteMetrics.snapshot(registry,"UP")));
            c.routes.exception(IllegalArgumentException.class,(e,ctx)->ctx.status(400).json(Map.of("error",e.getMessage())));
            c.routes.exception(java.sql.SQLException.class,(e,ctx)->ctx.status(e.getSQLState().startsWith("23")?409:500).json(Map.of("error",e.getSQLState())));
        }).start(8080);
        System.out.println("Jetty thread pool: " + app.jettyServer().server().getThreadPool());
        Runtime.getRuntime().addShutdownHook(new Thread(()->{app.stop();ds.close();registry.close();}));
    }
}
