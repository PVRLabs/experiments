package pvrlabs.stars;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class GithubClientTest {
    @Test void splitsOwnerAndRepo() { assertArrayEquals(new String[]{"spring-projects", "spring-boot"}, GithubClient.splitOwnerRepo("spring-projects/spring-boot")); }
    @Test void rejectsMalformedRepoNames() {
        assertThrows(GithubClient.FetchException.class, () -> GithubClient.splitOwnerRepo("nope"));
        assertThrows(GithubClient.FetchException.class, () -> GithubClient.splitOwnerRepo("/repo"));
        assertThrows(GithubClient.FetchException.class, () -> GithubClient.splitOwnerRepo("owner/"));
        assertThrows(GithubClient.FetchException.class, () -> GithubClient.splitOwnerRepo("a/b/c"));
    }
}
