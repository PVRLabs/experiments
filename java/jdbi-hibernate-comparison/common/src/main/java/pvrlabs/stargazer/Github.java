package pvrlabs.stargazer;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public final class Github {
    public record Snapshot(int stars, int forks, int watchers, Instant pushedAt) {}

    private final HttpClient client =
            HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
    private final ObjectMapper mapper = new ObjectMapper();
    private final Map<String, String> etags = new ConcurrentHashMap<>();
    private final String baseUrl;
    private final String token;

    public Github(String baseUrl, String token) {
        this.baseUrl = baseUrl;
        this.token = token;
    }

    public Optional<Snapshot> fetch(String repositoryName) {
        if (repositoryName == null || !repositoryName.matches("[^/]+/[^/]+")) {
            throw new IllegalArgumentException("Repository must be owner/name: " + repositoryName);
        }
        try {
            var request =
                    HttpRequest.newBuilder(URI.create(baseUrl + "/repos/" + repositoryName))
                            .timeout(Duration.ofSeconds(30))
                            .header("User-Agent", "pvrlabs-stars-demo")
                            .header("Accept", "application/vnd.github+json");
            if (token != null && !token.isBlank()) {
                request.header("Authorization", "Bearer " + token.trim());
            }
            if (etags.containsKey(repositoryName)) {
                request.header("If-None-Match", etags.get(repositoryName));
            }
            var response = client.send(request.build(), HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() == 304) {
                return Optional.empty();
            }
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new IllegalStateException(
                        "GitHub " + response.statusCode() + " for " + repositoryName);
            }
            response.headers()
                    .firstValue("ETag")
                    .ifPresent(etag -> etags.put(repositoryName, etag));
            var node = mapper.readTree(response.body());
            if (!node.hasNonNull("stargazers_count")) {
                throw new IllegalStateException("Missing stargazers_count");
            }
            var pushedAt = node.path("pushed_at").asText(null);
            return Optional.of(
                    new Snapshot(
                            node.get("stargazers_count").asInt(),
                            node.path("forks_count").asInt(0),
                            node.path("subscribers_count").asInt(0),
                            pushedAt == null || pushedAt.isBlank()
                                    ? null
                                    : Instant.parse(pushedAt)));
        } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(failure);
        } catch (java.io.IOException failure) {
            throw new IllegalStateException(failure);
        }
    }
}
