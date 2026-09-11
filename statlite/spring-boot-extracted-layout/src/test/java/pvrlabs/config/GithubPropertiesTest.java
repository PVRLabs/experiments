package pvrlabs.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;

class GithubPropertiesTest {

    @Test
    void capsAtFourUniqueReposAndTrims() {
        GithubProperties properties = new GithubProperties();
        properties.setRepos(List.of(
                " PVRLabs/statlite ",
                "spring-projects/spring-boot",
                "PVRLabs/aibadger",
                "PVRLabs/statlite",
                "",
                "one/two",
                "three/four"));

        assertThat(properties.trackedRepos())
                .containsExactly(
                        "PVRLabs/statlite",
                        "spring-projects/spring-boot",
                        "PVRLabs/aibadger",
                        "one/two");
    }
}
