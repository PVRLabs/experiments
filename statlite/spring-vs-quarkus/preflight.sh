#!/usr/bin/env bash
set -euo pipefail
OUT=${1:-/home/ubuntu/preflight.txt}
exec > >(tee "$OUT") 2>&1
date --iso-8601=seconds
echo '== identity =='; cat /etc/os-release; uname -a; uname -m
echo '== resources =='; free -h; swapon --show; df -h /
echo '== java =='; /usr/local/bin/java -version
echo '== statlite =='; file /usr/local/bin/statlite; /usr/local/bin/statlite --version
echo '== files =='; ls -l /opt/spring-stars/stars.jar /opt/quarkus-stars/quarkus-run.jar /etc/statlite/statlite.yaml
echo '== services before start =='; systemctl show spring-stars.service quarkus-stars.service statlite.service -p ActiveState -p SubState -p MainPID -p NRestarts
start_ready() {
  local service=$1 url=$2 code=''
  echo "== start $service =="; date --iso-8601=seconds; systemctl start "$service"
  for _ in $(seq 1 90); do code=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' "$url" || true); [ "$code" = 200 ] && break; sleep 2; done
  echo "$service readiness=$code"; systemctl show "$service" -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStartTimestamp -p ExecMainStatus
  if [[ "$code" != 200 ]] || ! systemctl is-active --quiet "$service"; then
    echo "readiness failed: $service" >&2
    return 1
  fi
}
start_ready spring-stars.service http://127.0.0.1:8080/
start_ready quarkus-stars.service http://127.0.0.1:8081/
start_ready statlite.service http://127.0.0.1:9090/healthz
echo '== effective cmdlines =='; ps -ww -eo user,pid,rss,vsz,etime,args | grep -E 'java|/usr/local/bin/statlite' | grep -v grep || true
echo '== required endpoint status =='
assert_http_200() {
  local url=$1 code
  code=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "$url" || true)
  printf '%s %s\n' "$code" "$url"
  [[ "$code" == 200 ]]
}
for url in http://127.0.0.1:8080/ http://127.0.0.1:8080/actuator/health http://127.0.0.1:8080/actuator/prometheus http://127.0.0.1:8081/ http://127.0.0.1:8081/q/metrics http://127.0.0.1:8081/q/health http://127.0.0.1:9090/ http://127.0.0.1:9090/healthz http://127.0.0.1:9090/api/summary http://127.0.0.1:9090/statlite/metrics; do assert_http_200 "$url"; done
assert_h2_console_absent() {
  local endpoint=$1 headers; headers=$(mktemp)
  if ! curl -sS --max-time 5 --location --dump-header "$headers" --output /dev/null "$endpoint"; then
    cat "$headers"
    rm -f "$headers"
    return 1
  fi
  cat "$headers"
  if awk '$1 ~ /^HTTP\// { count++; if ($2 != 404) bad=1 } END { exit (count == 1 && bad == 0) ? 0 : 1 }' "$headers"; then echo "H2 console absent: $endpoint"; else echo "H2 console exposed or inconclusive: $endpoint"; rm -f "$headers"; return 1; fi
  rm -f "$headers"
}
echo '== h2 checks =='; assert_h2_console_absent http://127.0.0.1:8080/h2-console; assert_h2_console_absent http://127.0.0.1:8081/h2-console
echo '== statlite summary =='; curl -sS http://127.0.0.1:9090/api/summary; echo
echo '== listeners =='; ss -ltnp
echo '== system state =='; systemctl show spring-stars.service quarkus-stars.service statlite.service -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStartTimestamp -p ExecMainStatus
