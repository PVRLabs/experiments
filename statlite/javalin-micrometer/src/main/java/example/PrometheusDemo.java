package example;

import io.javalin.config.JavalinConfig;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.prometheusmetrics.PrometheusConfig;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;

// Keep the optional scrape dependency outside the normal registry path.
final class PrometheusDemo {
    static MeterRegistry registry() {
        return new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
    }

    static void route(JavalinConfig config, MeterRegistry registry) {
        config.routes.get("/prometheus", ctx -> ctx.contentType("text/plain; version=0.0.4; charset=utf-8")
            .result(((PrometheusMeterRegistry) registry).scrape()));
    }
}
