package pvrlabs.config;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.github")
public class GithubProperties {

    /** 4 repos × 12 polls/hour = 48, under GitHub's unauthenticated 60/hour cap. */
    public static final int MAX_REPOS = 4;

    /**
     * Comma-separated owner/repo values, e.g. PVRLabs/statlite.
     * Extra entries beyond {@link #MAX_REPOS} are ignored.
     */
    private List<String> repos = new ArrayList<>();

    private String apiBaseUrl = "https://api.github.com";

    private String token = "";

    public List<String> getRepos() {
        return repos;
    }

    public void setRepos(List<String> repos) {
        this.repos = repos == null ? new ArrayList<>() : repos;
    }

    public String getApiBaseUrl() {
        return apiBaseUrl;
    }

    public void setApiBaseUrl(String apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
    }

    public String getToken() {
        return token;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public List<String> trackedRepos() {
        LinkedHashSet<String> unique = new LinkedHashSet<>();
        for (String repo : repos) {
            if (repo == null) {
                continue;
            }
            String trimmed = repo.trim();
            if (!trimmed.isEmpty()) {
                unique.add(trimmed);
            }
            if (unique.size() >= MAX_REPOS) {
                break;
            }
        }
        return List.copyOf(unique);
    }

    public boolean hasToken() {
        return token != null && !token.isBlank();
    }
}
