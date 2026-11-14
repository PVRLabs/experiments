package pvrlabs.poll;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.Test;

import pvrlabs.github.GithubClient;
import pvrlabs.github.RepoSnapshot;
import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;
import pvrlabs.repository.ProjectRepository;
import pvrlabs.repository.StarHistoryRepository;

import java.time.Instant;
import java.util.Optional;

/** Focused reference semantics; does not substitute for database transaction tests. */
class StarPollWriterTest {
    private final GithubClient github = mock(GithubClient.class);
    private final ProjectRepository projects = mock(ProjectRepository.class);
    private final StarHistoryRepository history = mock(StarHistoryRepository.class);
    private final StarPollWriter writer = new StarPollWriter(github, projects, history);
    private final Instant now = Instant.parse("2026-01-01T00:00:00Z");

    private Project existing(int stars) {
        Project project = new Project();
        project.setRepoName("test/repo");
        project.setCurrentStars(stars);
        when(projects.findByRepoName("test/repo")).thenReturn(Optional.of(project));
        return project;
    }

    @Test
    void unchangedStarsStillUpdateOtherFields() {
        Project project = existing(10);
        when(github.fetchSnapshot("test/repo"))
                .thenReturn(Optional.of(new RepoSnapshot(10, 3, 4, now)));
        assertFalse(writer.pollOne("test/repo", now));
        assertEquals(3, project.getCurrentForks());
        assertEquals(4, project.getCurrentWatchers());
        assertEquals(now, project.getLastPushedAt());
        assertEquals(now, project.getLastPolledAt());
        verify(history, never()).save(any());
    }

    @Test
    void changedStarsAppendHistory() {
        Project project = existing(10);
        when(github.fetchSnapshot("test/repo"))
                .thenReturn(Optional.of(new RepoSnapshot(11, 3, 4, now)));
        assertTrue(writer.pollOne("test/repo", now));
        var row = org.mockito.ArgumentCaptor.forClass(StarHistory.class);
        verify(history).save(row.capture());
        assertSame(project, row.getValue().getProject());
        assertEquals(11, row.getValue().getStarCount());
        assertEquals(now, row.getValue().getRecordedAt());
    }

    @Test
    void notModifiedOnlyAdvancesPollTimestamp() {
        Project project = existing(10);
        when(github.fetchSnapshot("test/repo")).thenReturn(Optional.empty());
        assertFalse(writer.pollOne("test/repo", now));
        assertEquals(10, project.getCurrentStars());
        assertEquals(now, project.getLastPolledAt());
        verify(history, never()).save(any());
    }
}
