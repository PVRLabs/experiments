package pvrlabs.stargazer;

import static org.junit.jupiter.api.Assertions.*;

import com.sun.net.httpserver.HttpServer;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

class PersistenceTest {
    @Test
    void pollingAndRollback() throws Exception {
        var config = new HikariConfig();
        config.setJdbcUrl("jdbc:h2:mem:" + UUID.randomUUID() + ";DB_CLOSE_DELAY=-1");
        config.setUsername("sa");
        config.setMaximumPoolSize(4);
        config.setMinimumIdle(1);
        try (var source = new HikariDataSource(config)) {
            RuntimeSupport.schema(source);
            try (Store store = new HibernateStore(source)) {
                var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
                int[] stars = {10}, status = {200};
                server.createContext(
                        "/repos/test/repo",
                        e -> {
                            var body =
                                    ("{\"stargazers_count\":"
                                                    + stars[0]
                                                    + ",\"forks_count\":3,\"subscribers_count\":4,\"pushed_at\":\"2026-01-01T00:00:00Z\"}")
                                            .getBytes();
                            e.getResponseHeaders().add("ETag", "\"v1\"");
                            e.sendResponseHeaders(status[0], status[0] == 304 ? -1 : body.length);
                            if (status[0] != 304) {
                                e.getResponseBody().write(body);
                            }
                            e.close();
                        });
                server.start();
                try {
                    var poll =
                            new PollService(
                                    store,
                                    new Github(
                                            "http://127.0.0.1:" + server.getAddress().getPort(),
                                            ""),
                                    List.of("test/repo"));
                    var now = Instant.parse("2026-01-01T00:00:00Z");
                    assertTrue(poll.pollOne("test/repo", now));
                    assertFalse(poll.pollOne("test/repo", now.plusSeconds(1)));
                    stars[0] = 11;
                    assertTrue(poll.pollOne("test/repo", now.plusSeconds(2)));
                    status[0] = 304;
                    assertFalse(poll.pollOne("test/repo", now.plusSeconds(3)));
                    store.transaction(
                            () -> {
                                var p = store.find("test/repo");
                                assertEquals(11, p.getCurrentStars());
                                assertEquals(3, p.getCurrentForks());
                                assertEquals(4, p.getCurrentWatchers());
                                assertEquals(now.plusSeconds(3), p.getLastPolledAt());
                                assertEquals(2, store.history(List.of(p.getId())).size());
                                return null;
                            });
                    status[0] = 500;
                    assertThrows(
                            RuntimeException.class,
                            () -> poll.pollOne("test/repo", now.plusSeconds(4)));
                    store.transaction(
                            () -> {
                                assertEquals(
                                        now.plusSeconds(3),
                                        store.find("test/repo").getLastPolledAt());
                                return null;
                            });
                    assertThrows(
                            IllegalStateException.class,
                            () ->
                                    store.transaction(
                                            () -> {
                                                var p = new pvrlabs.model.Project();
                                                p.setRepoName("rollback/new");
                                                store.save(p);
                                                throw new IllegalStateException(
                                                        "injected after insert");
                                            }));
                    store.transaction(
                            () -> {
                                assertNull(store.find("rollback/new"));
                                return null;
                            });
                    var html =
                            store.transaction(
                                    () -> {
                                        try {
                                            return new Views()
                                                    .render(
                                                            new DashboardController(
                                                                            store,
                                                                            List.of("test/repo"))
                                                                    .dashboard());
                                        } catch (Exception e) {
                                            throw new RuntimeException(e);
                                        }
                                    });
                    assertTrue(html.contains("test/repo"));
                    assertTrue(html.contains("star-chart"));
                    assertTrue(html.contains("chart-data"));
                } finally {
                    server.stop(0);
                }
            }
        }
    }
}
