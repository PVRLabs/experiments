package pvrlabs.poolreclaim;

import com.zaxxer.hikari.HikariDataSource;
import java.sql.Connection;
import java.time.Instant;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
class WorkController {
    private static final Logger log = LoggerFactory.getLogger(WorkController.class);
    private final HikariDataSource pool;
    private final String instance;
    private final String applicationName;
    private final int holdMs;
    private final int gateTimeoutMs;
    private final Map<String, Wave> waves = new HashMap<>();

    WorkController(HikariDataSource pool, @Value("${spring.application.name}") String instance,
            @Value("${PG_APP_NAME:pool-A}") String applicationName,
            @Value("${experiment.hold-ms:1000}") int holdMs,
            @Value("${experiment.gate-timeout-ms:5000}") int gateTimeoutMs) {
        if (holdMs < 0 || holdMs > 2000 || gateTimeoutMs < 1 || gateTimeoutMs > 5000)
            throw new IllegalArgumentException("Invalid hold/gate duration");
        this.pool = pool;
        this.instance = instance;
        this.applicationName = applicationName;
        this.holdMs = holdMs;
        this.gateTimeoutMs = gateTimeoutMs;
    }

    @GetMapping("/experiment/state")
    Map<String, Object> state() {
        var bean = pool.getHikariPoolMXBean();
        return Map.ofEntries(Map.entry("instance", instance), Map.entry("applicationName", applicationName),
                Map.entry("poolName", pool.getPoolName()), Map.entry("minimumIdle", pool.getMinimumIdle()),
                Map.entry("maximumPoolSize", pool.getMaximumPoolSize()), Map.entry("idleTimeoutMs", pool.getIdleTimeout()),
                Map.entry("maxLifetimeMs", pool.getMaxLifetime()), Map.entry("keepaliveMs", pool.getKeepaliveTime()),
                Map.entry("connectionTimeoutMs", pool.getConnectionTimeout()), Map.entry("holdMs", holdMs),
                Map.entry("active", bean.getActiveConnections()), Map.entry("idle", bean.getIdleConnections()),
                Map.entry("total", bean.getTotalConnections()));
    }

    @GetMapping("/experiment/work")
    Map<String, Object> work(@RequestParam String wave, @RequestParam int request,
            @RequestParam(defaultValue = "10") int participants) throws Exception {
        if (!wave.matches("[a-zA-Z0-9_-]{1,64}") || (participants != 1 && participants != 10)
                || request < 0 || request >= participants)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid wave");
        Wave rendezvous = enter(wave, request, participants);
        long started = System.nanoTime();
        long startMs = System.currentTimeMillis();
        double acquisitionMs = -1;
        try {
            long acquiredMs;
            int backendPid;
            int activeAtGate;
            try (Connection connection = pool.getConnection()) {
                acquisitionMs = (System.nanoTime() - started) / 1_000_000.0;
                acquiredMs = System.currentTimeMillis();
                try (var statement = connection.createStatement()) {
                    statement.setQueryTimeout(5);
                    try (var rows = statement.executeQuery("SELECT pg_backend_pid(), 1")) {
                        if (!rows.next() || rows.getInt(2) != 1) throw new IllegalStateException("Query assertion failed");
                        backendPid = rows.getInt(1);
                    }
                }
                // Count only successfully borrowed connections, not incoming HTTP requests.
                rendezvous.acquired.countDown();
                if (!rendezvous.acquired.await(gateTimeoutMs, TimeUnit.MILLISECONDS))
                    throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Wave did not acquire all connections");
                activeAtGate = pool.getHikariPoolMXBean().getActiveConnections();
                try (var statement = connection.prepareStatement("SELECT pg_sleep(?)")) {
                    statement.setQueryTimeout(5);
                    statement.setDouble(1, holdMs / 1000.0);
                    statement.execute();
                }
            }
            long returnedMs = System.currentTimeMillis();
            log.info("work instance={} wave={} request={} pid={} acquisition_ms={} start_ms={} acquired_ms={} returned_ms={}",
                    instance, wave, request, backendPid, acquisitionMs, startMs, acquiredMs, returnedMs);
            return Map.ofEntries(Map.entry("instance", instance), Map.entry("wave", wave), Map.entry("request", request),
                    Map.entry("backendPid", backendPid), Map.entry("acquisitionMs", acquisitionMs),
                    Map.entry("startMs", startMs), Map.entry("acquiredMs", acquiredMs),
                    Map.entry("returnedMs", returnedMs), Map.entry("activeAtGate", activeAtGate), Map.entry("value", 1));
        } catch (Exception e) {
            log.warn("work failed instance={} wave={} request={} acquisition_ms={} kind={}",
                    instance, wave, request, acquisitionMs, e.getClass().getSimpleName());
            throw e;
        } finally {
            synchronized (waves) {
                rendezvous.finished++;
                if (rendezvous.finished == participants) waves.remove(wave, rendezvous);
            }
        }
    }

    private Wave enter(String id, int request, int participants) {
        synchronized (waves) {
            waves.entrySet().removeIf(entry -> entry.getValue().created.isBefore(Instant.now().minusSeconds(30)));
            Wave wave = waves.get(id);
            if (wave == null) {
                if (waves.size() >= 4) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "Too many waves");
                wave = new Wave(participants);
                waves.put(id, wave);
            }
            if (wave.participants != participants || !wave.requests.add(request))
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Duplicate or mismatched wave");
            return wave;
        }
    }

    private static class Wave {
        final int participants;
        final CountDownLatch acquired;
        final Set<Integer> requests = new HashSet<>();
        final Instant created = Instant.now();
        int finished;
        Wave(int participants) {
            this.participants = participants;
            acquired = new CountDownLatch(participants);
        }
    }
}
