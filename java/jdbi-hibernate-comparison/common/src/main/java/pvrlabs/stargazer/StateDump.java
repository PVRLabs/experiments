package pvrlabs.stargazer;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.sql.DriverManager;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Offline, post-shutdown verification; does not affect measured query counts. */
public final class StateDump {
    public static void main(String[] args) throws Exception {
        try (var connection = DriverManager.getConnection(args[0], "sa", "")) {
            var state = new LinkedHashMap<String, Object>();
            for (String table : List.of("projects", "star_history")) {
                var rows = new ArrayList<Map<String, Object>>();
                try (var statement = connection.createStatement();
                        var result =
                                statement.executeQuery("select * from " + table + " order by id")) {
                    var metadata = result.getMetaData();
                    while (result.next()) {
                        var row = new LinkedHashMap<String, Object>();
                        for (int i = 1; i <= metadata.getColumnCount(); i++) {
                            Object value = result.getObject(i);
                            if (value instanceof java.time.OffsetDateTime time) {
                                value = time.toInstant().toString();
                            }
                            row.put(metadata.getColumnLabel(i).toLowerCase(Locale.ROOT), value);
                        }
                        rows.add(row);
                    }
                }
                state.put(table, rows);
            }
            System.out.println(new ObjectMapper().writeValueAsString(state));
        }
    }
}
