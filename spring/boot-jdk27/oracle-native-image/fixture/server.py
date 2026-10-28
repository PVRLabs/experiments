#!/usr/bin/env python3
"""Deterministic, read-only minute quote replay over checked-in CSV data."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable


DATA_FILE = Path(__file__).parent / "data" / "quotes-2026-09-30.csv"
EXPECTED_SYMBOLS = frozenset({"AAPL", "GOOG", "NVDA"})
EXPECTED_MARKET_TIMES = tuple(
    (dt.datetime(2026, 9, 30, 9, 30) + dt.timedelta(minutes=index)).strftime("%H:%M")
    for index in range(390)
)


@dataclass(frozen=True)
class Sample:
    market_time: str
    quotes: tuple[dict[str, object], ...]


def load_samples(path: Path = DATA_FILE) -> tuple[Sample, ...]:
    grouped: dict[str, list[dict[str, object]]] = {}
    with path.open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            grouped.setdefault(row["market_time"], []).append(
                {"symbol": row["symbol"], "price": float(row["price"])}
            )
    if tuple(sorted(grouped)) != EXPECTED_MARKET_TIMES:
        raise ValueError("fixture data must contain exactly 390 consecutive samples from 09:30 through 15:59")
    samples = tuple(Sample(key, tuple(grouped[key])) for key in EXPECTED_MARKET_TIMES)
    for sample in samples:
        if any(not math.isfinite(quote["price"]) or quote["price"] <= 0 for quote in sample.quotes):
            raise ValueError("fixture prices must be finite and positive")
        symbols = [quote["symbol"] for quote in sample.quotes]
        if len(symbols) != 3 or set(symbols) != EXPECTED_SYMBOLS:
            raise ValueError(
                f"{sample.market_time} must contain exactly one quote each for AAPL, GOOG, and NVDA"
            )
    return samples


class Replay:
    def __init__(
        self,
        samples: tuple[Sample, ...],
        step_seconds: float = 60.0,
        monotonic: Callable[[], float] = time.monotonic,
        started_at: float | None = None,
    ) -> None:
        if not math.isfinite(step_seconds) or step_seconds <= 0:
            raise ValueError("step_seconds must be finite and positive")
        if not samples:
            raise ValueError("samples must not be empty")
        self.samples = samples
        self.step_seconds = step_seconds
        self.monotonic = monotonic
        self.started_at = monotonic() if started_at is None else started_at

    def current(self) -> dict[str, object]:
        elapsed = max(0.0, self.monotonic() - self.started_at)
        absolute_step = int(elapsed // self.step_seconds)
        sample_index = absolute_step % len(self.samples)
        sample = self.samples[sample_index]
        return {
            "cycle": absolute_step // len(self.samples),
            "marketTime": sample.market_time,
            "sampleIndex": sample_index,
            "quotes": list(sample.quotes),
        }


def make_handler(replay: Replay) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"UP"}')
                return
            if self.path != "/quotes":
                self.send_error(404)
                return
            body = json.dumps(replay.current(), separators=(",", ":")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print("fixture: " + format % args)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("FIXTURE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("FIXTURE_PORT", "8090")))
    parser.add_argument(
        "--step-seconds", type=float, default=float(os.getenv("FIXTURE_STEP_SECONDS", "60"))
    )
    args = parser.parse_args()
    replay = Replay(load_samples(), args.step_seconds)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(replay))
    print(f"market fixture listening on http://{args.host}:{args.port}; {len(replay.samples)} samples", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
