#!/usr/bin/env python3
"""Check one short, otherwise idle smoke run using only the public API."""
import json
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def check(directory):
    for target in ("express-via-caddy", "spring-via-caddy", "spring-direct"):
        totals = {}
        previous_poll = None
        for stage in ("baseline", "workload", "isolation"):
            def read(endpoint):
                return json.loads((directory / f"{target}-{stage}-{endpoint}.json").read_text())

            status, metrics = read("status"), read("metrics")
            label = f"{target} {stage}"
            require(status["target"] == metrics["target"] == target, f"{label}: wrong target")
            require(status["collection_status"] == "ok", f"{label}: collection is not ok")
            require(status["consecutive_collection_failures"] == 0, f"{label}: collection failures")
            poll = status["last_successful_poll_at"]
            require(poll is not None, f"{label}: no successful poll")
            require(previous_poll is None or poll > previous_poll, f"{label}: no new successful poll")
            previous_poll = poll
            require(metrics["latest_http_observation_at"] is not None, f"{label}: no HTTP observation")
            require(bool(metrics["points"]), f"{label}: empty metrics")
            totals[stage] = {
                key: sum(point[key] or 0 for point in metrics["points"])
                for key in ("requests", "http_5xx")
            }
        for stage, previous, requests, errors in (
            ("workload", "baseline", 3, 1),
            ("isolation", "workload", 1 if target == "express-via-caddy" else 0, 0),
        ):
            for key, expected in (("requests", requests), ("http_5xx", errors)):
                actual = totals[stage][key] - totals[previous][key]
                require(actual == expected, f"{target} {stage}: {key} delta {actual}, expected {expected}")
        print(f"PASS: {target}: successful collection, workload deltas and host isolation")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
