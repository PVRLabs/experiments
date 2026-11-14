package pvrlabs.stargazer;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class DashboardController {

    private static final String[] COLORS = {"#38bdf8", "#f59e0b", "#e879f9", "#4ade80", "#fb7185"};

    private final Store store;
    private final List<String> repos;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public DashboardController(Store store, List<String> repos) {
        this.store = store;
        this.repos = repos;
    }

    public Map<String, Object> dashboard() throws JsonProcessingException {
        Map<String, Object> model = new LinkedHashMap<>();
        Instant now = Instant.now();

        List<Project> projects = repos.isEmpty() ? List.of() : store.projects(repos);

        Map<String, Project> byName = new LinkedHashMap<>();
        for (Project project : projects) {
            byName.put(project.getRepoName(), project);
        }

        List<ProjectCard> cards = new ArrayList<>();
        for (int i = 0; i < repos.size(); i++) {
            String repo = repos.get(i);
            Project project = byName.get(repo);
            cards.add(toCard(repo, project, COLORS[i % COLORS.length], now));
        }

        model.put("cards", cards);
        model.put("chartJson", objectMapper.writeValueAsString(toChart(cards, projects)));
        model.put("repoCount", repos.size());
        model.put("maxRepos", 4);
        return model;
    }

    private ProjectCard toCard(String repo, Project project, String color, Instant now) {
        if (project == null) {
            return new ProjectCard(
                    repo, null, null, null, "—", "Waiting for first poll", color, githubUrl(repo));
        }
        return new ProjectCard(
                repo,
                project.getCurrentStars(),
                project.getCurrentForks(),
                project.getCurrentWatchers(),
                relative(project.getLastPushedAt(), now),
                relative(project.getLastPolledAt(), now),
                color,
                githubUrl(repo));
    }

    private ChartPayload toChart(List<ProjectCard> cards, List<Project> projects) {
        List<Long> ids = projects.stream().map(Project::getId).toList();
        List<StarHistory> rows = ids.isEmpty() ? List.of() : store.history(ids);

        Map<Long, String> names = new LinkedHashMap<>();
        for (Project project : projects) {
            names.put(project.getId(), project.getRepoName());
        }

        Map<String, ChartDataset> datasets = new LinkedHashMap<>();
        for (ProjectCard card : cards) {
            datasets.put(
                    card.repoName(),
                    new ChartDataset(
                            card.repoName(), card.color(), new ArrayList<>(), card.stars()));
        }

        for (StarHistory row : rows) {
            String repo = names.get(row.getProject().getId());
            ChartDataset dataset = datasets.get(repo);
            if (dataset == null) {
                continue;
            }
            dataset.points()
                    .add(new ChartPoint(row.getRecordedAt().toEpochMilli(), row.getStarCount()));
        }

        return new ChartPayload(new ArrayList<>(datasets.values()));
    }

    static String relative(Instant then, Instant now) {
        if (then == null) {
            return "Never";
        }
        long seconds = Math.max(0, Duration.between(then, now).getSeconds());
        if (seconds < 10) {
            return "just now";
        }
        if (seconds < 60) {
            return seconds + "s ago";
        }
        long minutes = seconds / 60;
        if (minutes < 60) {
            return minutes + "m ago";
        }
        long hours = minutes / 60;
        if (hours < 48) {
            return hours + "h ago";
        }
        return (hours / 24) + "d ago";
    }

    private static String githubUrl(String repo) {
        return "https://github.com/" + repo;
    }

    public record ProjectCard(
            String repoName,
            Integer stars,
            Integer forks,
            Integer watchers,
            String lastPushed,
            String lastPolled,
            String color,
            String url) {}

    public record ChartPoint(long x, int y) {}

    public record ChartDataset(
            String label, String color, List<ChartPoint> points, Integer current) {}

    public record ChartPayload(List<ChartDataset> datasets) {}
}
