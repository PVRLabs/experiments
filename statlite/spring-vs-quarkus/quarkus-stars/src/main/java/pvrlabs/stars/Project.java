package pvrlabs.stars;

import io.quarkus.hibernate.orm.panache.PanacheEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity @Table(name = "projects")
public class Project extends PanacheEntity {
    @Column(name = "repo_name", nullable = false, unique = true) public String repoName;
    @Column(name = "current_stars") public Integer currentStars;
    @Column(name = "current_forks") public Integer currentForks;
    @Column(name = "current_watchers") public Integer currentWatchers;
    @Column(name = "last_pushed_at") public Instant lastPushedAt;
    @Column(name = "last_polled_at") public Instant lastPolledAt;
}
