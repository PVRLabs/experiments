package pvrlabs.stargazer;

import io.avaje.jex.Jex;

import pvrlabs.coilbase.jex.CoilBaseJexApplication;

public final class Application extends CoilBaseJexApplication {
    // Leave createPrimaryDataSource() null: no Jdbi RepositoryContext is initialized.
    private boolean repositoryContextInitialized() {
        try {
            db();
            return true;
        } catch (IllegalStateException absent) {
            return false;
        }
    }

    @Override
    protected void registerRoutes(Jex jex) {
        if (repositoryContextInitialized()) {
            throw new IllegalStateException("Unused repository context initialized");
        }
        jex.get(
                "/persistence-context",
                ctx ->
                        ctx.json(
                                java.util.Map.of(
                                        "coilbase_repository_context_initialized",
                                        repositoryContextInitialized())));
        var source = RuntimeSupport.datasource();
        // CoilBase owns neither resource here: returning a datasource would create Jdbi.
        HibernateStore openedStore = null;
        try {
            RuntimeSupport.schema(source);
            var store = new HibernateStore(source);
            openedStore = store;
            // Close Hibernate before its datasource on normal shutdown.
            jex.lifecycle()
                    .onShutdown(
                            () -> {
                                try {
                                    store.close();
                                } finally {
                                    source.close();
                                }
                            });
            RuntimeSupport.routes(jex, store, source);
        } catch (RuntimeException | Error failure) {
            // Route/bootstrap failure must release the resources before Jex can serve.
            try {
                if (openedStore != null) {
                    openedStore.close();
                }
            } finally {
                source.close();
            }
            throw failure;
        }
    }

    public static void main(String[] args) {
        new Application().start();
    }
}
