package pvrlabs.web;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import pvrlabs.config.GithubProperties;
import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;
import pvrlabs.poll.StarPollService;
import pvrlabs.repository.ProjectRepository;
import pvrlabs.repository.StarHistoryRepository;

@Controller
public class DashboardController {

    private static final String[] COLORS = {
        "#38bdf8", "#f59e0b", "#e879f9", "#4ade80", "#fb7185"
    };

    private final GithubProperties properties;
    private final ProjectRepository projectRepository;
    private final StarHistoryRepository historyRepository;
    private final StarPollService pollService;
    private final ObjectMapper objectMapper;

    public DashboardController(
            GithubProperties properties,
            ProjectRepository projectRepository,
            StarHistoryRepository historyRepository,
            StarPollService pollService,
            ObjectMapper objectMapper) {
        this.properties = properties;
        this.projectRepository = projectRepository;
        this.historyRepository = historyRepository;
        this.pollService = pollService;
        this.objectMapper = objectMapper;
    }

    @GetMapping("/")
    public String dashboard(Model model) throws JsonProcessingException {
        Instant now = Instant.now();
        List<String> repos = properties.trackedRepos();
        List<Project> projects = repos.isEmpty()
                ? List.of()
                : projectRepository.findByRepoNameInOrderByRepoNameAsc(repos);

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

        model.addAttribute("cards", cards);
        model.addAttribute("chartJson", objectMapper.writeValueAsString(toChart(cards, projects)));
        model.addAttribute("repoCount", repos.size());
        model.addAttribute("maxRepos", GithubProperties.MAX_REPOS);
        return "index";
    }

    @PostMapping("/refresh")
    public String refresh() {
        pollService.pollAll();
        return "redirect:/";
    }

    private ProjectCard toCard(String repo, Project project, String color, Instant now) {
        if (project == null) {
            return new ProjectCard(repo, null, null, null, "—", "Waiting for first poll", color, githubUrl(repo));
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
        List<StarHistory> rows = ids.isEmpty()
                ? List.of()
                : historyRepository.findChartSeries(ids);

        Map<Long, String> names = new LinkedHashMap<>();
        for (Project project : projects) {
            names.put(project.getId(), project.getRepoName());
        }

        Map<String, ChartDataset> datasets = new LinkedHashMap<>();
        for (ProjectCard card : cards) {
            datasets.put(
                    card.repoName(),
                    new ChartDataset(card.repoName(), card.color(), new ArrayList<>(), card.stars()));
        }

        for (StarHistory row : rows) {
            String repo = names.get(row.getProject().getId());
            ChartDataset dataset = datasets.get(repo);
            if (dataset == null) {
                continue;
            }
            dataset.points().add(new ChartPoint(row.getRecordedAt().toEpochMilli(), row.getStarCount()));
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

    public record ChartDataset(String label, String color, List<ChartPoint> points, Integer current) {}

    public record ChartPayload(List<ChartDataset> datasets) {}
}
