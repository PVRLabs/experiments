package pvrlabs.poll;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.context.annotation.Profile;

@Component
@Profile("!experiment")
public class StarPollScheduler {

    private final StarPollService pollService;

    public StarPollScheduler(StarPollService pollService) {
        this.pollService = pollService;
    }

    @Scheduled(fixedRate = 300000, initialDelay = 3000)
    public void poll() {
        pollService.pollAll();
    }
}
