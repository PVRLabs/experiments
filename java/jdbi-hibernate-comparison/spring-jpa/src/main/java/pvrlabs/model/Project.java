package pvrlabs.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "projects")
public class Project {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "repo_name", nullable = false, unique = true, length = 255)
    private String repoName;

    @Column(name = "current_stars")
    private Integer currentStars;

    @Column(name = "current_forks")
    private Integer currentForks;

    @Column(name = "current_watchers")
    private Integer currentWatchers;

    @Column(name = "last_pushed_at")
    private Instant lastPushedAt;

    @Column(name = "last_polled_at")
    private Instant lastPolledAt;

    public Long getId() {
        return id;
    }

    public String getRepoName() {
        return repoName;
    }

    public void setRepoName(String repoName) {
        this.repoName = repoName;
    }

    public Integer getCurrentStars() {
        return currentStars;
    }

    public void setCurrentStars(Integer currentStars) {
        this.currentStars = currentStars;
    }

    public Integer getCurrentForks() {
        return currentForks;
    }

    public void setCurrentForks(Integer currentForks) {
        this.currentForks = currentForks;
    }

    public Integer getCurrentWatchers() {
        return currentWatchers;
    }

    public void setCurrentWatchers(Integer currentWatchers) {
        this.currentWatchers = currentWatchers;
    }

    public Instant getLastPushedAt() {
        return lastPushedAt;
    }

    public void setLastPushedAt(Instant lastPushedAt) {
        this.lastPushedAt = lastPushedAt;
    }

    public Instant getLastPolledAt() {
        return lastPolledAt;
    }

    public void setLastPolledAt(Instant lastPolledAt) {
        this.lastPolledAt = lastPolledAt;
    }
}
