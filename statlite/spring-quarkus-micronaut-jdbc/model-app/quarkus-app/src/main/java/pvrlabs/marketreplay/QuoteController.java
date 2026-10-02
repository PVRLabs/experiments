package pvrlabs.marketreplay;

import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import io.smallrye.common.annotation.Blocking;
import java.sql.SQLException;
import java.util.List;

@Path("/api/quotes")
@Produces(MediaType.APPLICATION_JSON)
@Blocking
public class QuoteController {
    @Inject QuoteRepository repository;
    @GET @Path("/latest")
    public List<QuoteObservation> latest() throws SQLException { return repository.latest(); }
    @GET @Path("/history")
    public List<QuoteObservation> history() throws SQLException { return repository.history(); }
}
