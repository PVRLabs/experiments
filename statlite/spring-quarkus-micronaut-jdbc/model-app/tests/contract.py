#!/usr/bin/env python3
"""Exercise packaged JVM applications against a controllable real replay fixture.

Build each selected application with mvn-lite package before running this script.
This accelerated contract check is not a framework performance measurement.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fixture"))
from server import Replay, load_samples  # noqa: E402

ENDPOINTS = {
    "spring": ("/actuator/health", "/actuator/prometheus", "target/market-replay-spring-0.1.0-SNAPSHOT.jar"),
    "quarkus": ("/q/health", "/q/metrics", "target/quarkus-app/quarkus-run.jar"),
    "micronaut": ("/health", "/prometheus", "target/market-replay-micronaut-0.1.0-SNAPSHOT.jar"),
}


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=3) as response:
        return response.read()


def rows(base):
    return json.loads(get(base, "/api/quotes/history"))


def wait_for(predicate, process, description, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"application exited ({process.returncode}) while waiting for {description}")
        try:
            value = predicate()
            if value:
                return value
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {description}")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def stop(process):
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def verify(framework, statlite=None):
    health_path, metrics_path, artifact = ENDPOINTS[framework]
    jar = ROOT / f"{framework}-app" / artifact
    check(jar.is_file(), f"missing {jar}; run mvn-lite package first")
    replay = Replay(load_samples(), step_seconds=3600)
    fixture_lock = threading.Lock()
    released = threading.Event()
    released.set()
    fixture_state = {"payload": replay.current(), "status": 200, "requests": 0, "release": released}

    def hold_response(payload, status):
        release = threading.Event()
        with fixture_lock:
            fixture_state.update(payload=payload, status=status, requests=0, release=release)
        return release

    def received_requests(count):
        with fixture_lock:
            return fixture_state["requests"] >= count

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            with fixture_lock:
                body = json.dumps(fixture_state["payload"]).encode()
                status = fixture_state["status"]
                release = fixture_state["release"]
                fixture_state["requests"] += 1
            if not release.wait(timeout=30):
                return
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=fixture.serve_forever, daemon=True)
    thread.start()
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix=f"market-{framework}-") as directory:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            base = f"http://127.0.0.1:{port}"
            env = dict(os.environ, SERVER_PORT=str(port),
                       MARKET_FIXTURE_URL=f"http://127.0.0.1:{fixture.server_port}/quotes",
                       MARKET_DB_URL=f"jdbc:h2:file:{directory}/quotes;DB_CLOSE_ON_EXIT=FALSE",
                       MARKET_POLL_INTERVAL_MS="100", MARKET_POLL_INITIAL_DELAY_MS="0")
            log_path = Path(directory) / "app.log"
            with log_path.open("w+") as log:
                def start():
                    return subprocess.Popen(["java", "-jar", str(jar)], cwd=ROOT / f"{framework}-app",
                                            env=env, stdout=log, stderr=subprocess.STDOUT)

                try:
                    process = start()
                    wait_for(lambda: len(rows(base)) >= 6, process, "initial and repeated persisted polls")
                    latest = json.loads(get(base, "/api/quotes/latest"))
                    check([row["symbol"] for row in latest] == ["AAPL", "GOOG", "NVDA"], "latest symbol order")
                    check([row["price"] for row in latest] == [331.61, 341.91, 229.32], "checked-in sample prices")
                    check(all(row["sampleIndex"] == 0 and row["cycle"] == 0 and row["marketTime"] == "09:30"
                              for row in latest), "replay metadata")
                    check(all(set(row) == {"id", "fetchedAt", "cycle", "sampleIndex", "marketTime", "symbol", "price"}
                              for row in latest), "observation JSON contract")
                    for asset in ("/", "/index.html", "/app.js", "/styles.css", "/chart.umd.min.js", "/favicon.svg"):
                        body = get(base, asset)
                        name = "index.html" if asset == "/" else asset.lstrip("/")
                        expected = (ROOT / "spring-app/src/main/resources/static" / name).read_bytes()
                        check(body == expected, f"shared asset differs: {asset}")
                    health = json.loads(get(base, health_path))
                    check(health.get("status") == "UP", "application health")
                    if framework == "micronaut":
                        check(health.get("details", {}).get("jdbc", {}).get("status") == "UP", "visible JDBC health")
                    metrics = get(base, metrics_path).decode()
                    for family in ("jvm_memory_used_bytes", "process_cpu_usage", "process_start_time_seconds",
                                   "http_server_requests_seconds_count"):
                        check(family in metrics, f"missing metrics family {family}")

                    if statlite:
                        command = [str(statlite), "inspect", base]
                        if framework != "spring":
                            command += ["--type", framework]
                        inspected = subprocess.run(command,
                                                   capture_output=True, text=True, timeout=15)
                        check(inspected.returncode == 0, inspected.stdout + inspected.stderr)
                        if framework != "spring":
                            check("Compatibility: compatible" in inspected.stdout, inspected.stdout)
                        print(f"PASS {framework}: StatLite inspection compatible", flush=True)

                    # Malformed responses and HTTP failures must leave stored batches intact.
                    bad_payload = copy.deepcopy(replay.current())
                    bad_payload["quotes"][2]["symbol"] = "AAPL"
                    wrong_time = copy.deepcopy(replay.current())
                    wrong_time["marketTime"] = "09:31"
                    bad_price = copy.deepcopy(replay.current())
                    bad_price["quotes"][2]["price"] = -1
                    unknown_symbol = copy.deepcopy(replay.current())
                    unknown_symbol["quotes"][2]["symbol"] = "UNKNOWN"
                    for payload, status in ((bad_payload, 200), (wrong_time, 200),
                                            (bad_price, 200), (unknown_symbol, 200), (None, 200),
                                            (replay.current(), 503)):
                        release = hold_response(payload, status)
                        # A serial poll reaching the new response proves the previous
                        # valid poll has finished, including its DB commit. Hold this
                        # response until the baseline is read, then observe two completed
                        # failing polls via the arrival of a third request.
                        wait_for(lambda: received_requests(1), process, "first failing fixture request")
                        before = rows(base)
                        release.set()
                        wait_for(lambda: received_requests(3), process, "two completed failing polls")
                        check(rows(base) == before, "failed poll changed stored history")
                    with fixture_lock:
                        fixture_state.update(payload=replay.current(), status=200)
                    wait_for(lambda: len(rows(base)) > len(before), process, "recovery after failed polls")

                    # The file-backed DB must survive an app restart with schema initialization repeated.
                    release = hold_response(replay.current(), 503)
                    wait_for(lambda: received_requests(1), process, "poll settled before restart")
                    persisted = rows(base)
                    release.set()
                    stop(process)
                    process = start()
                    wait_for(lambda: rows(base) == persisted, process, "persisted history after restart")
                    print(f"PASS {framework}: polling, payloads, assets, health/metrics, failure/recovery, file restart", flush=True)
                except Exception:
                    stop(process)
                    log.flush()
                    print(log_path.read_text()[-12000:], file=sys.stderr)
                    raise
                finally:
                    stop(process)
                    process = None
    finally:
        with fixture_lock:
            fixture_state["release"].set()
        stop(process)
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", nargs="+", choices=ENDPOINTS, default=list(ENDPOINTS))
    parser.add_argument("--statlite", type=Path, help="optional candidate binary for typed endpoint inspection")
    args = parser.parse_args()
    for framework in args.framework:
        verify(framework, args.statlite.resolve() if args.statlite else None)


if __name__ == "__main__":
    main()
