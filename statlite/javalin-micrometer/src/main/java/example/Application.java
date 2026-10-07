package example;

import io.javalin.Javalin;
import io.javalin.micrometer.MicrometerPlugin;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.binder.jvm.JvmGcMetrics;
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics;
import io.micrometer.core.instrument.binder.jvm.JvmThreadMetrics;
import io.micrometer.core.instrument.binder.system.ProcessorMetrics;
import io.micrometer.core.instrument.binder.system.UptimeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.concurrent.atomic.AtomicReference;

public class Application {
    public static void main(String[] args) {
        boolean simple = args.length > 0 && args[0].equals("simple");
        MeterRegistry registry = simple ? new SimpleMeterRegistry()
            : PrometheusDemo.registry();
        new JvmMemoryMetrics().bindTo(registry);
        JvmGcMetrics gc = new JvmGcMetrics();
        gc.bindTo(registry);
        new JvmThreadMetrics().bindTo(registry);
        new UptimeMetrics().bindTo(registry);
        new ProcessorMetrics().bindTo(registry);
        // Explicit demo-owned readiness signal; no dependency-health inference.
        AtomicReference<String> health = new AtomicReference<>("UP");
        Javalin app = Javalin.create(config -> {
            config.jetty.host = "127.0.0.1";
            config.registerPlugin(new MicrometerPlugin(plugin -> plugin.registry = registry));
            config.routes.get("/hello", ctx -> ctx.result("hello"));
            config.routes.get("/slow", ctx -> { Thread.sleep(120); ctx.result("slow"); });
            config.routes.get("/error", ctx -> { throw new IllegalStateException("deliberate demo error"); });
            config.routes.exception(IllegalStateException.class, (e, ctx) -> ctx.status(500).result("deliberate error"));
            config.routes.post("/demo/health/{status}", ctx -> {
                String status = ctx.pathParam("status");
                if (!status.equals("UP") && !status.equals("DOWN")) { ctx.status(400); return; }
                health.set(status);
                ctx.result(status);
            });
            if (!simple) {
                PrometheusDemo.route(config, registry);
            }
            config.routes.get("/statlite/metrics", ctx -> ctx.contentType("application/json")
                .header("Cache-Control", "no-store").result(StatLiteSnapshot.json(registry, health.get())));
        }).start(18087);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> { app.stop(); gc.close(); registry.close(); }));
    }
}
