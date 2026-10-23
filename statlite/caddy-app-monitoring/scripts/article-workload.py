#!/usr/bin/env python3
"""Run inside the guest; preserve timestamped traffic and read-only API evidence."""
import concurrent.futures
import datetime
import json
import subprocess
import time
import urllib.request
from pathlib import Path


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


ROOT = Path("run") / ("article-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
ROOT.mkdir(parents=True)
TARGETS = ("express-via-caddy", "spring-via-caddy", "spring-direct")


def capture(stage):
    for target in TARGETS:
        for endpoint in ("v1/status", "v1/metrics", "summary", "series", "events"):
            query = f"target={target}" + ("" if endpoint.startswith("v1/") else "&range=1h")
            url = f"http://127.0.0.1:9090/api/{endpoint}?{query}"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.load(response)
            (ROOT / f"{stage}-{target}-{endpoint.replace('/', '-')}.json").write_text(json.dumps(data, indent=2) + "\n")
    with urllib.request.urlopen("http://127.0.0.1:2019/metrics", timeout=10) as response:
        (ROOT / f"{stage}-caddy.txt").write_bytes(response.read())


def request(host, route, expected):
    result = subprocess.run(["curl", "--noproxy", "*", "--max-time", "5", "-sS", "-o", "/dev/null", "-w", "%{http_code} %{time_total}", f"https://{host}/{route}"], capture_output=True, text=True, check=True)
    code, elapsed = result.stdout.split()
    if int(code) != expected:
        raise RuntimeError(f"{host}/{route}: expected {expected}, got {code}")
    return dict(at=now(), host=host, route=route, status=int(code), seconds=float(elapsed))


manifest = dict(started_at=now(), directory=str(ROOT), phase_seconds=120, tick_seconds=1, phases=[])
print(ROOT, flush=True)
capture("before")
with (ROOT / "traffic.jsonl").open("w") as traffic, concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    for name, route, code in (("baseline", "ok", 200), ("not-found", "missing", 404), ("server-errors", "fail", 500), ("slow", "slow", 200), ("recovery", "ok", 200)):
        phase = dict(name=name, started_at=now(), express_route=route, expected_status=code, ticks=120)
        manifest["phases"].append(phase)
        print(name, phase["started_at"], flush=True)
        start = time.monotonic()
        for tick in range(120):
            futures = [pool.submit(request, "express.test", route, code), pool.submit(request, "spring.test", "ok", 200)]
            for future in futures:
                traffic.write(json.dumps(dict(phase=name, **future.result())) + "\n")
            traffic.flush()
            time.sleep(max(0, start + tick + 1 - time.monotonic()))
        phase["ended_at"] = now()
        capture(name)
        (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
time.sleep(40)  # Let the next ordinary poll collect the final requests.
capture("final")
manifest["finished_at"] = now()
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("COMPLETE", now(), flush=True)
