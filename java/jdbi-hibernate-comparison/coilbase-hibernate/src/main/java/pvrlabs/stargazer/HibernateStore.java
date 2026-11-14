package pvrlabs.stargazer;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;

import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;

import java.util.List;
import java.util.Objects;
import java.util.function.Supplier;

import javax.sql.DataSource;

public final class HibernateStore implements Store {
    private final SessionFactory sessionFactory;
    private final ThreadLocal<Session> currentSession = new ThreadLocal<>();

    public HibernateStore(DataSource source) {
        sessionFactory = build(source);
    }

    HibernateStore(SessionFactory sessionFactory) {
        this.sessionFactory = sessionFactory;
    }

    private static SessionFactory build(DataSource source) {
        var config =
                new Configuration()
                        .addAnnotatedClass(Project.class)
                        .addAnnotatedClass(StarHistory.class);
        config.setProperty("hibernate.hbm2ddl.auto", "validate");
        config.setProperty("hibernate.jdbc.time_zone", "UTC");
        config.getProperties().put("hibernate.connection.datasource", source);
        return config.buildSessionFactory();
    }

    private Session session() {
        return Objects.requireNonNull(currentSession.get(), "No transaction");
    }

    public <T> T transaction(Supplier<T> work) {
        if (currentSession.get() != null) {
            throw new IllegalStateException("Unexpected nested transaction");
        }
        try (var session = sessionFactory.openSession()) {
            // Make the session available only within this repository transaction scope.
            currentSession.set(session);
            try {
                var transaction = session.beginTransaction();
                try {
                    T result = work.get();
                    transaction.commit();
                    return result;
                } catch (RuntimeException | Error failure) {
                    if (transaction.isActive()) {
                        transaction.rollback();
                    }
                    throw failure;
                }
            } finally {
                // Also clear the context when beginTransaction itself fails.
                currentSession.remove();
            }
        }
    }

    public Project find(String repositoryName) {
        return session()
                .createQuery("from Project where repoName=:name", Project.class)
                .setParameter("name", repositoryName)
                .uniqueResult();
    }

    public void save(Project project) {
        // Existing entities are managed by this session; dirty checking writes changes.
        if (project.getId() == null) {
            session().persist(project);
        }
    }

    public Integer latest(Project project) {
        return session()
                .createQuery(
                        "select starCount"
                                + " from StarHistory"
                                + " where project.id=:id"
                                + " order by recordedAt desc,id desc",
                        Integer.class)
                .setParameter("id", project.getId())
                .setMaxResults(1)
                .uniqueResultOptional()
                .orElse(project.getCurrentStars());
    }

    public void append(StarHistory row) {
        session().persist(row);
    }

    public List<Project> projects(List<String> names) {
        return names.isEmpty()
                ? List.of()
                : session()
                        .createQuery(
                                "from Project where repoName in :names order by repoName",
                                Project.class)
                        .setParameter("names", names)
                        .list();
    }

    public List<StarHistory> history(List<Long> ids) {
        return ids.isEmpty()
                ? List.of()
                : session()
                        .createQuery(
                                "select h"
                                        + " from StarHistory h"
                                        + " join fetch h.project"
                                        + " where h.project.id in :ids"
                                        + " order by h.recordedAt,"
                                        + "h.id",
                                StarHistory.class)
                        .setParameter("ids", ids)
                        .list();
    }

    public void close() {
        sessionFactory.close();
    }
}
