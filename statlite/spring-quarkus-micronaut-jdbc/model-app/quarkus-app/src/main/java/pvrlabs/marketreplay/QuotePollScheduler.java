package pvrlabs.marketreplay;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import jakarta.inject.Inject;
import io.quarkus.runtime.StartupEvent;
import io.quarkus.runtime.ShutdownEvent;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@ApplicationScoped
public class QuotePollScheduler {
    private static final Logger log = LoggerFactory.getLogger(QuotePollScheduler.class);
    @Inject QuoteSyncService syncService;
    @Inject QuoteRepository repository;
    @ConfigProperty(name = "market.poll-interval-ms", defaultValue = "60000") long interval;
    @ConfigProperty(name = "market.poll-initial-delay-ms", defaultValue = "0") long initialDelay;
    private ScheduledExecutorService executor;

    void start(@Observes StartupEvent event) throws Exception {
        if (interval <= 0 || initialDelay < 0) throw new IllegalArgumentException("invalid poll timing");
        repository.initialize();
        // Framework scheduler APIs are not consistent across Spring, Quarkus, and Micronaut,
        // and many applications use their own executors. Market Replay uses the same JDK
        // scheduled executor in all three ports so scheduling is held constant rather than
        // becoming part of the framework comparison.
        executor = Executors.newSingleThreadScheduledExecutor(runnable -> {
            Thread thread = new Thread(runnable, "market-poll");
            thread.setDaemon(false);
            return thread;
        });
        executor.scheduleWithFixedDelay(this::poll, initialDelay, interval, TimeUnit.MILLISECONDS);
    }

    void stop(@Observes ShutdownEvent event) {
        if (executor == null) return;
        executor.shutdownNow();
        try {
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                log.warn("Market quote scheduler did not stop within five seconds");
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
        }
    }

    private void poll() {
        try {
            syncService.pollOnce();
            log.info("Synchronized three market quotes");
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            log.info("Market quote poll interrupted");
        } catch (Exception exception) {
            log.warn("Market quote poll failed; the next scheduled poll will retry", exception);
        }
    }
}
