package pvrlabs.stargazer;

import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;

import java.time.Instant;
import java.util.List;

public final class PollService {
    private final Store store;
    private final Github github;
    private final List<String> repos;

    public PollService(Store store, Github github, List<String> repos) {
        this.store = store;
        this.github = github;
        this.repos = repos;
    }

    public record Summary(int repos, int recorded, int unchanged, int failed) {}

    public Summary pollAll() {
        int recorded = 0;
        int unchanged = 0;
        int failed = 0;
        for (String repository : repos) {
            try {
                if (pollOne(repository, Instant.now())) {
                    recorded++;
                } else {
                    unchanged++;
                }
            } catch (RuntimeException failure) {
                failed++;
                System.getLogger(getClass().getName())
                        .log(System.Logger.Level.WARNING, "Poll failed for " + repository, failure);
            }
        }
        return new Summary(repos.size(), recorded, unchanged, failed);
    }

    // Each repository commits independently, so a failed poll cannot undo another.
    public boolean pollOne(String repositoryName, Instant now) {
        return store.transaction(
                () -> {
                    Project project = store.find(repositoryName);
                    if (project == null) {
                        project = new Project();
                        project.setRepoName(repositoryName);
                        store.save(project);
                    }
                    var fetched = github.fetch(repositoryName);
                    project.setLastPolledAt(now);
                    // A 304 advances the poll timestamp without adding history.
                    if (fetched.isEmpty()) {
                        store.save(project);
                        return false;
                    }
                    var snapshot = fetched.get();
                    Integer previous = store.latest(project);
                    project.setCurrentStars(snapshot.stars());
                    project.setCurrentForks(snapshot.forks());
                    project.setCurrentWatchers(snapshot.watchers());
                    project.setLastPushedAt(snapshot.pushedAt());
                    store.save(project);
                    if (previous != null && previous == snapshot.stars()) {
                        return false;
                    }
                    var history = new StarHistory();
                    history.setProject(project);
                    history.setStarCount(snapshot.stars());
                    history.setRecordedAt(now);
                    store.append(history);
                    return true;
                });
    }
}
