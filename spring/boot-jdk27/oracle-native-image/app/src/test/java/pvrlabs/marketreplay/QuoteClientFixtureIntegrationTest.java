package pvrlabs.marketreplay;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;
import java.time.Duration;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

class QuoteClientFixtureIntegrationTest {
    @Test
    void javaClientReadsCheckedInDataFromPythonFixture() throws Exception {
        Path fixtureScript = Path.of("..", "fixture", "server.py").toAbsolutePath().normalize();
        assertThat(fixtureScript).exists();

        int port = availableLoopbackPort();
        Process fixture = new ProcessBuilder(
                        "python3",
                        fixtureScript.toString(),
                        "--port",
                        Integer.toString(port),
                        "--step-seconds",
                        "3600")
                .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                .redirectError(ProcessBuilder.Redirect.DISCARD)
                .start();
        try {
            URI healthUri = URI.create("http://127.0.0.1:" + port + "/health");
            awaitFixture(healthUri, fixture);

            QuoteClient client = new QuoteClient(
                    URI.create("http://127.0.0.1:" + port + "/quotes"), new ObjectMapper());
            QuoteBatch batch = client.fetch();

            assertThat(batch.cycle()).isZero();
            assertThat(batch.sampleIndex()).isZero();
            assertThat(batch.marketTime()).isEqualTo("09:30");
            assertThat(batch.quotes()).extracting(FixtureQuote::symbol).containsExactly("AAPL", "GOOG", "NVDA");
            assertThat(batch.quotes())
                    .extracting(FixtureQuote::price)
                    .containsExactly(
                            new java.math.BigDecimal("331.61"),
                            new java.math.BigDecimal("341.91"),
                            new java.math.BigDecimal("229.32"));
        } finally {
            fixture.destroy();
            if (!fixture.waitFor(3, TimeUnit.SECONDS)) {
                fixture.destroyForcibly();
                fixture.waitFor(3, TimeUnit.SECONDS);
            }
        }
    }

    private static int availableLoopbackPort() throws IOException {
        try (ServerSocket socket = new ServerSocket()) {
            socket.bind(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), 0));
            return socket.getLocalPort();
        }
    }

    private static void awaitFixture(URI healthUri, Process fixture) throws Exception {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofMillis(300)).build();
        HttpRequest request = HttpRequest.newBuilder(healthUri).timeout(Duration.ofSeconds(1)).GET().build();
        long deadline = System.nanoTime() + Duration.ofSeconds(8).toNanos();
        while (System.nanoTime() < deadline) {
            if (!fixture.isAlive()) {
                throw new IllegalStateException("Python fixture exited before becoming ready");
            }
            try {
                HttpResponse<Void> response = client.send(request, HttpResponse.BodyHandlers.discarding());
                if (response.statusCode() == 200) {
                    return;
                }
            } catch (IOException ignored) {
                // Wait briefly for the fixture's loopback listener to start.
            }
            Thread.sleep(50);
        }
        throw new IllegalStateException("Python fixture did not become ready in time");
    }
}
