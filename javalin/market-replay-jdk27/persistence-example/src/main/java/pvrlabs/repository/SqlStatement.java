package pvrlabs.repository;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;

/**
 * Immutable default SQL text with optional dialect-keyed replacements.
 * Selection uses a trimmed, case-insensitive key and falls back to the default
 * when no override exists. Overrides return a new instance; they do not detect
 * the database, parse or rewrite SQL, or validate equivalent behavior. Callers
 * must ensure that bindings, mappings and execution methods work for each
 * selected statement. Jdbi executes the chosen text.
 */
public final class SqlStatement {
    private final String defaultSql;
    private final Map<String, String> overrides;

    private SqlStatement(String defaultSql, Map<String, String> overrides) {
        this.defaultSql = requireSql(defaultSql);
        this.overrides = Map.copyOf(overrides);
    }

    public static SqlStatement of(String sql) {
        return new SqlStatement(sql, Map.of());
    }

    public SqlStatement override(Dialects dialect, String sql) {
        return override(Objects.requireNonNull(dialect, "dialect").name(), sql);
    }

    public SqlStatement override(String dialect, String sql) {
        var copy = new HashMap<>(overrides);
        copy.put(dialectKey(dialect), requireSql(sql));
        return new SqlStatement(defaultSql, copy);
    }

    public SqlStatement h2(String sql) {
        return override(Dialects.H2, sql);
    }

    public SqlStatement postgres(String sql) {
        return override(Dialects.POSTGRES, sql);
    }

    public String sql(Dialects dialect) {
        return sql(Objects.requireNonNull(dialect, "dialect").name());
    }

    public String sql(String dialect) {
        return overrides.getOrDefault(dialectKey(dialect), defaultSql);
    }

    static String dialectKey(String dialect) {
        String key = Objects.requireNonNull(dialect, "dialect").trim().toLowerCase(Locale.ROOT);
        if (key.isEmpty()) throw new IllegalArgumentException("dialect must not be blank");
        return key;
    }

    private static String requireSql(String sql) {
        if (Objects.requireNonNull(sql, "sql").isBlank()) {
            throw new IllegalArgumentException("SQL must not be blank");
        }
        return sql;
    }
}
