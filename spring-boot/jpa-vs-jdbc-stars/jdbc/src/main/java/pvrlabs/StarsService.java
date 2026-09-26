package pvrlabs;

import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.JsonNode;

@Service
public class StarsService {
    private static final Logger log = LoggerFactory.getLogger(StarsService.class);
    private static final Pattern REPO = Pattern.compile("[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+");
    private final List<String> repos;
    private final RestClient github;
    private final JdbcTemplate jdbc;
    private final String token;

    public StarsService(@Value("${app.github.repos}") String configuredRepos,
                        @Value("${app.github.api-base-url}") String apiBaseUrl,
                        @Value("${app.github.token:}") String token,
                        JdbcTemplate jdbc) {
        LinkedHashSet<String> names = new LinkedHashSet<>();
        for (String value : configuredRepos.split(",")) {
            String name = value.trim();
            if (!REPO.matcher(name).matches()) {
                throw new IllegalArgumentException("Invalid GitHub repository: " + name);
            }
            names.add(name);
        }
        if (names.isEmpty() || names.size() > 5) {
            throw new IllegalArgumentException("Configure 1 to 5 GitHub repositories");
        }
        this.repos = List.copyOf(names);
        this.token = token;
        this.jdbc = jdbc;
        var requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(5000);
        requestFactory.setReadTimeout(5000);
        this.github = RestClient.builder().baseUrl(apiBaseUrl).requestFactory(requestFactory).build();
    }

    public List<String> repos() {
        return repos;
    }

    @Scheduled(fixedDelayString = "${app.poll.interval-ms:600000}",
            initialDelayString = "${app.poll.initial-delay-ms:3000}")
    public void scheduledPoll() {
        pollAll();
    }

    public synchronized void pollAll() {
        for (String repo : repos) {
            try {
                JsonNode response = github.get()
                        .uri("/repos/{owner}/{repo}", repo.split("/")[0], repo.split("/")[1])
                        .header(HttpHeaders.USER_AGENT, "star-pulse-jdbc")
                        .header(HttpHeaders.ACCEPT, "application/vnd.github+json")
                        .headers(headers -> {
                            if (!token.isBlank()) {
                                headers.setBearerAuth(token.trim());
                            }
                        })
                        .retrieve().body(JsonNode.class);
                if (response == null || !response.hasNonNull("stargazers_count")) {
                    throw new IllegalStateException("Missing stargazers_count");
                }
                int stars = response.get("stargazers_count").asInt();
                jdbc.update("INSERT INTO star_observation (repo_name, star_count, observed_at) VALUES (?, ?, ?)",
                        repo, stars, Instant.now());
            } catch (Exception ex) {
                log.warn("Poll failed for {}: {}", repo, ex.toString());
            }
        }
    }

    public List<Observation> history(String repo) {
        return jdbc.query("SELECT star_count, observed_at FROM star_observation "
                        + "WHERE repo_name = ? ORDER BY observed_at DESC, id DESC LIMIT 200",
                (rs, row) -> new Observation(rs.getTimestamp("observed_at").toInstant(),
                        rs.getInt("star_count")), repo);
    }

    public record Observation(Instant at, int stars) {}
}
