package pvrlabs.poolreclaim;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.zaxxer.hikari.HikariDataSource;
import com.zaxxer.hikari.HikariPoolMXBean;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

class WorkControllerTest {
    private HikariDataSource pool(AtomicInteger closes) throws Exception {
        var pool = mock(HikariDataSource.class);
        var bean = mock(HikariPoolMXBean.class);
        when(pool.getHikariPoolMXBean()).thenReturn(bean);
        when(bean.getActiveConnections()).thenReturn(10);
        var nextPid = new AtomicInteger(100);
        when(pool.getConnection()).thenAnswer(invocation -> {
            var connection = mock(Connection.class);
            var statement = mock(Statement.class);
            var rows = mock(ResultSet.class);
            int pid = nextPid.incrementAndGet();
            when(connection.createStatement()).thenReturn(statement);
            when(statement.executeQuery(anyString())).thenReturn(rows);
            when(rows.next()).thenReturn(true);
            when(rows.getInt(1)).thenReturn(pid);
            when(rows.getInt(2)).thenReturn(1);
            when(connection.prepareStatement(anyString())).thenReturn(mock(PreparedStatement.class));
            org.mockito.Mockito.doAnswer(call -> { closes.incrementAndGet(); return null; }).when(connection).close();
            return connection;
        });
        return pool;
    }

    @Test
    void tenConcurrentRequestsPassGateAndReleaseDistinctConnections() throws Exception {
        var closes = new AtomicInteger();
        var controller = new WorkController(pool(closes), "pool-A", "test-A", 0, 5000);
        try (var executor = Executors.newFixedThreadPool(10)) {
            var futures = new ArrayList<java.util.concurrent.Future<java.util.Map<String, Object>>>();
            for (int i = 0; i < 10; i++) {
                int request = i;
                futures.add(executor.submit(() -> controller.work("wave", request, 10)));
            }
            var pids = new java.util.HashSet<Object>();
            for (var future : futures) {
                var result = future.get(6, TimeUnit.SECONDS);
                assertThat(result.get("value")).isEqualTo(1);
                assertThat(result.get("instance")).isEqualTo("pool-A");
                pids.add(result.get("backendPid"));
            }
            assertThat(pids).hasSize(10);
            assertThat(closes).hasValue(10);
        }
    }

    @Test
    void incompleteWaveTimesOutAndReturnsItsConnection() throws Exception {
        var closes = new AtomicInteger();
        var controller = new WorkController(pool(closes), "pool-A", "test-A", 0, 50);
        assertThatThrownBy(() -> controller.work("incomplete", 0, 10)).isInstanceOf(ResponseStatusException.class);
        assertThat(closes).hasValue(1);
        assertThatThrownBy(() -> controller.work("bad", 0, 2)).isInstanceOf(ResponseStatusException.class);
        assertThat(closes).hasValue(1);
    }
}
