package pvrlabs.stargazer;

import java.util.ArrayList;
import java.util.Map;

import javax.sql.DataSource;

public final class Diagnostics {
    public static Map<String, Object> snapshot(DataSource source) {
        try (var connection = source.getConnection();
                var statement = connection.createStatement()) {
            var rows = new ArrayList<Map<String, Object>>();
            try (var result =
                    statement.executeQuery(
                            "select SQL_STATEMENT,EXECUTION_COUNT from"
                                    + " INFORMATION_SCHEMA.QUERY_STATISTICS")) {
                while (result.next()) {
                    rows.add(Map.of("sql", result.getString(1), "executions", result.getLong(2)));
                }
            }
            return Map.of(
                    "heap_used_bytes",
                    java.lang.management.ManagementFactory.getMemoryMXBean()
                            .getHeapMemoryUsage()
                            .getUsed(),
                    "queries",
                    rows);
        } catch (java.sql.SQLException failure) {
            throw new IllegalStateException(failure);
        }
    }
}
