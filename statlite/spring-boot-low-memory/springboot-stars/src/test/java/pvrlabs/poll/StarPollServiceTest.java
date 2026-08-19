package pvrlabs.poll;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import pvrlabs.github.GithubClient;
import pvrlabs.github.RepoSnapshot;
import pvrlabs.model.StarHistory;
import pvrlabs.repository.ProjectRepository;
import pvrlabs.repository.StarHistoryRepository;

@DataJpaTest
class StarPollServiceTest {

    @Autowired
    private ProjectRepository projectRepository;

    @Autowired
    private StarHistoryRepository historyRepository;

    private GithubClient githubClient;
    private StarPollWriter pollService;

    @BeforeEach
    void setUp() {
        githubClient = mock(GithubClient.class);
        pollService = new StarPollWriter(githubClient, projectRepository, historyRepository);
    }

    @Test
    void writesHistoryOnlyWhenStarCountChanges() {
        Instant t1 = Instant.parse("2026-08-18T10:00:00Z");
        Instant t2 = Instant.parse("2026-08-18T10:05:00Z");
        Instant t3 = Instant.parse("2026-08-18T10:10:00Z");

        Instant pushed = Instant.parse("2026-08-17T12:00:00Z");
        when(githubClient.fetchSnapshot("PVRLabs/statlite"))
                .thenReturn(
                        Optional.of(new RepoSnapshot(10, 2, 4, pushed)),
                        Optional.of(new RepoSnapshot(10, 3, 4, pushed)),
                        Optional.of(new RepoSnapshot(11, 3, 5, pushed)));

        assertThat(pollService.pollOne("PVRLabs/statlite", t1)).isTrue();
        assertThat(pollService.pollOne("PVRLabs/statlite", t2)).isFalse();
        assertThat(pollService.pollOne("PVRLabs/statlite", t3)).isTrue();

        var project = projectRepository.findByRepoName("PVRLabs/statlite").orElseThrow();
        assertThat(project.getCurrentStars()).isEqualTo(11);
        assertThat(project.getCurrentForks()).isEqualTo(3);
        assertThat(project.getCurrentWatchers()).isEqualTo(5);
        assertThat(project.getLastPushedAt()).isEqualTo(pushed);
        assertThat(project.getLastPolledAt()).isEqualTo(t3);

        List<StarHistory> history =
                historyRepository.findChartSeries(List.of(project.getId()));
        assertThat(history).hasSize(2);
        assertThat(history.get(0).getStarCount()).isEqualTo(10);
        assertThat(history.get(0).getRecordedAt()).isEqualTo(t1);
        assertThat(history.get(1).getStarCount()).isEqualTo(11);
        assertThat(history.get(1).getRecordedAt()).isEqualTo(t3);
    }

    @Test
    void notModifiedStillUpdatesLastPolledAtWithoutHistory() {
        Instant t1 = Instant.parse("2026-08-18T12:00:00Z");
        Instant t2 = Instant.parse("2026-08-18T12:05:00Z");

        when(githubClient.fetchSnapshot("PVRLabs/statlite"))
                .thenReturn(Optional.of(new RepoSnapshot(42, 8, 9, t1)), Optional.empty());

        pollService.pollOne("PVRLabs/statlite", t1);
        pollService.pollOne("PVRLabs/statlite", t2);

        var project = projectRepository.findByRepoName("PVRLabs/statlite").orElseThrow();
        assertThat(project.getCurrentStars()).isEqualTo(42);
        assertThat(project.getLastPolledAt()).isEqualTo(t2);
        assertThat(historyRepository.count()).isEqualTo(1);
    }
}
