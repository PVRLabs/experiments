package pvrlabs.marketreplay;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/quotes")
class QuoteController {
    private final QuoteRepository repository;

    QuoteController(QuoteRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/latest")
    List<QuoteObservation> latest() {
        return repository.latest();
    }

    @GetMapping("/history")
    List<QuoteObservation> history() {
        return repository.history();
    }
}
