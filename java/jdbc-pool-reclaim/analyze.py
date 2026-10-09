#!/usr/bin/env python3
"""Recompute the published headlines from the curated series and request logs.

Reads results/run1007a only. Compares window medians and revisit latency
with summary.csv, which was produced from the original one-second samples
by scripts/summarize.py. Also checks the ten-connection / two-cgroup
sample coverage of each published window.
"""
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "results" / "run1007a"
ORDER = ["default-1", "no-reclaim-1", "reclaim-1", "reclaim-2", "no-reclaim-2", "default-2"]
WINDOWS = {
    "initial": (-10, 0),
    "B_busy_A_idle": (58, 68),
    "both_quiet": (118, 128),
    "final": (134, 144),
}
CHECKS = [
    ("peak_aggregate_pg", "peak_pg_aggregate", None),
    ("both_quiet_pg_A", "both_quiet_pg_A", None),
    ("both_quiet_pg_B", "both_quiet_pg_B", None),
    ("both_quiet_pg_aggregate", "both_quiet_pg_aggregate", None),
    ("both_quiet_pg_cgroup_bytes_mib", "both_quiet_pg_cgroup_mib", 1e-9),
    ("B_busy_A_idle_pg_aggregate", "B_busy_A_idle_pg_aggregate", None),
    ("B_busy_A_idle_pg_cgroup_bytes_mib", "B_busy_A_idle_pg_cgroup_mib", 1e-9),
    ("initial_pg_aggregate", "initial_pg_aggregate", None),
    ("initial_pg_cgroup_bytes_mib", "initial_pg_cgroup_mib", 1e-9),
    ("final_pg_aggregate", "final_pg_aggregate", None),
    ("final_pg_cgroup_bytes_mib", "final_pg_cgroup_mib", 1e-9),
    ("overall_errors", "request_errors", None),
    ("overall_successes", "request_successes", None),
    ("sample_errors", "sample_errors", None),
    ("supporting_warnings", "supporting_warnings", None),
    ("A_revisit_borrow_median_ms", "A_revisit_borrow_median_ms", 1e-9),
    ("B_revisit_borrow_median_ms", "B_revisit_borrow_median_ms", 1e-9),
    ("A_revisit_median_ms", "A_revisit_median_ms", 1e-9),
    ("B_revisit_median_ms", "B_revisit_median_ms", 1e-9),
]


def median(values):
    return statistics.median(values) if values else None


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def number(text):
    return None if text is None or text == "" else float(text)


def selected(samples, name, column):
    lo, hi = WINDOWS[name]
    values = []
    for sample in samples:
        elapsed = float(sample["elapsed"])
        if lo <= elapsed < hi and sample[column] != "":
            values.append(float(sample[column]))
    return values


def window(samples, name, column):
    return median(selected(samples, name, column))


def revisit_median(requests, instance, column):
    values = [
        float(row[column])
        for row in requests
        if row["instance"] == instance and row["stage"] == "revisit" and row["error"] == "" and row[column] != ""
    ]
    return median(values)


def recompute(scenario):
    samples = rows(RUN / scenario / "series.csv")
    requests = rows(RUN / scenario / "requests.csv")
    measured = [row for row in requests if row["stage"] != "warmup"]
    result = {
        "peak_pg_aggregate": max(int(float(sample["pg_aggregate"])) for sample in samples if sample["pg_aggregate"]),
        "sample_errors": sum(int(sample["sample_errors"]) for sample in samples),
        "supporting_warnings": sum(int(sample["supporting_warnings"]) for sample in samples),
        "request_errors": sum(row["error"] != "" for row in measured),
        "request_successes": sum(row["error"] == "" and row["status"] == "200" for row in measured),
        "A_revisit_borrow_median_ms": revisit_median(requests, "A", "acquisition_ms"),
        "B_revisit_borrow_median_ms": revisit_median(requests, "B", "acquisition_ms"),
        "A_revisit_median_ms": revisit_median(requests, "A", "elapsed_ms"),
        "B_revisit_median_ms": revisit_median(requests, "B", "elapsed_ms"),
    }
    for label in WINDOWS:
        result[f"{label}_pg_samples"] = len(selected(samples, label, "pg_aggregate"))
        result[f"{label}_cgroup_samples"] = len(selected(samples, label, "pg_cgroup_bytes"))
    for label in WINDOWS:
        result[f"{label}_pg_A"] = window(samples, label, "pg_A")
        result[f"{label}_pg_B"] = window(samples, label, "pg_B")
        result[f"{label}_pg_aggregate"] = window(samples, label, "pg_aggregate")
        cgroup = window(samples, label, "pg_cgroup_bytes")
        result[f"{label}_pg_cgroup_mib"] = None if cgroup is None else cgroup / 1048576
    return result


def close(actual, expected, tolerance):
    if actual is None or expected is None:
        return actual is expected
    if tolerance is None:
        return float(actual) == float(expected)
    return abs(float(actual) - float(expected)) <= tolerance


def main():
    summary = {row["run"]: row for row in rows(RUN / "summary.csv")}
    failures = []
    print(f"{'scenario':<14} {'quiet conn':>10} {'quiet MiB':>10} {'busy conn':>10} {'final conn':>10}")
    for scenario in ORDER:
        fresh = recompute(scenario)
        recorded = summary[scenario]
        print(
            f"{scenario:<14} {fresh['both_quiet_pg_aggregate']:10.0f} "
            f"{fresh['both_quiet_pg_cgroup_mib']:10.2f} "
            f"{fresh['B_busy_A_idle_pg_aggregate']:10.0f} "
            f"{fresh['final_pg_aggregate']:10.0f}"
        )
        for recorded_key, fresh_key, tolerance in CHECKS:
            if not close(fresh[fresh_key], number(recorded[recorded_key]), tolerance):
                failures.append(f"{scenario} {recorded_key}: series {fresh[fresh_key]} summary {recorded[recorded_key]}")
        mechanism = json.loads((RUN / scenario / "mechanism-check.json").read_text())
        if mechanism.get("status") != recorded["mechanism_status"]:
            failures.append(f"{scenario} mechanism {mechanism.get('status')} != {recorded['mechanism_status']}")
        if recorded["status"] != "valid":
            failures.append(f"{scenario} status {recorded['status']}")
        for label in WINDOWS:
            if fresh[f"{label}_pg_samples"] != 10 or fresh[f"{label}_cgroup_samples"] != 2:
                failures.append(
                    f"{scenario} {label}: connection samples {fresh[f'{label}_pg_samples']}, "
                    f"cgroup samples {fresh[f'{label}_cgroup_samples']}"
                )
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("curated series match summary.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
