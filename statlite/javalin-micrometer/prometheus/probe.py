"""Small workload and StatLite collection check; Python standard library only."""
from datetime import datetime
import json
import time
import urllib.error
import urllib.request

APP = "http://127.0.0.1:18087"
STATLITE = "http://127.0.0.1:19087"


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def get(url):
    code, body = fetch(url)
    assert code == 200, (url, code)
    return json.loads(body)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


before = get(APP + "/statlite/metrics")
# Establish a collector baseline before traffic, including after a restart.
deadline = time.monotonic() + 15
while True:
    latest = get(STATLITE + "/api/latest")
    if latest["status"] == "ok" and parse_time(latest["result"]["process_start_time"]) == parse_time(before["started_at"]):
        break
    assert time.monotonic() < deadline, "No StatLite baseline collected"
    time.sleep(0.25)
for _ in range(12):
    for path, expected in [("/hello", 200), ("/slow", 200), ("/missing", 404), ("/error", 500)]:
        code, _ = fetch(APP + path)
        assert code == expected, (path, code)
    time.sleep(0.25)  # Spread traffic across the demo's two-second polls.
time.sleep(0.1)  # Let Javalin's request logger finish.
after = get(APP + "/statlite/metrics")
for key, expected in {"requests_total": 48, "responses_404_total": 12,
                      "responses_4xx_total": 12, "responses_5xx_total": 12}.items():
    assert after["metrics"][key] - before["metrics"][key] == expected, key
duration = after["metrics"]["request_duration_seconds_total"] - before["metrics"]["request_duration_seconds_total"]
assert duration >= 1.32, duration
deadline = time.monotonic() + 15
while True:
    latest = get(STATLITE + "/api/latest")
    if latest["status"] == "ok":
        samples = {sample["key"]: sample["value"] for sample in latest["result"]["samples"]}
        if samples.get("http_requests_total") == after["metrics"]["requests_total"]:
            for key in ["http_404_total", "http_4xx_total", "http_5xx_total"]:
                assert samples[key] >= 12, key
            assert samples["runtime_heap_used_bytes"] > 0
            assert "process_cpu_usage" in samples
            assert latest["result"]["health_status"] == "UP"
            break
    assert time.monotonic() < deadline, "Workload did not appear in StatLite"
    time.sleep(0.25)
print(json.dumps({"requests": 48, "404_and_4xx": 12, "5xx": 12,
                  "duration_seconds": duration, "average_latency_ms": duration / 48 * 1000,
                  "statlite_run_id": latest["app_run_id"]}, indent=2))
