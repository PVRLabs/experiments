package pvrlabs.marketreplay;

import io.micronaut.json.JsonMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import jakarta.inject.Singleton;
import jakarta.inject.Inject;
import io.micronaut.context.annotation.Value;

@Singleton
class QuoteClient {
    private final URI quotesUri;
    private final HttpClient httpClient;
    private final JsonMapper objectMapper;

    @Inject
    public QuoteClient(
            @Value("${market.fixture-url}") URI quotesUri,
            JsonMapper objectMapper) {
        this.quotesUri = quotesUri;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    }

    QuoteBatch fetch() throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(quotesUri).timeout(Duration.ofSeconds(5)).GET().build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        if (response.statusCode() != 200) {
            throw new IOException("fixture returned HTTP " + response.statusCode());
        }
        return objectMapper.readValue(response.body(), QuoteBatch.class);
    }
}
