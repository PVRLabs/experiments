package lab;

import java.util.Map;

import org.apache.ibatis.mapping.Environment;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.session.LocalCacheScope;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.apache.ibatis.transaction.jdbc.JdbcTransactionFactory;

import com.zaxxer.hikari.HikariDataSource;

import io.javalin.Javalin;
import io.javalin.micrometer.MicrometerPlugin;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.micrometer.core.instrument.binder.jvm.JvmMemoryMetrics;
import io.micrometer.core.instrument.binder.system.ProcessorMetrics;

public final class JavalinMybatisApp {
    public static void main(String[] args) {
        var registry = new SimpleMeterRegistry();
        new JvmMemoryMetrics().bindTo(registry);
        new ProcessorMetrics().bindTo(registry);

        var ds = new HikariDataSource();
        ds.setJdbcUrl("jdbc:h2:file:" + System.getProperty("run.dir")
            + "/quotes;CACHE_SIZE=4096;DB_CLOSE_ON_EXIT=FALSE");
        ds.setUsername("sa");
        ds.setPassword("");
        ds.setMinimumIdle(1);
        ds.setMaximumPoolSize(2);
        ds.setConnectionTimeout(3000);
        ds.setValidationTimeout(1000);

        Javalin app = null;
        try {
            var environment = new Environment("h2", new JdbcTransactionFactory(), ds);
            var configuration = new Configuration(environment);
            configuration.setLocalCacheScope(LocalCacheScope.STATEMENT);
            configuration.addMapper(QuoteMapper.class);
            SqlSessionFactory sessionFactory = new SqlSessionFactoryBuilder().build(configuration);

            var repository = new MyBatisQuoteRepository(sessionFactory);
            repository.initialize(ds);
            var controller = new QuoteController(repository);
            app = Javalin.create(c -> {
                c.jetty.host = "127.0.0.1";
                c.registerPlugin(new MicrometerPlugin(p -> p.registry = registry));
                c.routes.get("/ready", ctx -> ctx.json(Map.of("status", "UP")));
                controller.register(c);
                c.routes.get(StatLiteMetrics.PATH,
                    ctx -> ctx.json(StatLiteMetrics.snapshot(registry, "UP")));
            });
            app.start(Integer.getInteger("app.port", 8080));
            System.out.println("Jetty thread pool: " + app.jettyServer().server().getThreadPool());
            var startedApp = app;
            Runtime.getRuntime().addShutdownHook(new Thread(() -> close(startedApp, ds, registry)));
        } catch (Exception | Error failure) {
            try {
                close(app, ds, registry);
            } catch (Exception | Error cleanupFailure) {
                failure.addSuppressed(cleanupFailure);
            }
            throw failure;
        }
    }

    private static void close(Javalin app, HikariDataSource ds, SimpleMeterRegistry registry) {
        try {
            if (app != null) app.stop();
        } finally {
            try {
                ds.close();
            } finally {
                registry.close();
            }
        }
    }
}
