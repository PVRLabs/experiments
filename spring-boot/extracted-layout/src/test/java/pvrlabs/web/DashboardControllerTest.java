package pvrlabs.web;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class DashboardControllerTest {

    @Test
    void formatsRelativePollTimes() {
        Instant now = Instant.parse("2026-08-18T12:00:00Z");
        assertThat(DashboardController.relative(null, now)).isEqualTo("Never");
        assertThat(DashboardController.relative(now.minusSeconds(4), now)).isEqualTo("just now");
        assertThat(DashboardController.relative(now.minusSeconds(40), now)).isEqualTo("40s ago");
        assertThat(DashboardController.relative(now.minusSeconds(300), now)).isEqualTo("5m ago");
        assertThat(DashboardController.relative(now.minusSeconds(7200), now)).isEqualTo("2h ago");
    }
}
