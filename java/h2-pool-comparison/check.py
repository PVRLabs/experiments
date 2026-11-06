#!/usr/bin/env python3
"""Check the reported Linux run against retained samples and request events."""
import json
import math
from pathlib import Path
from statistics import mean

root = Path(__file__).parent / "results"
expected = [("1-native", 85.30, 111.05, 6.82, 9.71), ("2-hikari", 87.98, 109.05, 5.84, 8.42), ("3-hikari", 87.85, 109.80, 6.23, 8.84), ("4-native", 86.15, 110.85, 6.96, 10.21)]
for run, idle, moderate, p95, p99 in expected:
    path = root / run
    memory = json.loads((path / "memory.json").read_text())
    phases = json.loads((path / "phases.json").read_text())["phases"]
    samples = [json.loads(line) for line in (path / "guest/samples.jsonl").read_text().splitlines()]
    for phase, reported in (("idle", idle), ("moderate", moderate)):
        bounds = next(p for p in phases if p["phase"] == phase)
        values = [s["rss_kib"] for s in samples if bounds["start"] <= s["epoch"] < bounds["end"]]
        assert len(values) == memory[phase]["samples"]
        assert abs(mean(values) - memory[phase]["mean_rss_kib"]) < 0.001
        assert abs(mean(values) / 1024 - reported) < 0.0051
    summary = json.loads((path / "moderate/summary.json").read_text())
    events = [json.loads(line) for line in (path / "moderate/requests.jsonl").read_text().splitlines()]
    assert summary["offered"] == summary["successful"] == len(events) == 1800
    assert summary["errors"] == summary["unsent"] == summary["timeouts"] == 0
    assert all(e["ok"] for e in events)
    # The original generator uses nearest rank over successful request latencies.
    latencies = sorted(e["latency_ms"] for e in events if e["ok"])
    for percentile, reported in ((95, p95), (99, p99)):
        value = latencies[math.ceil(len(latencies) * percentile / 100) - 1]
        assert abs(value - summary[f"p{percentile}_ms"]) < 1e-9
        assert abs(value - reported) < 0.0051
    print(f"{run}: OK")
