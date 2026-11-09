"""Validate curated summaries; this does not recheck the original raw traces."""
import json
from pathlib import Path

MODULES = {"spring-boot", "javalin-coilbase", "micronaut-data",
           "micronaut-coilbase", "jex-coilbase"}
EXPECTED = {(module, round_number) for module in MODULES for round_number in (1, 2)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(data, runtime):
    require(runtime in {"hotspot", "native"}, f"Unknown runtime: {runtime}")
    require(data["planned"] == data["completed"] == len(data["runs"]) == 10,
            f"{runtime}: expected ten planned and completed runs")
    require(not data["failures"], f"{runtime}: recorded failures")
    seen = set()
    for run in data["runs"]:
        identity = (run["module"], run["round"])
        label = f"{runtime}/{identity[0]}/round-{identity[1]}"
        require(type(run["round"]) is int and identity in EXPECTED,
                f"{label}: unexpected module or round")
        require(identity not in seen, f"{label}: duplicate observation")
        seen.add(identity)
        state = run["state"]
        require(state["trace_verified"] is True, f"{label}: trace not verified")
        for field, expected in {"quotes": 1210, "audits": 210, "records": 100}.items():
            require(type(state[field]) is int and state[field] == expected,
                    f"{label}: expected {field}={expected}, got {state[field]!r}")
        metrics = run["metrics"]
        for phase, reads, writes in [("warmup", 480, 60), ("workload", 1200, 150)]:
            expected = {"offered": reads + 2 * writes,
                        "successful": reads + 2 * writes,
                        "errors": 0, "unsent": 0, "timeouts": 0,
                        "/api/quotes/latest.successful": reads,
                        "/api/quotes.successful": writes,
                        "/api/records/status.successful": writes}
            for suffix, count in expected.items():
                key = f"{phase}.http.{suffix}"
                require(type(metrics[key]) is int and metrics[key] == count,
                        f"{label}: expected {key}={count}, got {metrics[key]!r}")
    require(seen == EXPECTED, f"{runtime}: incomplete run matrix")


def main():
    # Validate both files before printing any accepted observations.
    summaries = {runtime: json.loads(Path(__file__).with_name(runtime + ".json").read_text())
                 for runtime in ("hotspot", "native")}
    for runtime, data in summaries.items():
        validate(data, runtime)
    for runtime, data in summaries.items():
        for run in data["runs"]:
            metrics = run["metrics"]
            print(runtime, run["module"], run["round"],
                  metrics["workload.app.rss_median_mib"], metrics["startup_seconds"])


if __name__ == "__main__":
    main()
