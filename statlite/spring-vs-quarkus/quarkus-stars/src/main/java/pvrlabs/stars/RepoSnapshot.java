package pvrlabs.stars;

import java.time.Instant;

public record RepoSnapshot(int stars, int forks, int watchers, Instant pushedAt) {}
