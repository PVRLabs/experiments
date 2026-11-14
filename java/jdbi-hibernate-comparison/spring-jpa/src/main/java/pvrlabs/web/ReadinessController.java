package pvrlabs.web;

import org.springframework.web.bind.annotation.*;

import java.util.Map;

import javax.sql.DataSource;

@RestController
public class ReadinessController {
    private final DataSource source;

    public ReadinessController(DataSource source) {
        this.source = source;
    }

    @GetMapping("/ready")
    public Map<String, String> ready() throws java.sql.SQLException {
        try (var c = source.getConnection();
                var s = c.createStatement();
                var rows = s.executeQuery("select count(*) from projects")) {
            rows.next();
            return Map.of("status", "UP");
        }
    }

    @GetMapping("/diagnostics")
    public Map<String, Object> diagnostics() {
        return Diagnostics.snapshot(source);
    }
}
