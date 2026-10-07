package example;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.lang.management.ManagementFactory;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

// Example only: fixed mapping, no scrape parser or custom request instrumentation.
final class StatLiteSnapshot {
    static String json(MeterRegistry registry, String health) {
        double count = 0, notFound = 0, clientErrors = 0, serverErrors = 0, seconds = 0;
        for (Timer timer : registry.find("http.server.requests").timers()) {
            String uri = timer.getId().getTag("uri");
            // Exclude monitoring and demo control requests using the same timers for count and time.
            if ("/prometheus".equals(uri) || "/statlite/metrics".equals(uri)
                || "/demo/health/{status}".equals(uri)) continue;
            long n = timer.count();
            count += n;
            seconds += timer.totalTime(TimeUnit.SECONDS);
            String status = timer.getId().getTag("status");
            if ("404".equals(status)) notFound += n;
            if (status != null && status.startsWith("4")) clientErrors += n;
            if (status != null && status.startsWith("5")) serverErrors += n;
        }
        Map<String, Double> metrics = new LinkedHashMap<>();
        metrics.put("requests_total", count);
        metrics.put("responses_404_total", notFound);
        metrics.put("responses_4xx_total", clientErrors);
        metrics.put("responses_5xx_total", serverErrors);
        metrics.put("request_duration_seconds_total", seconds);
        double heap = 0;
        for (Gauge gauge : registry.find("jvm.memory.used").tag("area", "heap").gauges()) heap += gauge.value();
        put(metrics, "runtime_heap_used_bytes", heap);
        Gauge cpu = registry.find("process.cpu.usage").gauge();
        // Micrometer reports a fraction of visible CPU capacity; v1 requires cores.
        if (cpu != null) put(metrics, "process_cpu_usage", cpu.value() * Runtime.getRuntime().availableProcessors());
        Gauge hostCpu = registry.find("system.cpu.usage").gauge();
        if (hostCpu != null) put(metrics, "host_cpu_usage", hostCpu.value());
        var runtime = ManagementFactory.getRuntimeMXBean();
        put(metrics, "uptime_seconds", runtime.getUptime() / 1000.0);
        StringBuilder json = new StringBuilder("{\"schema\":\"statlite-metrics/v1\",\"integration\":\"javalin-demo\",\"status\":\"")
            .append(health).append("\",\"started_at\":\"").append(Instant.ofEpochMilli(runtime.getStartTime()))
            .append("\",\"metrics\":{");
        String separator = "";
        for (var entry : metrics.entrySet()) {
            json.append(separator).append('"').append(entry.getKey()).append("\":").append(entry.getValue());
            separator = ",";
        }
        return json.append("}}").toString();
    }

    private static void put(Map<String, Double> metrics, String name, double value) {
        if (Double.isFinite(value) && value >= 0) metrics.put(name, value);
    }
}
