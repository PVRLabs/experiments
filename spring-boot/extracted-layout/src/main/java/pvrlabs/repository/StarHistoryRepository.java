package pvrlabs.repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import pvrlabs.model.StarHistory;

public interface StarHistoryRepository extends JpaRepository<StarHistory, Long> {

    Optional<StarHistory> findTopByProjectIdOrderByRecordedAtDescIdDesc(Long projectId);

    @Query("""
            select h from StarHistory h
            join fetch h.project
            where h.project.id in :ids
            order by h.recordedAt asc, h.id asc
            """)
    List<StarHistory> findChartSeries(@Param("ids") Collection<Long> ids);
}
