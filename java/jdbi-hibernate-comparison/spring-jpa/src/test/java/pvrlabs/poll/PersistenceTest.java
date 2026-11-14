package pvrlabs.poll;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import pvrlabs.github.*;
import pvrlabs.repository.*;

import java.time.Instant;
import java.util.Optional;

@SpringBootTest(
        properties = {
            "spring.datasource.url=jdbc:h2:mem:contract;DB_CLOSE_DELAY=-1",
            "app.github.initial-delay-ms=3600000"
        })
class PersistenceTest {
    @Autowired StarPollWriter writer;
    @Autowired ProjectRepository projects;
    @Autowired StarHistoryRepository history;
    @MockitoBean GithubClient github;

    @Test
    void databasePollingAndRollback() {
        String repo = "test/repo";
        var now = Instant.parse("2026-01-01T00:00:00Z");
        when(github.fetchSnapshot(repo)).thenReturn(Optional.of(new RepoSnapshot(10, 3, 4, now)));
        assertTrue(writer.pollOne(repo, now));
        assertFalse(writer.pollOne(repo, now.plusSeconds(1)));
        when(github.fetchSnapshot(repo)).thenReturn(Optional.of(new RepoSnapshot(11, 3, 4, now)));
        assertTrue(writer.pollOne(repo, now.plusSeconds(2)));
        when(github.fetchSnapshot(repo)).thenReturn(Optional.empty());
        assertFalse(writer.pollOne(repo, now.plusSeconds(3)));
        var project = projects.findByRepoName(repo).orElseThrow();
        assertEquals(11, project.getCurrentStars());
        assertEquals(3, project.getCurrentForks());
        assertEquals(4, project.getCurrentWatchers());
        assertEquals(now.plusSeconds(3), project.getLastPolledAt());
        assertEquals(2, history.count());
        when(github.fetchSnapshot(repo)).thenThrow(new IllegalStateException("injected"));
        assertThrows(RuntimeException.class, () -> writer.pollOne(repo, now.plusSeconds(4)));
        assertEquals(
                now.plusSeconds(3), projects.findByRepoName(repo).orElseThrow().getLastPolledAt());
        when(github.fetchSnapshot("rollback/new"))
                .thenThrow(new IllegalStateException("injected after insert"));
        assertThrows(RuntimeException.class, () -> writer.pollOne("rollback/new", now));
        assertTrue(projects.findByRepoName("rollback/new").isEmpty());
    }
}
