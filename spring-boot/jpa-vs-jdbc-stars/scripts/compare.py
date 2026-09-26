#!/usr/bin/env python3
"""Run the Stars JPA and JDBC jars with the same local workload and JVM."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
JDBC = ROOT / "jdbc"
BASELINE = ROOT / "jpa"
FIXTURE = ROOT / "fixture" / "server.py"
JAVA_FLAGS = (
    "-Xms16m", "-Xmx80m", "-Xss256k", "-XX:+UseSerialGC",
    "-XX:TieredStopAtLevel=1", "-XX:ReservedCodeCacheSize=32m",
    "-XX:+UseCompactObjectHeaders",
)
REPOS = "PVRLabs/statlite,PVRLabs/aibadger,scriptella/scriptella-etl"
FIXTURE_PORT = 18080
APP_PORT = 18081
SECONDS = 60
WARMUP_SECONDS = 30


def request(url, method="GET"):
    with urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=10) as response:
        return response.read()


def ready(url, process, timeout=40):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if process.poll() is not None:
            raise RuntimeError(f"process exited with status {process.returncode}")
        try:
            request(url)
            return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError(f"timeout waiting for {url}")


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def rss_kib(pid):
    result = subprocess.check_output(("ps", "-o", "rss=", "-p", str(pid)), text=True)
    return int(result.strip())


def run_variant(name, jar, output):
    work = output / name
    (work / "data").mkdir(parents=True)
    command = ["java", *JAVA_FLAGS, "-jar", str(jar),
               f"--server.port={APP_PORT}",
               f"--spring.datasource.url=jdbc:h2:file:{work / 'data' / 'starsdb'}",
               "--app.github.api-base-url=http://127.0.0.1:18080",
               f"--app.github.repos={REPOS}",
               "--app.github.initial-delay-ms=600000",
               "--app.github.poll-interval-ms=600000",
               "--app.poll.initial-delay-ms=600000"]
    with (work / "application.log").open("w") as log:
        start = time.monotonic()
        process = subprocess.Popen(command, cwd=work, stdout=log, stderr=subprocess.STDOUT)
        try:
            ready(f"http://127.0.0.1:{APP_PORT}/", process)
            startup_seconds = round(time.monotonic() - start, 3)
            request(f"http://127.0.0.1:{APP_PORT}/refresh", "POST")
            warmup_until = time.monotonic() + WARMUP_SECONDS
            while time.monotonic() < warmup_until:
                exercise_app()
                time.sleep(5)
            samples = []
            until = time.monotonic() + SECONDS
            while time.monotonic() < until:
                exercise_app()
                samples.append(rss_kib(process.pid))
                time.sleep(5)
            return {"name": name, "startup_seconds": startup_seconds,
                    "rss_kib": samples, "rss_median_kib": median(samples),
                    "dashboard_requests": len(samples) + WARMUP_SECONDS // 5,
                    "jar_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(), "pid": process.pid}
        finally:
            stop(process)


def exercise_app():
    base = f"http://127.0.0.1:{APP_PORT}"
    body = request(base + "/")
    if b"Star Pulse" not in body:
        raise RuntimeError("dashboard response did not contain Star Pulse")
    for count in (b"142", b"87", b"63"):
        if count not in body:
            raise RuntimeError(f"dashboard response missing fixture count {count!r}")
    if b"UP" not in request(base + "/actuator/health"):
        raise RuntimeError("Actuator health is not UP")
    request(base + "/actuator/metrics")
    if b"jvm_memory_used_bytes" not in request(base + "/actuator/prometheus"):
        raise RuntimeError("Prometheus JVM metrics missing")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reverse", action="store_true", help="run JDBC before JPA")
    args = parser.parse_args()
    jars = {
        "jpa": BASELINE / "target" / "stars-0.0.1-SNAPSHOT.jar",
        "jdbc": JDBC / "target" / "stars-jdbc-0.0.1-SNAPSHOT.jar",
    }
    for jar in jars.values():
        if not jar.is_file():
            raise SystemExit(f"Build the missing jar first: {jar}")
    if args.reverse:
        jars = dict(reversed(list(jars.items())))
    output = ROOT / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True)
    with (output / "fixture.log").open("w") as log:
        fixture = subprocess.Popen((sys.executable, str(FIXTURE), "--port", str(FIXTURE_PORT)),
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            ready(f"http://127.0.0.1:{FIXTURE_PORT}/healthz", fixture)
            results = [run_variant(name, jar, output) for name, jar in jars.items()]
        finally:
            stop(fixture)
    report = {"captured_at": datetime.now(timezone.utc).isoformat(),
              "host": platform.platform(), "java": subprocess.check_output(
                  ("java", "-version"), stderr=subprocess.STDOUT, text=True).splitlines()[0],
              "jvm_flags": JAVA_FLAGS, "sample_seconds": SECONDS,
              "warmup_seconds": WARMUP_SECONDS, "order": list(jars),
              "fixture": str(FIXTURE), "variants": results}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(output / "report.json"), "variants": results}, indent=2))


if __name__ == "__main__":
    main()
