package example;

import io.javalin.Javalin;
import io.javalin.micrometer.MicrometerPlugin;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics;
import io.micrometer.core.instrument.binder.system.ProcessorMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.concurrent.atomic.AtomicReference;

public final class Application {
    static final AtomicReference<String> health = new AtomicReference<>("UP");

    public static void setReady(boolean ready) {
        health.set(ready ? "UP" : "DOWN");
    }

    public static void main(String[] args) {
        MeterRegistry registry = new SimpleMeterRegistry();
        new JvmMemoryMetrics().bindTo(registry);
        new ProcessorMetrics().bindTo(registry);

        Javalin app = Javalin.create(config -> {
            config.jetty.host = "127.0.0.1";
            config.registerPlugin(new MicrometerPlugin(plugin -> plugin.registry = registry));
            config.routes.get("/hello", ctx -> ctx.result("hello"));
            config.routes.get("/slow", ctx -> {
                Thread.sleep(120);
                ctx.result("slow");
            });
            config.routes.get("/error", ctx -> {
                throw new IllegalStateException("deliberate demo error");
            });
            config.routes.exception(IllegalStateException.class,
                (error, ctx) -> ctx.status(500).result("deliberate error"));
            config.routes.post("/demo/health/{status}", ctx -> {
                String status = ctx.pathParam("status");
                if (!status.equals("UP") && !status.equals("DOWN")) {
                    ctx.status(400).result("Use UP or DOWN");
                    return;
                }
                setReady(status.equals("UP"));
                ctx.result(status);
            });
            config.routes.get(StatLiteMetrics.PATH, ctx -> {
                ctx.header("Cache-Control", "no-store");
                ctx.json(StatLiteMetrics.snapshot(registry, health.get()));
            });
        }).start(18087);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            app.stop();
            registry.close();
        }));
    }
}
