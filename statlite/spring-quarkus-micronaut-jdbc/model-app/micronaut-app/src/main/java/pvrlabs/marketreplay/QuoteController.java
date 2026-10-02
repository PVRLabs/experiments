package pvrlabs.marketreplay;

import io.micronaut.http.annotation.*;
import io.micronaut.scheduling.annotation.ExecuteOn;
import io.micronaut.scheduling.TaskExecutors;
import java.sql.SQLException;
import java.util.List;

@Controller("/api/quotes")
@ExecuteOn(TaskExecutors.BLOCKING)
public class QuoteController {
    private final QuoteRepository repository;
    public QuoteController(QuoteRepository repository) { this.repository = repository; }
    @Get("/latest")
    public List<QuoteObservation> latest() throws SQLException { return repository.latest(); }
    @Get("/history")
    public List<QuoteObservation> history() throws SQLException { return repository.history(); }
}
