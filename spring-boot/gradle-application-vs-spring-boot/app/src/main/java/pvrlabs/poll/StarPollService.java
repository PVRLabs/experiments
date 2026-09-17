package pvrlabs.poll;

import java.time.Instant;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import pvrlabs.config.GithubProperties;

@Service
public class StarPollService {

    private static final Logger log = LoggerFactory.getLogger(StarPollService.class);

    private final GithubProperties properties;
    private final StarPollWriter writer;

    public StarPollService(GithubProperties properties, StarPollWriter writer) {
        this.properties = properties;
        this.writer = writer;
    }

    /**
     * Not transactional. Each repo is committed (or rolled back) on its own
     * via {@link StarPollWriter} so one failure cannot undo the others.
     */
    public PollSummary pollAll() {
        List<String> repos = properties.trackedRepos();
        int recorded = 0;
        int unchanged = 0;
        int failed = 0;
        for (String repo : repos) {
            try {
                if (writer.pollOne(repo, Instant.now())) {
                    recorded++;
                } else {
                    unchanged++;
                }
            } catch (RuntimeException ex) {
                failed++;
                log.warn("Poll failed for {}: {}", repo, ex.getMessage());
            }
        }
        PollSummary summary = new PollSummary(repos.size(), recorded, unchanged, failed);
        log.info("Poll cycle complete: {}", summary);
        return summary;
    }

    public record PollSummary(int repos, int recorded, int unchanged, int failed) {}
}
