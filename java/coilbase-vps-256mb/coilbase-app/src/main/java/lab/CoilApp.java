package lab;
import javax.sql.DataSource;
import io.avaje.jex.Jex;
import pvrlabs.coilbase.jex.CoilBaseJexApplication;
public class CoilApp extends CoilBaseJexApplication {
    private com.zaxxer.hikari.HikariDataSource pool;
    @Override protected DataSource createPrimaryDataSource() { pool=Quotes.dataSource(); return pool; }
    @Override protected void registerRoutes(Jex jex) {
        // Shared schema and fixture initialization occurs before readiness on both stacks.
        try { new Quotes(pool); }
        catch(Exception e) { throw new IllegalStateException(e); }
        var healthDb=org.jdbi.v3.core.Jdbi.create(pool);
        jex.get("/inspection/db",ctx -> ctx.json(pvrlabs.coilbase.monitoring.DatabaseHealth.check(healthDb,2)));
        var service=new QuoteService(db(),new QuoteRepository(db()));
        jex.error(org.jdbi.v3.core.statement.UnableToExecuteStatementException.class, (ctx,e) -> {
            Throwable cause=e;
            while(cause!=null && !(cause instanceof java.sql.SQLException)) cause=cause.getCause();
            boolean conflict=cause instanceof java.sql.SQLException sql && sql.getSQLState()!=null && sql.getSQLState().startsWith("23");
            ctx.status(conflict ? 409 : 500).json(java.util.Map.of("error",conflict ? "conflict" : "internal_error"));
        });
        jex.routing(new QuoteController$Route(new QuoteController(service)));
    }
    @Override protected void configureErrorHandling() {
        mapError(IllegalArgumentException.class,400);
    }
    public static void main(String[] args) { new CoilApp().enableMonitoring().start(); }
}
