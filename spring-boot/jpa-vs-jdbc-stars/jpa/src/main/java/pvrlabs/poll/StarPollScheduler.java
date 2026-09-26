package pvrlabs.poll;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class StarPollScheduler {

    private final StarPollService pollService;

    public StarPollScheduler(StarPollService pollService) {
        this.pollService = pollService;
    }

    @Scheduled(
            fixedRateString = "${app.github.poll-interval-ms:300000}",
            initialDelayString = "${app.github.initial-delay-ms:300000}")
    public void poll() {
        pollService.pollAll();
    }
}
