// Source and updates: https://github.com/PVRLabs/statlite/blob/main/docs/integrate/java/javalin.md

package example;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.lang.management.ManagementFactory;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

public final class StatLiteMetrics {
    public static final String PATH = "/statlite/metrics";

    // Micrometer's uri tag is the matched route template.
    // PATH covers /statlite/metrics. Add other instrumentation routes if used.
    private static final Set<String> EXCLUDED_URIS = Set.of(PATH);

    private StatLiteMetrics() {}

    public static Map<String, Object> snapshot(MeterRegistry registry, String status) {
        if (status == null || status.isBlank()) {
            throw new IllegalArgumentException("StatLite application status must not be empty");
        }

        double requests = 0;
        double notFound = 0;
        double clientErrors = 0;
        double serverErrors = 0;
        double seconds = 0;
        for (Timer timer : registry.find("http.server.requests").timers()) {
            String uri = timer.getId().getTag("uri");
            if (uri != null && EXCLUDED_URIS.contains(uri)) {
                continue;
            }
            long count = timer.count();
            requests += count;
            seconds += timer.totalTime(TimeUnit.SECONDS);
            String code = timer.getId().getTag("status");
            if ("404".equals(code)) {
                notFound += count;
            }
            if (code != null && code.startsWith("4")) {
                clientErrors += count;
            }
            if (code != null && code.startsWith("5")) {
                serverErrors += count;
            }
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("requests_total", requests);
        metrics.put("responses_404_total", notFound);
        metrics.put("responses_4xx_total", clientErrors);
        metrics.put("responses_5xx_total", serverErrors);
        metrics.put("request_duration_seconds_total", seconds);

        double heap = 0;
        boolean heapSeen = false;
        for (Gauge gauge : registry.find("jvm.memory.used").tag("area", "heap").gauges()) {
            double value = gauge.value();
            if (Double.isFinite(value) && value >= 0) {
                heap += value;
                heapSeen = true;
            }
        }
        if (heapSeen) {
            metrics.put("runtime_heap_used_bytes", heap);
        }

        Gauge cpu = registry.find("process.cpu.usage").gauge();
        if (cpu != null) {
            double cpuFraction = cpu.value();
            if (Double.isFinite(cpuFraction) && cpuFraction >= 0) {
                metrics.put(
                    "process_cpu_usage",
                    cpuFraction * Runtime.getRuntime().availableProcessors());
            }
        }

        var runtime = ManagementFactory.getRuntimeMXBean();
        double uptimeSeconds = runtime.getUptime() / 1000.0;
        if (Double.isFinite(uptimeSeconds) && uptimeSeconds >= 0) {
            metrics.put("uptime_seconds", uptimeSeconds);
        }

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("schema", "statlite-metrics/v1");
        body.put("integration", "javalin");
        body.put("status", status);
        body.put("started_at", Instant.ofEpochMilli(runtime.getStartTime()).toString());
        body.put("metrics", metrics);
        return body;
    }
}
