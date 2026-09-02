package pvrlabs.stars;

import io.quarkus.scheduler.Scheduled;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.transaction.Transactional;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.jboss.logging.Logger;

@ApplicationScoped
public class StarPollService {
    private static final Logger LOG = Logger.getLogger(StarPollService.class);
    private final GithubConfig config;
    private final GithubClient github;

    public StarPollService(GithubConfig config, GithubClient github) { this.config = config; this.github = github; }

    @Scheduled(every = "{app.github.poll-interval}", delayed = "3s")
    void scheduledPoll() { pollAll(); }

    public PollSummary pollAll() {
        int recorded = 0, unchanged = 0, failed = 0;
        List<String> repos = config.trackedRepos();
        for (String repo : repos) try {
            if (pollOne(repo, Instant.now())) recorded++; else unchanged++;
        } catch (RuntimeException ex) { failed++; LOG.warnf("Poll failed for %s: %s", repo, ex.getMessage()); }
        PollSummary summary = new PollSummary(repos.size(), recorded, unchanged, failed);
        LOG.infof("Poll cycle complete: %s", summary);
        return summary;
    }

    @Transactional
    public boolean pollOne(String repoName, Instant now) {
        Project project = Project.find("repoName", repoName).firstResult();
        if (project == null) { project = new Project(); project.repoName = repoName; project.persist(); }
        Optional<RepoSnapshot> fetched = github.fetch(repoName);
        project.lastPolledAt = now;
        if (fetched.isEmpty()) return false;
        RepoSnapshot snapshot = fetched.get();
        Integer previous = StarHistory.find("project = ?1 order by recordedAt desc, id desc", project).firstResultOptional()
                .map(row -> ((StarHistory) row).starCount).orElse(project.currentStars);
        project.currentStars = snapshot.stars(); project.currentForks = snapshot.forks();
        project.currentWatchers = snapshot.watchers(); project.lastPushedAt = snapshot.pushedAt();
        if (previous != null && previous == snapshot.stars()) return false;
        StarHistory row = new StarHistory(); row.project = project; row.starCount = snapshot.stars(); row.recordedAt = now; row.persist();
        return true;
    }

    public record PollSummary(int repos, int recorded, int unchanged, int failed) {}
}
