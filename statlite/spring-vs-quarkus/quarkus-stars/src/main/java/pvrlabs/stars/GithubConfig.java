package pvrlabs.stars;

import jakarta.enterprise.context.ApplicationScoped;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class GithubConfig {
    public static final int MAX_REPOS = 4;
    @ConfigProperty(name = "app.github.repos") String repos;
    @ConfigProperty(name = "app.github.token", defaultValue = " ") String token;

    public List<String> trackedRepos() {
        LinkedHashSet<String> unique = new LinkedHashSet<>();
        if (repos != null) for (String value : Arrays.asList(repos.split(","))) {
            String trimmed = value.trim();
            if (!trimmed.isEmpty()) unique.add(trimmed);
            if (unique.size() == MAX_REPOS) break;
        }
        return List.copyOf(unique);
    }

    public String token() {
        String configured = token == null ? "" : token.trim();
        if (!configured.isBlank()) return configured;
        String environment = System.getenv("GITHUB_TOKEN");
        return environment == null ? "" : environment.trim();
    }
}
