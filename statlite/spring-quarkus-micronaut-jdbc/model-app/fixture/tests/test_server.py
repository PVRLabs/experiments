import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Replay, load_samples  # noqa: E402


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.samples = load_samples()

    def test_known_offset_and_requests_do_not_advance(self):
        now = [100.0]
        replay = Replay(self.samples, step_seconds=10, monotonic=lambda: now[0], started_at=100)
        self.assertEqual(replay.current()["marketTime"], "09:30")
        now[0] = 145.0
        first = replay.current()
        self.assertEqual((first["sampleIndex"], first["marketTime"]), (4, "09:34"))
        self.assertEqual(
            [(quote["symbol"], quote["price"]) for quote in first["quotes"]],
            [("AAPL", 331.94), ("GOOG", 343.77), ("NVDA", 231.04)],
        )
        self.assertEqual(first, replay.current())

    def test_rejects_invalid_intervals_and_empty_samples(self):
        for interval in (0, -1, float("nan"), float("inf")):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                Replay(self.samples, step_seconds=interval)
        with self.assertRaisesRegex(ValueError, "empty"):
            Replay(())

    def test_loader_rejects_non_finite_and_non_positive_prices(self):
        source = Path(__file__).resolve().parents[1] / "data" / "quotes-2026-09-30.csv"
        with source.open(newline="", encoding="utf-8") as input_file:
            reader = csv.DictReader(input_file)
            rows = list(reader)
            fieldnames = reader.fieldnames
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.csv"
            for price in ("nan", "inf", "0", "-1"):
                rows[0]["price"] = price
                with path.open("w", newline="", encoding="utf-8") as output_file:
                    writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                with self.subTest(price=price), self.assertRaisesRegex(ValueError, "finite and positive"):
                    load_samples(path)

    def test_wrap_increments_cycle(self):
        now = [0.0]
        replay = Replay(self.samples, step_seconds=1, monotonic=lambda: now[0], started_at=0)
        now[0] = len(self.samples) - 1
        self.assertEqual((replay.current()["cycle"], replay.current()["sampleIndex"]), (0, 389))
        now[0] = len(self.samples)
        self.assertEqual((replay.current()["cycle"], replay.current()["sampleIndex"]), (1, 0))

    def test_loader_rejects_missing_sample(self):
        source = Path(__file__).resolve().parents[1] / "data" / "quotes-2026-09-30.csv"
        with source.open(newline="", encoding="utf-8") as input_file:
            reader = csv.DictReader(input_file)
            rows = list(reader)
            fieldnames = reader.fieldnames
        rows = [row for row in rows if row["market_time"] != "15:59"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.csv"
            with path.open("w", newline="", encoding="utf-8") as output_file:
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "exactly 390 consecutive samples"):
                load_samples(path)

    def test_loader_rejects_duplicate_symbol_and_missing_symbol(self):
        source = Path(__file__).resolve().parents[1] / "data" / "quotes-2026-09-30.csv"
        with source.open(newline="", encoding="utf-8") as input_file:
            reader = csv.DictReader(input_file)
            rows = list(reader)
            fieldnames = reader.fieldnames
        next(row for row in rows if row["market_time"] == "09:30" and row["symbol"] == "NVDA")["symbol"] = "AAPL"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.csv"
            with path.open("w", newline="", encoding="utf-8") as output_file:
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "exactly one quote each for AAPL, GOOG, and NVDA"):
                load_samples(path)


if __name__ == "__main__":
    unittest.main()
