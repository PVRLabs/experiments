package pvrlabs.stargazer;

import pvrlabs.coilbase.Repository;
import pvrlabs.coilbase.RepositoryContext;
import pvrlabs.coilbase.SqlStatement;
import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.function.Supplier;

public final class JdbiStore extends Repository implements Store {
    private static final SqlStatement FIND =
            SqlStatement.of("select * from projects where repo_name=:name");

    public JdbiStore(RepositoryContext db) {
        super(db);
    }

    public <T> T transaction(Supplier<T> work) {
        return db.transactional(work);
    }

    private static Project mapProject(ResultSet result) throws SQLException {
        var project = new Project();
        project.setId(result.getLong("id"));
        project.setRepoName(result.getString("repo_name"));
        project.setCurrentStars((Integer) result.getObject("current_stars"));
        project.setCurrentForks((Integer) result.getObject("current_forks"));
        project.setCurrentWatchers((Integer) result.getObject("current_watchers"));
        var pushed = result.getTimestamp("last_pushed_at");
        var polled = result.getTimestamp("last_polled_at");
        project.setLastPushedAt(pushed == null ? null : pushed.toInstant());
        project.setLastPolledAt(polled == null ? null : polled.toInstant());
        return project;
    }

    public Project find(String repositoryName) {
        return db.query(
                FIND,
                statement ->
                        statement
                                .bind("name", repositoryName)
                                .map((result, context) -> mapProject(result))
                                .findOne()
                                .orElse(null));
    }

    public void save(Project project) {
        if (project.getId() == null) {
            project.setId(
                    db.withHandle(
                            handle ->
                                    handle.createUpdate(
                                                    "insert into projects(repo_name) values(:name)")
                                            .bind("name", project.getRepoName())
                                            .executeAndReturnGeneratedKeys("id")
                                            .mapTo(Long.class)
                                            .one()));
            return;
        }
        db.update(
                "update projects"
                        + " set current_stars=:s,"
                        + "current_forks=:f,"
                        + "current_watchers=:w,"
                        + "last_pushed_at=:push,"
                        + "last_polled_at=:poll"
                        + " where id=:id",
                statement ->
                        statement
                                .bind("s", project.getCurrentStars())
                                .bind("f", project.getCurrentForks())
                                .bind("w", project.getCurrentWatchers())
                                .bind("push", project.getLastPushedAt())
                                .bind("poll", project.getLastPolledAt())
                                .bind("id", project.getId())
                                .execute());
    }

    // Match the reference tie-breaker when multiple observations share a timestamp.
    public Integer latest(Project project) {
        return db.query(
                "select star_count"
                        + " from star_history"
                        + " where project_id=:id"
                        + " order by recorded_at desc,"
                        + "id desc limit 1",
                statement ->
                        statement
                                .bind("id", project.getId())
                                .mapTo(Integer.class)
                                .findOne()
                                .orElse(project.getCurrentStars()));
    }

    public void append(StarHistory row) {
        db.update(
                "insert into star_history(project_id,star_count,recorded_at) values(:id,:s,:at)",
                statement ->
                        statement
                                .bind("id", row.getProject().getId())
                                .bind("s", row.getStarCount())
                                .bind("at", row.getRecordedAt())
                                .execute());
    }

    public List<Project> projects(List<String> names) {
        return names.isEmpty()
                ? List.of()
                : db.query(
                        "select * from projects where repo_name in (<names>) order by repo_name",
                        statement ->
                                statement
                                        .bindList("names", names)
                                        .map((result, context) -> mapProject(result))
                                        .list());
    }

    public List<StarHistory> history(List<Long> ids) {
        return ids.isEmpty()
                ? List.of()
                : db.query(
                        "select h.*,"
                                + "p.repo_name"
                                + " from star_history h"
                                + " join projects p on p.id=h.project_id"
                                + " where project_id in (<ids>)"
                                + " order by recorded_at,"
                                + "h.id",
                        statement ->
                                statement
                                        .bindList("ids", ids)
                                        .map(
                                                (result, context) -> {
                                                    var history = new StarHistory();
                                                    history.setId(result.getLong("id"));
                                                    var project = new Project();
                                                    project.setId(result.getLong("project_id"));
                                                    project.setRepoName(
                                                            result.getString("repo_name"));
                                                    history.setProject(project);
                                                    history.setStarCount(
                                                            result.getInt("star_count"));
                                                    history.setRecordedAt(
                                                            result.getTimestamp("recorded_at")
                                                                    .toInstant());
                                                    return history;
                                                })
                                        .list());
    }

    public void close() {
        // CoilBase owns the datasource; this repository owns no separate resources.
    }
}
