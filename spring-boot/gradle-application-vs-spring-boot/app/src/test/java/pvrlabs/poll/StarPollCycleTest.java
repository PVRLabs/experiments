package pvrlabs.poll;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.List;
import org.junit.jupiter.api.Test;
import pvrlabs.config.GithubProperties;

class StarPollCycleTest {

    @Test
    void oneFailedRepoDoesNotStopTheCycle() {
        GithubProperties properties = new GithubProperties();
        properties.setRepos(List.of("a/one", "b/two"));
        StarPollWriter writer = mock(StarPollWriter.class);
        when(writer.pollOne(eq("a/one"), any())).thenThrow(new RuntimeException("boom"));
        when(writer.pollOne(eq("b/two"), any())).thenReturn(true);

        StarPollService.PollSummary summary = new StarPollService(properties, writer).pollAll();

        assertThat(summary.failed()).isEqualTo(1);
        assertThat(summary.recorded()).isEqualTo(1);
        assertThat(summary.unchanged()).isZero();
    }
}
