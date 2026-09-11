package pvrlabs.github;

import java.time.Instant;

/** Current snapshot from GET /repos/{owner}/{repo}. History is still stars-only. */
public record RepoSnapshot(int stars, int forks, int watchers, Instant pushedAt) {}
