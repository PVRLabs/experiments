package pvrlabs.poolreclaim;

import com.zaxxer.hikari.HikariDataSource;
import java.sql.Connection;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class PoolApplication {
    private static final Logger log = LoggerFactory.getLogger(PoolApplication.class);

    public static void main(String[] args) {
        SpringApplication.run(PoolApplication.class, args);
    }

    // One explicit DB check before readiness; later health/metric polls are passive.
    @Bean
    ApplicationRunner databaseCheck(HikariDataSource pool) {
        return args -> {
            try (Connection connection = pool.getConnection();
                    var statement = connection.createStatement()) {
                statement.setQueryTimeout(5);
                try (var rows = statement.executeQuery("SELECT 1")) {
                    if (!rows.next() || rows.getInt(1) != 1) throw new IllegalStateException("DB check failed");
                }
                log.info("Database ready: server={}, driver={}, Hikari={}",
                        connection.getMetaData().getDatabaseProductVersion(),
                        connection.getMetaData().getDriverVersion(),
                        HikariDataSource.class.getPackage().getImplementationVersion());
            }
        };
    }
}
