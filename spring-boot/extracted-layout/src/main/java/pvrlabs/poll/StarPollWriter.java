package pvrlabs.poll;

import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import pvrlabs.github.GithubClient;
import pvrlabs.github.RepoSnapshot;
import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;
import pvrlabs.repository.ProjectRepository;
import pvrlabs.repository.StarHistoryRepository;

/**
 * One repo, one transaction. Invoked through the Spring proxy from
 * {@link StarPollService} so a failure cannot mark another repo's work rollback-only.
 */
@Service
public class StarPollWriter {

    private static final Logger log = LoggerFactory.getLogger(StarPollWriter.class);

    private final GithubClient githubClient;
    private final ProjectRepository projectRepository;
    private final StarHistoryRepository historyRepository;

    public StarPollWriter(
            GithubClient githubClient,
            ProjectRepository projectRepository,
            StarHistoryRepository historyRepository) {
        this.githubClient = githubClient;
        this.projectRepository = projectRepository;
        this.historyRepository = historyRepository;
    }

    /**
     * Fetch current stars for one repo. Always updates {@code last_polled_at} on a
     * successful GitHub response (including 304). Appends {@code star_history}
     * only when the star count differs from the last stored value.
     *
     * @return true if a history row was written
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public boolean pollOne(String repoName, Instant now) {
        Project project = projectRepository
                .findByRepoName(repoName)
                .orElseGet(() -> createProject(repoName));

        Optional<RepoSnapshot> fetched = githubClient.fetchSnapshot(repoName);
        project.setLastPolledAt(now);

        if (fetched.isEmpty()) {
            projectRepository.save(project);
            return false;
        }

        RepoSnapshot snapshot = fetched.get();
        Integer previous = latestStarCount(project);
        project.setCurrentStars(snapshot.stars());
        project.setCurrentForks(snapshot.forks());
        project.setCurrentWatchers(snapshot.watchers());
        project.setLastPushedAt(snapshot.pushedAt());
        projectRepository.save(project);

        int stars = snapshot.stars();
        if (previous != null && previous == stars) {
            return false;
        }

        StarHistory row = new StarHistory();
        row.setProject(project);
        row.setStarCount(stars);
        row.setRecordedAt(now);
        historyRepository.save(row);
        log.info("Recorded history for {} : {} → {}", repoName, previous, stars);
        return true;
    }

    private Integer latestStarCount(Project project) {
        if (project.getId() == null) {
            return project.getCurrentStars();
        }
        return historyRepository
                .findTopByProjectIdOrderByRecordedAtDescIdDesc(project.getId())
                .map(StarHistory::getStarCount)
                .orElse(project.getCurrentStars());
    }

    private Project createProject(String repoName) {
        Project project = new Project();
        project.setRepoName(repoName);
        return projectRepository.save(project);
    }
}
