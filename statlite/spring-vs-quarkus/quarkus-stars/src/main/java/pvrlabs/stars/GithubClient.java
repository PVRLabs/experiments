package pvrlabs.stars;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import jakarta.ws.rs.core.HttpHeaders;
import jakarta.ws.rs.core.Response;
import java.io.IOException;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import org.eclipse.microprofile.rest.client.inject.RestClient;

@ApplicationScoped
public class GithubClient {
    private static final String USER_AGENT = "pvrlabs-stars-quarkus";
    private static final String GITHUB_ACCEPT = "application/vnd.github+json";
    private final GithubConfig config;
    private final ObjectMapper mapper;
    private final GithubApi api;
    private final Map<String, String> etags = new ConcurrentHashMap<>();

    @Inject
    public GithubClient(GithubConfig config, ObjectMapper mapper, @RestClient GithubApi api) {
        this.config = config; this.mapper = mapper; this.api = api;
    }

    public Optional<RepoSnapshot> fetch(String repo) {
        String[] parts = splitOwnerRepo(repo);
        Response response = api.repository(parts[0], parts[1], config.token().isBlank() ? null : "Bearer " + config.token(),
                etags.get(repo), USER_AGENT, GITHUB_ACCEPT);
        try (response) {
            if (response.getStatus() == 304) return Optional.empty();
            if (response.getStatusInfo().getFamily() != Response.Status.Family.SUCCESSFUL) {
                throw new FetchException("GitHub " + response.getStatus() + " for " + repo);
            }
            String etag = response.getHeaderString(HttpHeaders.ETAG);
            if (etag != null) etags.put(repo, etag);
            JsonNode node = mapper.readTree(response.readEntity(String.class));
            if (!node.hasNonNull("stargazers_count")) throw new FetchException("Missing stargazers_count for " + repo);
            String pushed = node.path("pushed_at").asText("");
            return Optional.of(new RepoSnapshot(node.get("stargazers_count").asInt(), node.path("forks_count").asInt(), node.path("subscribers_count").asInt(), pushed.isBlank() ? null : Instant.parse(pushed)));
        } catch (IOException ex) { throw new FetchException("Invalid GitHub response for " + repo, ex); }
    }

    static String[] splitOwnerRepo(String repo) {
        int slash = repo == null ? -1 : repo.indexOf('/');
        if (slash <= 0 || slash == repo.length() - 1 || repo.indexOf('/', slash + 1) >= 0) throw new FetchException("Repository must be owner/name: " + repo);
        return new String[] {repo.substring(0, slash), repo.substring(slash + 1)};
    }

    public static class FetchException extends RuntimeException {
        public FetchException(String message) { super(message); }
        public FetchException(String message, Throwable cause) { super(message, cause); }
    }

    @RegisterRestClient(configKey = "github")
    public interface GithubApi {
        @jakarta.ws.rs.GET @jakarta.ws.rs.Path("/repos/{owner}/{repo}")
        Response repository(@jakarta.ws.rs.PathParam("owner") String owner, @jakarta.ws.rs.PathParam("repo") String repo,
                @jakarta.ws.rs.HeaderParam(HttpHeaders.AUTHORIZATION) String authorization,
                @jakarta.ws.rs.HeaderParam(HttpHeaders.IF_NONE_MATCH) String etag,
                @jakarta.ws.rs.HeaderParam(HttpHeaders.USER_AGENT) String userAgent,
                @jakarta.ws.rs.HeaderParam(HttpHeaders.ACCEPT) String accept);
    }
}
