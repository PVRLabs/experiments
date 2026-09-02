package pvrlabs.stars;

import io.quarkus.qute.Template;
import io.quarkus.qute.TemplateInstance;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.time.Duration;
import java.time.Instant;
import java.util.*;

@Path("/") @Produces(MediaType.TEXT_HTML)
public class DashboardResource {
    private static final String[] COLORS = {"#38bdf8", "#f59e0b", "#e879f9", "#4ade80"};
    @Inject Template index;
    @Inject GithubConfig config;
    @Inject StarPollService pollService;

    @GET public TemplateInstance dashboard() {
        List<String> repos = config.trackedRepos();
        List<Project> projects = repos.isEmpty() ? List.of() : Project.list("repoName in ?1 order by repoName", repos);
        Map<String, Project> byName = new HashMap<>(); projects.forEach(p -> byName.put(p.repoName, p));
        List<Card> cards = new ArrayList<>();
        for (int i = 0; i < repos.size(); i++) cards.add(card(repos.get(i), byName.get(repos.get(i)), COLORS[i % COLORS.length]));
        return index.data("cards", cards).data("repoCount", repos.size()).data("maxRepos", GithubConfig.MAX_REPOS)
                .data("chartJson", chartJson(cards, projects));
    }

    @POST @Path("refresh") public TemplateInstance refresh() { pollService.pollAll(); return dashboard(); }

    private Card card(String repo, Project p, String color) {
        return p == null ? new Card(repo, null, null, null, "—", "Waiting for first poll", color, githubUrl(repo), List.of())
                : new Card(repo, p.currentStars, p.currentForks, p.currentWatchers, relative(p.lastPushedAt), relative(p.lastPolledAt), color, githubUrl(repo), history(p));
    }
    private List<Point> history(Project p) { return StarHistory.<StarHistory>list("project = ?1 order by recordedAt, id", p).stream().map(h -> new Point(h.recordedAt.toEpochMilli(), h.starCount)).toList(); }
    private String chartJson(List<Card> cards, List<Project> projects) {
        StringBuilder out = new StringBuilder("{\"datasets\":[");
        for (int i = 0; i < cards.size(); i++) { if (i > 0) out.append(','); Card c = cards.get(i); out.append("{\"label\":\"").append(esc(c.repoName)).append("\",\"color\":\"").append(c.color).append("\",\"current\":").append(c.stars == null ? "null" : c.stars).append(",\"points\":["); for (int j = 0; j < c.points.size(); j++) { if (j > 0) out.append(','); Point p = c.points.get(j); out.append("{\"x\":").append(p.x).append(",\"y\":").append(p.y).append('}'); } out.append("]}"); }
        return out.append("]}").toString();
    }
    private static String esc(String s) { return s.replace("\\", "\\\\").replace("\"", "\\\""); }
    static String relative(Instant then) { if (then == null) return "Never"; long seconds = Math.max(0, Duration.between(then, Instant.now()).getSeconds()); if (seconds < 10) return "just now"; if (seconds < 60) return seconds + "s ago"; long minutes = seconds / 60; if (minutes < 60) return minutes + "m ago"; long hours = minutes / 60; if (hours < 48) return hours + "h ago"; return (hours / 24) + "d ago"; }
    private static String githubUrl(String repo) { return "https://github.com/" + repo; }
    public record Card(String repoName, Integer stars, Integer forks, Integer watchers, String lastPushed, String lastPolled, String color, String url, List<Point> points) {}
    public record Point(long x, int y) {}
}
