package pvrlabs.stars;

import io.quarkus.hibernate.orm.panache.PanacheEntity;
import jakarta.persistence.*;
import java.time.Instant;

@Entity @Table(name = "star_history")
public class StarHistory extends PanacheEntity {
    @ManyToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "project_id", nullable = false)
    public Project project;
    @Column(name = "star_count", nullable = false) public Integer starCount;
    @Column(name = "recorded_at", nullable = false) public Instant recordedAt;
}
