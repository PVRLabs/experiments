package pvrlabs.stargazer;

import com.zaxxer.hikari.HikariDataSource;

import io.avaje.jex.Jex;

import pvrlabs.coilbase.jex.CoilBaseJexApplication;

public final class Application extends CoilBaseJexApplication {
    private HikariDataSource source;

    // Returning the datasource transfers lifecycle ownership to CoilBase.
    @Override
    protected javax.sql.DataSource createPrimaryDataSource() {
        source = RuntimeSupport.datasource();
        try {
            RuntimeSupport.schema(source);
            return source;
        } catch (RuntimeException failure) {
            source.close();
            throw failure;
        }
    }

    @Override
    protected void registerRoutes(Jex jex) {
        RuntimeSupport.routes(jex, new JdbiStore(db()), source);
    }

    public static void main(String[] args) {
        new Application().start();
    }
}
