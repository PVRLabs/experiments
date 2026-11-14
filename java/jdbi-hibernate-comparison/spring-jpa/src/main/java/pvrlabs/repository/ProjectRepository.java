package pvrlabs.repository;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import pvrlabs.model.Project;

public interface ProjectRepository extends JpaRepository<Project, Long> {

    Optional<Project> findByRepoName(String repoName);

    List<Project> findByRepoNameInOrderByRepoNameAsc(List<String> repoNames);
}
