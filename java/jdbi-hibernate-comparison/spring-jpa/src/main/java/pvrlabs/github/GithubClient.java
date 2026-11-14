package pvrlabs.github;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import pvrlabs.config.GithubProperties;

/**
 * Thin GitHub REST client. In-memory ETags still send {@code If-None-Match}
 * so unchanged polls return 304 and skip the body. That exemption from the
 * primary rate limit applies only when the request is authenticated; without
 * a token every poll counts toward the 60 req/hour cap.
 */
@Component
public class GithubClient {

    private static final Logger log = LoggerFactory.getLogger(GithubClient.class);
    private static final String USER_AGENT = "pvrlabs-stars-demo";

    private final RestClient restClient;
    private final GithubProperties properties;
    private final ObjectMapper objectMapper;
    private final Map<String, String> etags = new ConcurrentHashMap<>();

    public GithubClient(RestClient.Builder builder, GithubProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        this.restClient = builder.baseUrl(properties.getApiBaseUrl()).build();
    }

    public Optional<RepoSnapshot> fetchSnapshot(String repoName) {
        String[] parts = splitOwnerRepo(repoName);
        return restClient.get()
                .uri("/repos/{owner}/{repo}", parts[0], parts[1])
                .headers(this::applyCommonHeaders)
                .headers(headers -> applyEtag(headers, repoName))
                .exchange((request, response) -> handle(repoName, response));
    }

    static String[] splitOwnerRepo(String repoName) {
        int slash = repoName == null ? -1 : repoName.indexOf('/');
        if (slash <= 0 || slash == repoName.length() - 1 || repoName.indexOf('/', slash + 1) >= 0) {
            throw new GithubFetchException("Repository must be owner/name: " + repoName);
        }
        return new String[] {repoName.substring(0, slash), repoName.substring(slash + 1)};
    }

    private void applyCommonHeaders(HttpHeaders headers) {
        headers.set(HttpHeaders.USER_AGENT, USER_AGENT);
        headers.set(HttpHeaders.ACCEPT, "application/vnd.github+json");
        if (properties.hasToken()) {
            headers.setBearerAuth(properties.getToken().trim());
        }
    }

    private void applyEtag(HttpHeaders headers, String repoName) {
        String etag = etags.get(repoName);
        if (etag != null) {
            headers.set(HttpHeaders.IF_NONE_MATCH, etag);
        }
    }

    private Optional<RepoSnapshot> handle(String repoName, RestClient.RequestHeadersSpec.ConvertibleClientHttpResponse response)
            throws IOException {
        HttpStatus status = HttpStatus.resolve(response.getStatusCode().value());
        String remaining = response.getHeaders().getFirst("X-RateLimit-Remaining");

        if (status == HttpStatus.NOT_MODIFIED) {
            log.debug("GitHub 304 for {} (rate remaining={})", repoName, remaining);
            return Optional.empty();
        }

        if (status == null || !status.is2xxSuccessful()) {
            String body = new String(response.getBody().readAllBytes());
            throw new GithubFetchException(
                    "GitHub " + response.getStatusCode().value() + " for " + repoName + ": " + abbreviate(body));
        }

        String etag = response.getHeaders().getETag();
        if (etag != null) {
            etags.put(repoName, etag);
        }

        JsonNode node = objectMapper.readTree(response.getBody());
        if (!node.hasNonNull("stargazers_count")) {
            throw new GithubFetchException("GitHub response for " + repoName + " missing stargazers_count");
        }

        RepoSnapshot snapshot = new RepoSnapshot(
                node.get("stargazers_count").asInt(),
                node.path("forks_count").asInt(0),
                node.path("subscribers_count").asInt(0),
                parseInstant(node.path("pushed_at").asText(null)));
        log.info(
                "Fetched {} → {} stars, {} forks, {} watchers (rate remaining={})",
                repoName,
                snapshot.stars(),
                snapshot.forks(),
                snapshot.watchers(),
                remaining);
        return Optional.of(snapshot);
    }

    private static Instant parseInstant(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return Instant.parse(value);
    }

    private static String abbreviate(String body) {
        if (body == null) {
            return "";
        }
        String trimmed = body.replaceAll("\\s+", " ").trim();
        return trimmed.length() <= 180 ? trimmed : trimmed.substring(0, 180) + "…";
    }

    public static final class GithubFetchException extends RuntimeException {
        public GithubFetchException(String message) {
            super(message);
        }
    }
}
