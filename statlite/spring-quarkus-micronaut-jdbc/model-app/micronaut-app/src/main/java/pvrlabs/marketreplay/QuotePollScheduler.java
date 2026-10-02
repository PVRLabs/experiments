package pvrlabs.marketreplay;

import jakarta.inject.Singleton;
import jakarta.annotation.PreDestroy;
import io.micronaut.context.annotation.Value;
import io.micronaut.context.event.ApplicationEventListener;
import io.micronaut.runtime.event.ApplicationStartupEvent;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Singleton
public class QuotePollScheduler implements ApplicationEventListener<ApplicationStartupEvent> {
    private static final Logger log = LoggerFactory.getLogger(QuotePollScheduler.class);
    private final QuoteSyncService syncService;
    private final QuoteRepository repository;
    private final long interval;
    private final long initialDelay;
    private ScheduledExecutorService executor;

    public QuotePollScheduler(QuoteSyncService syncService, QuoteRepository repository,
            @Value("${market.poll-interval-ms:60000}") long interval,
            @Value("${market.poll-initial-delay-ms:0}") long initialDelay) {
        this.syncService = syncService;
        this.repository = repository;
        this.interval = interval;
        this.initialDelay = initialDelay;
    }

    @Override
    public void onApplicationEvent(ApplicationStartupEvent event) {
        if (interval <= 0 || initialDelay < 0) throw new IllegalArgumentException("invalid poll timing");
        try { repository.initialize(); } catch (Exception exception) {
            throw new IllegalStateException("Cannot initialize market database", exception);
        }
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

    @PreDestroy
    void stop() {
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
