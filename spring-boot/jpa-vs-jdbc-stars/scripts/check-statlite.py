#!/usr/bin/env python3
"""Verify the JDBC app is collected by an exact StatLite v0.5.0 binary."""

import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
APP = HERE.parent / "jdbc"
FIXTURE = HERE.parent / "fixture" / "server.py"


def get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read()


def wait_for(url, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            return get(url)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    raise RuntimeError(f"timed out waiting for {url}")


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--statlite-bin", type=Path, required=True)
    args = parser.parse_args()
    version = subprocess.check_output((str(args.statlite_bin), "--version"), text=True).strip()
    if version != "statlite v0.5.0":
        raise SystemExit(f"Expected StatLite v0.5.0, got {version}")
    with tempfile.TemporaryDirectory(prefix="stars-statlite-") as temporary:
        work = Path(temporary)
        logs = [open(work / name, "w") for name in ("fixture.log", "app.log", "statlite.log")]
        processes = []
        try:
            fixture = subprocess.Popen((sys.executable, str(FIXTURE), "--port", "18080"),
                                       stdout=logs[0], stderr=subprocess.STDOUT)
            processes.append(fixture)
            wait_for("http://127.0.0.1:18080/healthz")
            app = subprocess.Popen((str(APP / "run.sh"),
                                    f"--spring.datasource.url=jdbc:h2:file:{work / 'starsdb'}",
                                    "--app.github.api-base-url=http://127.0.0.1:18080",
                                    "--app.poll.initial-delay-ms=600000"),
                                   stdout=logs[1], stderr=subprocess.STDOUT)
            processes.append(app)
            wait_for("http://127.0.0.1:8080/actuator/health")
            monitor = subprocess.Popen((str(args.statlite_bin), "--config", str(APP / "statlite.yaml")),
                                       cwd=work, stdout=logs[2], stderr=subprocess.STDOUT)
            processes.append(monitor)
            target = urllib.parse.quote("star-pulse-jdbc")
            status_url = f"http://127.0.0.1:9091/api/v1/status?target={target}"
            end = time.monotonic() + 65
            status = None
            while time.monotonic() < end:
                try:
                    status = json.loads(get(status_url))
                    if status.get("collection_status") == "ok":
                        break
                except (urllib.error.URLError, TimeoutError):
                    pass
                time.sleep(2)
            if status is None or status.get("collection_status") != "ok":
                raise RuntimeError(f"StatLite did not collect app: {status}")
            if status.get("application_health") != "UP":
                raise RuntimeError(f"StatLite did not collect application health: {status}")
            metrics = json.loads(get(f"http://127.0.0.1:9091/api/v1/metrics?target={target}"))
            if not any(point.get("runtime_memory_bytes") is not None
                       for point in metrics.get("points", [])):
                raise RuntimeError(f"StatLite did not collect JVM memory: {metrics}")
            result = {"version": version, "status": status, "metrics": metrics}
            output = HERE.parent / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output.mkdir(parents=True)
            (output / "statlite-check.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps({"version": version, "collection_status": status.get("collection_status"),
                              "application_health": status.get("application_health"),
                              "metric_points": len(metrics.get("points", [])),
                              "report": str(output / "statlite-check.json")}, indent=2))
        except Exception:
            for name in ("fixture.log", "app.log", "statlite.log"):
                print(f"{name}: {(work / name).read_text()[-4000:]}", file=sys.stderr)
            raise
        finally:
            for process in reversed(processes):
                stop(process)
            for log in logs:
                log.close()


if __name__ == "__main__":
    main()
