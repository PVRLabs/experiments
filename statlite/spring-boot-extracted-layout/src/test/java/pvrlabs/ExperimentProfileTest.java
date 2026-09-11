package pvrlabs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.scheduling.annotation.ScheduledAnnotationBeanPostProcessor;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;
import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;
import pvrlabs.poll.StarPollScheduler;
import pvrlabs.repository.ProjectRepository;
import pvrlabs.repository.StarHistoryRepository;

@SpringBootTest
@ActiveProfiles("experiment")
class ExperimentProfileTest {

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private WebApplicationContext webApplicationContext;

    @Autowired
    private ProjectRepository projectRepository;

    @Autowired
    private StarHistoryRepository historyRepository;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.webAppContextSetup(webApplicationContext).build();
        historyRepository.deleteAllInBatch();
        projectRepository.deleteAllInBatch();

        Project project = new Project();
        project.setRepoName("PVRLabs/statlite");
        project.setCurrentStars(1234);
        project.setCurrentForks(56);
        project.setCurrentWatchers(78);
        project.setLastPushedAt(Instant.parse("2025-12-31T00:00:00Z"));
        project.setLastPolledAt(Instant.parse("2026-01-02T00:00:00Z"));
        project = projectRepository.saveAndFlush(project);

        StarHistory first = new StarHistory();
        first.setProject(project);
        first.setStarCount(1000);
        first.setRecordedAt(Instant.parse("2026-01-01T00:00:00Z"));

        StarHistory second = new StarHistory();
        second.setProject(project);
        second.setStarCount(1234);
        second.setRecordedAt(Instant.parse("2026-01-02T00:00:00Z"));
        historyRepository.saveAllAndFlush(List.of(first, second));
    }

    @Test
    void experimentProfileHasNoSchedulerAndSeedsLocalFixture() {
        assertThat(applicationContext.getBeansOfType(StarPollScheduler.class)).isEmpty();
        assertThat(applicationContext.getBeansOfType(ScheduledAnnotationBeanPostProcessor.class)).isEmpty();

        Project project = projectRepository.findByRepoName("PVRLabs/statlite").orElseThrow();
        assertThat(project.getCurrentStars()).isEqualTo(1234);
        assertThat(historyRepository.count()).isEqualTo(2);
    }

    @Test
    void dashboardReadsAndRendersTheLocalFixture() throws Exception {
        mockMvc.perform(get("/"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("PVRLabs/statlite")))
                .andExpect(content().string(containsString("1,234")))
                .andExpect(content().string(containsString("1000")));
    }
}
