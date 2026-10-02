package pvrlabs.marketreplay;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.math.BigDecimal;
import java.time.Instant;
import java.io.IOException;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.jdbc.core.JdbcTemplate;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(
        properties = {
            "spring.datasource.url=jdbc:h2:mem:market-replay-test;DB_CLOSE_DELAY=-1",
            "market.poll-interval-ms=3600000",
            "market.poll-initial-delay-ms=3600000"
        })
@AutoConfigureMockMvc
class MarketReplaySmokeTest {
    @Autowired private MockMvc http;
    @Autowired private QuoteRepository repository;
    @Autowired private QuoteSyncService syncService;
    @Autowired private ObjectMapper objectMapper;
    @MockitoBean private QuoteClient quoteClient;

    @Autowired private JdbcTemplate jdbc;

    @BeforeEach
    void clearDatabase() {
        jdbc.update("DELETE FROM quote_samples");
    }

    @Test
    void rejectsMalformedBatchBeforeWriting() throws Exception {
        List<FixtureQuote> valid = List.of(
                new FixtureQuote("AAPL", new BigDecimal("1.25")),
                new FixtureQuote("GOOG", new BigDecimal("2.25")),
                new FixtureQuote("NVDA", new BigDecimal("3.25")));
        for (QuoteBatch batch : List.of(
                new QuoteBatch(-1, "09:30", 0, valid),
                new QuoteBatch(0, "09:31", 0, valid),
                new QuoteBatch(0, "09:30", 0, List.of(valid.get(0), valid.get(0), valid.get(2))),
                new QuoteBatch(0, "09:30", 0, List.of(valid.get(0), valid.get(1),
                        new FixtureQuote(null, BigDecimal.ONE))),
                new QuoteBatch(0, "09:30", 0, List.of(valid.get(0), valid.get(1),
                        new FixtureQuote("NVDA", new BigDecimal("0.00001")))))) {
            given(quoteClient.fetch()).willReturn(batch);
            assertThatThrownBy(() -> syncService.pollOnce()).isInstanceOf(IOException.class);
            assertThat(repository.count()).isZero();
        }
    }

    @Test
    void boundsHistoryPerSymbolAcrossReplayWrap() {
        List<FixtureQuote> quotes = List.of(
                new FixtureQuote("AAPL", BigDecimal.ONE),
                new FixtureQuote("GOOG", BigDecimal.TEN),
                new FixtureQuote("NVDA", new BigDecimal("3")));
        for (int index = 0; index < 391; index++) {
            repository.insert(Instant.now(), new QuoteBatch(index / 390,
                    java.time.LocalTime.of(9, 30).plusMinutes(index % 390).toString(), index % 390, quotes));
        }
        assertThat(repository.count()).isEqualTo(1173);
        assertThat(repository.history()).hasSize(1170);
        for (String symbol : List.of("AAPL", "GOOG", "NVDA")) {
            List<QuoteObservation> history = repository.history().stream()
                    .filter(row -> row.symbol().equals(symbol)).toList();
            assertThat(history).hasSize(390);
            assertThat(history.getFirst().sampleIndex()).isEqualTo(1);
            assertThat(history.getLast().cycle()).isEqualTo(1);
            assertThat(history.getLast().sampleIndex()).isZero();
        }
        assertThat(repository.latest()).extracting(QuoteObservation::cycle).containsOnly(1);
    }

    @Test
    void rollsBackEntireBatchWhenDatabaseRejectsLaterRow() {
        QuoteBatch batch = new QuoteBatch(0, "09:30", 0, List.of(
                new FixtureQuote("AAPL", BigDecimal.ONE),
                new FixtureQuote("GOOG", BigDecimal.TEN),
                new FixtureQuote("NVDA", null)));
        assertThatThrownBy(() -> repository.insert(Instant.now(), batch))
                .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);
        assertThat(repository.count()).isZero();
    }

    @Test
    void parsesFixtureAndPersistsQuotesThenServesUiApiAndMetrics() throws Exception {
        String fixtureJson = "{\"cycle\":0,\"marketTime\":\"09:30\",\"sampleIndex\":0,"
                + "\"quotes\":[{\"symbol\":\"AAPL\",\"price\":224.18},"
                + "{\"symbol\":\"GOOG\",\"price\":198.43},"
                + "{\"symbol\":\"NVDA\",\"price\":187.12}]}";
        QuoteBatch parsed = objectMapper.readValue(fixtureJson, QuoteBatch.class);
        assertThat(parsed.quotes()).hasSize(3);
        assertThat(parsed.quotes().getFirst().price()).isEqualByComparingTo("224.18");
        given(quoteClient.fetch()).willReturn(parsed);

        syncService.pollOnce();
        assertThat(repository.count()).isEqualTo(3);
        assertThat(repository.latest()).extracting(QuoteObservation::symbol).containsExactly("AAPL", "GOOG", "NVDA");
        assertThat(repository.history()).extracting(QuoteObservation::sampleIndex).containsOnly(0);

        QuoteBatch next = new QuoteBatch(
                0,
                "09:31",
                1,
                List.of(
                        new FixtureQuote("AAPL", new java.math.BigDecimal("225.00")),
                        new FixtureQuote("GOOG", new java.math.BigDecimal("199.00")),
                        new FixtureQuote("NVDA", new java.math.BigDecimal("188.00"))));
        given(quoteClient.fetch()).willReturn(next);
        syncService.pollOnce();
        assertThat(repository.count()).isEqualTo(6);
        assertThat(repository.latest()).extracting(QuoteObservation::sampleIndex).containsOnly(1);
        assertThat(repository.history()).extracting(QuoteObservation::sampleIndex).containsExactly(0, 0, 0, 1, 1, 1);

        http.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString("Market Replay")));
        http.perform(get("/api/quotes/latest"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString("AAPL")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("GOOG")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("NVDA")));
        http.perform(get("/api/quotes/history"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString("sampleIndex")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("marketTime")));
        http.perform(get("/chart.umd.min.js")).andExpect(status().isOk());
        http.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString("UP")));
        http.perform(get("/actuator/prometheus"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString("jvm_memory_used_bytes")));
    }
}
