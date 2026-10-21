#!/usr/bin/env python3
"""Validate and summarize the curated PostgreSQL rewrite measurements."""

import csv
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROWS = list(csv.DictReader((ROOT / "results" / "measurements.csv").open()))
VARIANTS = [
    ("postgres", "scriptella", "false"),
    ("postgres", "scriptella", "true"),
    ("postgres", "jdbc", "false"),
    ("postgres", "jdbc", "true"),
    ("mariadb", "scriptella", "default"),
    ("mariadb", "jdbc", "default"),
]

assert len(ROWS) == 18, f"expected 18 measurements, found {len(ROWS)}"
for round_id in range(1, 4):
    actual = [row for row in ROWS if int(row["round"]) == round_id]
    expected = VARIANTS if round_id % 2 else VARIANTS[::-1]
    assert [(r["database"], r["implementation"], r["rewrite"]) for r in actual] == expected
    assert [int(r["position"]) for r in actual] == list(range(1, 7))

for row in ROWS:
    assert row["verified"] == "true"
    assert row["rows"] == "1000000"
    assert row["batch_size"] == "1000"
    duration = float(row["duration_ms"])
    throughput = float(row["rows_per_second"])
    assert duration > 0
    assert abs(throughput - 1_000_000_000 / duration) < 0.1

medians = {}
print("| Database | Implementation | Rewrite | Run 1 | Run 2 | Run 3 | Median |")
print("|---|---|---|---:|---:|---:|---:|")
for variant in VARIANTS:
    values = [
        float(row["duration_ms"]) / 1000
        for row in ROWS
        if (row["database"], row["implementation"], row["rewrite"]) == variant
    ]
    assert len(values) == 3
    medians[variant] = statistics.median(values)
    rendered = " | ".join(f"{value:.3f} s" for value in values)
    print(f"| {' | '.join(variant)} | {rendered} | {medians[variant]:.3f} s |")

print()
for implementation in ("scriptella", "jdbc"):
    baseline = medians["postgres", implementation, "false"]
    rewritten = medians["postgres", implementation, "true"]
    mariadb = medians["mariadb", implementation, "default"]
    print(
        f"{implementation}: {baseline / rewritten:.3f}x rewrite speedup; "
        f"{100 * (1 - rewritten / baseline):.1f}% less elapsed time; "
        f"PostgreSQL minus MariaDB {baseline - mariadb:.3f} s -> "
        f"{rewritten - mariadb:.3f} s"
    )
