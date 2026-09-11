package pvrlabs.github;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import pvrlabs.github.GithubClient.GithubFetchException;

class GithubClientTest {

    @Test
    void splitsOwnerAndRepo() {
        assertThat(GithubClient.splitOwnerRepo("spring-projects/spring-boot"))
                .containsExactly("spring-projects", "spring-boot");
    }

    @Test
    void rejectsMalformedRepoNames() {
        assertThatThrownBy(() -> GithubClient.splitOwnerRepo("nope"))
                .isInstanceOf(GithubFetchException.class);
        assertThatThrownBy(() -> GithubClient.splitOwnerRepo("/repo"))
                .isInstanceOf(GithubFetchException.class);
        assertThatThrownBy(() -> GithubClient.splitOwnerRepo("owner/"))
                .isInstanceOf(GithubFetchException.class);
    }
}
