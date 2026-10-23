#!/bin/bash
set -euo pipefail
command -v python3 >/dev/null
mkdir -p run
targets=(express-via-caddy spring-via-caddy spring-direct)
capture() {
  local stage=$1 target endpoint
  for target in "${targets[@]}"; do
    for endpoint in status metrics; do
      curl -fsS "http://127.0.0.1:9090/api/v1/$endpoint?target=$target" >"run/$target-$stage-$endpoint.json"
    done
  done
}
# Startup traffic has already introduced both hosts. Wait for a regular baseline.
sleep 35
capture baseline
curl -fsS http://127.0.0.1:2019/metrics >run/metrics-before.txt
for host in express.test spring.test; do
  for route in ok fail slow; do
    expected=200; [ "$route" != fail ] || expected=500
    code=$(curl --noproxy '*' -sS -o /dev/null -w '%{http_code}' "https://$host/$route")
    printf '%s /%s %s\n' "$host" "$route" "$code"
    [ "$code" = "$expected" ]
  done
  curl -fsS http://127.0.0.1:2019/metrics >"run/metrics-after-${host}.txt"
done
# Two more ordinary polling intervals, with no debug/manual polls.
sleep 35
sleep 30
capture workload
for target in "${targets[@]}"; do
  curl -fsS "http://127.0.0.1:9090/api/v1/events?target=$target" >"run/$target-events.json"
done
# One asymmetric request checks that Spring histories do not gain Express traffic.
curl -fsS https://express.test/ok
sleep 35
capture isolation
python3 scripts/check-smoke.py run
printf 'Monitoring assertions passed; raw evidence saved under run/.\n'
