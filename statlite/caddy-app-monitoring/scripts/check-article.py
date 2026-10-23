#!/usr/bin/env python3
"""Assert controlled workload evidence without assuming minute/phase alignment."""
import collections
import json
import sys
from pathlib import Path


def check(root):
    def read(stage, target, endpoint):
        return json.loads((root / f"{stage}-{target}-{endpoint}.json").read_text())

    def require(condition, message):
        if not condition:
            raise SystemExit(f"FAIL: {message}")

    manifest = json.loads((root / "manifest.json").read_text())
    require(bool(manifest.get("finished_at")), "unfinished run")
    traffic = [json.loads(line) for line in (root / "traffic.jsonl").read_text().splitlines()]
    counts = collections.Counter((row["phase"], row["host"], row["status"]) for row in traffic)
    for phase in manifest["phases"]:
        require(counts[(phase["name"], "express.test", phase["expected_status"])] == 120, f"{phase['name']}: Express traffic")
        require(counts[(phase["name"], "spring.test", 200)] == 120, f"{phase['name']}: Spring traffic")
    require(len(traffic) == 1200, "unexpected traffic count")
    summary = {}
    for target in ("express-via-caddy", "spring-via-caddy", "spring-direct"):
        before = read("before", target, "v1-metrics")
        final = read("final", target, "v1-metrics")
        dashboard_before = read("before", target, "series")
        dashboard_final = read("final", target, "series")
        not_found = sum(p["http_404"] or 0 for p in dashboard_final["points"]) - sum(p["http_404"] or 0 for p in dashboard_before["points"])
        require(not_found == (120 if target == "express-via-caddy" else 0), f"{target}: dashboard 404 count")
        deltas = {}
        for key, expected in (("requests", 600), ("http_4xx", 120 if target == "express-via-caddy" else 0), ("http_5xx", 120 if target == "express-via-caddy" else 0)):
            delta = sum(p[key] or 0 for p in final["points"]) - sum(p[key] or 0 for p in before["points"])
            require(delta == expected, f"{target}: {key} delta {delta}, expected {expected}")
            deltas[key] = delta
        previous = None
        for stage in ("before", *(p["name"] for p in manifest["phases"]), "final"):
            status = read(stage, target, "v1-status")
            require(status["collection_status"] == "ok" and status["consecutive_collection_failures"] == 0, f"{target} {stage}: collection")
            poll = status["last_successful_poll_at"]
            require(poll and (previous is None or poll > previous), f"{target} {stage}: stale poll")
            previous = poll
        # Use complete poll intervals inside each phase, independent of minute alignment.
        def interior_latency(phase_name):
            import datetime
            phase = next(p for p in manifest["phases"] if p["name"] == phase_name)
            start = datetime.datetime.fromisoformat(phase["started_at"])
            end = datetime.datetime.fromisoformat(phase["ended_at"])
            values = []
            previous_time = None
            for point in dashboard_final["points"]:
                timestamp = datetime.datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
                if previous_time is not None and start < previous_time and timestamp < end and point["average_latency_seconds"] is not None:
                    values.append(point["average_latency_seconds"] * 1000)
                previous_time = timestamp
            return values
        slow, recovery = interior_latency("slow"), interior_latency("recovery")
        require(bool(slow) and bool(recovery), f"{target}: no interior latency buckets")
        if target == "express-via-caddy":
            require(min(slow) > 200 and max(recovery) < 50, "Express: latency rise/recovery")
        else:
            require(max(slow + recovery) < 50, f"{target}: Spring latency affected")
        runtime = any(p["runtime_memory_bytes"] is not None and p["process_cpu_cores"] is not None for p in final["points"])
        require(runtime == (target == "spring-direct"), f"{target}: runtime visibility")
        summary[target] = dict(deltas=deltas, slow_interior_latency_ms=slow, recovery_interior_latency_ms=recovery, runtime_reported=runtime)
        print(f"PASS: {target}: counts, errors, fresh polls, latency and runtime visibility")
    (root / "assertions.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
