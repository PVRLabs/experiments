package pvrlabs;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import tools.jackson.databind.ObjectMapper;

@Controller
public class DashboardController {
    private static final String[] COLORS = {"#38bdf8", "#f59e0b", "#e879f9", "#4ade80", "#fb7185"};
    private final StarsService stars;
    private final ObjectMapper json;

    public DashboardController(StarsService stars, ObjectMapper json) {
        this.stars = stars;
        this.json = json;
    }

    @GetMapping("/")
    public String dashboard(Model model) {
        List<Card> cards = new ArrayList<>();
        List<Dataset> datasets = new ArrayList<>();
        Instant now = Instant.now();
        int color = 0;
        for (String repo : stars.repos()) {
            List<StarsService.Observation> history = stars.history(repo);
            StarsService.Observation latest = history.isEmpty() ? null : history.get(0);
            String paint = COLORS[color++ % COLORS.length];
            cards.add(new Card(repo, latest == null ? null : latest.stars(),
                    latest == null ? "Never" : relative(latest.at(), now), paint,
                    "https://github.com/" + repo));
            List<Point> points = new ArrayList<>();
            for (int i = history.size() - 1; i >= 0; i--) {
                var observation = history.get(i);
                points.add(new Point(observation.at().toEpochMilli(), observation.stars()));
            }
            datasets.add(new Dataset(repo, paint, points, latest == null ? null : latest.stars()));
        }
        model.addAttribute("cards", cards);
        model.addAttribute("chartJson", json.writeValueAsString(new Chart(datasets)));
        model.addAttribute("repoCount", cards.size());
        model.addAttribute("maxRepos", 5);
        return "index";
    }

    @PostMapping("/refresh")
    public String refresh() {
        stars.pollAll();
        return "redirect:/";
    }

    private static String relative(Instant then, Instant now) {
        long seconds = Math.max(0, Duration.between(then, now).toSeconds());
        if (seconds < 10) return "just now";
        if (seconds < 60) return seconds + "s ago";
        if (seconds < 3600) return seconds / 60 + "m ago";
        if (seconds < 172800) return seconds / 3600 + "h ago";
        return seconds / 86400 + "d ago";
    }

    public record Card(String repoName, Integer stars, String lastPolled, String color, String url) {}
    public record Point(long x, int y) {}
    public record Dataset(String label, String color, List<Point> points, Integer current) {}
    public record Chart(List<Dataset> datasets) {}
}
