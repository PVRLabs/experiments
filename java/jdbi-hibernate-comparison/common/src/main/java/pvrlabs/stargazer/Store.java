package pvrlabs.stargazer;

import pvrlabs.model.Project;
import pvrlabs.model.StarHistory;

import java.util.List;
import java.util.function.Supplier;

public interface Store extends AutoCloseable {
    <T> T transaction(Supplier<T> work);

    Project find(String name);

    void save(Project project);

    Integer latest(Project project);

    void append(StarHistory row);

    List<Project> projects(List<String> names);

    List<StarHistory> history(List<Long> ids);

    void close();
}
