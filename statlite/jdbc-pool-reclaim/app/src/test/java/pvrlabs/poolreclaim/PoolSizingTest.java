package pvrlabs.poolreclaim;

import static org.assertj.core.api.Assertions.assertThat;

import com.zaxxer.hikari.HikariDataSource;
import java.util.HashMap;
import java.util.Properties;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.context.properties.source.MapConfigurationPropertySource;

class PoolSizingTest {
    private Properties properties(String resource) throws Exception {
        var values = new Properties();
        try (var stream = getClass().getResourceAsStream("/" + resource)) {
            values.load(stream);
        }
        return values;
    }

    private HikariDataSource boundPool(String profile) throws Exception {
        var values = properties("application.properties");
        values.putAll(properties("application-" + profile + ".properties"));
        var sizing = new HashMap<String, Object>();
        // Bind exactly the packaged numeric controls. Pool validation resolves defaults
        // without starting a JDBC connection or a PostgreSQL server.
        values.forEach((key, value) -> {
            String name = key.toString();
            if (name.startsWith("spring.datasource.hikari.") && value.toString().matches("[0-9]+"))
                sizing.put(name, value);
        });
        var pool = new HikariDataSource();
        new Binder(new MapConfigurationPropertySource(sizing)).bind("spring.datasource.hikari", Bindable.ofInstance(pool));
        pool.setJdbcUrl("jdbc:postgresql://127.0.0.1/unused");
        pool.validate();
        return pool;
    }

    @Test
    void defaultSizingIsUnsetAndResolvesThroughHikari() throws Exception {
        for (String resource : new String[] {"application.properties", "application-default.properties"}) {
            var values = properties(resource);
            assertThat(values).doesNotContainKeys("spring.datasource.hikari.minimum-idle",
                    "spring.datasource.hikari.maximum-pool-size");
        }
        try (var pool = boundPool("default")) {
            assertThat(pool.getMaximumPoolSize()).isEqualTo(10);
            assertThat(pool.getMinimumIdle()).isEqualTo(pool.getMaximumPoolSize());
        }
    }

    @Test
    void elasticProfilesExplicitlySetSizingAndRetirementControls() throws Exception {
        for (String profile : new String[] {"no-reclaim", "reclaim"}) {
            var values = properties("application-" + profile + ".properties");
            assertThat(values.getProperty("spring.datasource.hikari.minimum-idle")).isEqualTo("1");
            assertThat(values.getProperty("spring.datasource.hikari.maximum-pool-size")).isEqualTo("10");
            try (var pool = boundPool(profile)) {
                assertThat(pool.getMinimumIdle()).isEqualTo(1);
                assertThat(pool.getMaximumPoolSize()).isEqualTo(10);
                assertThat(pool.getIdleTimeout()).isEqualTo(profile.equals("reclaim") ? 10000 : 0);
            }
        }
    }
}
