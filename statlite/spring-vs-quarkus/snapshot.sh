#!/usr/bin/env bash
set -u
printf 'snapshot_time: '; date --iso-8601=seconds
echo '== uptime and load =='; uptime
echo '== memory =='; free -h
echo '== swap =='; swapon --show; free -h | awk 'NR == 1 || NR == 3 { print }'
echo '== root filesystem =='; df -h /
pid_for() { systemctl show -p MainPID --value "$1" 2>/dev/null || true; }
proc() { local label=$1 pid=$2; echo "$label:"; if [[ "$pid" =~ ^[1-9][0-9]*$ ]]; then ps -p "$pid" -o pid=,rss=,vsz=,pcpu=,etime=,args=; else echo not-running; fi; }
residency() {
  local label=$1 pid=$2
  echo "$label /proc/$pid/status:"
  if [[ "$pid" =~ ^[1-9][0-9]*$ ]]; then
    awk '$1 == "VmRSS:" || $1 == "VmSwap:" || $1 == "RssAnon:" || $1 == "RssFile:" {print}' "/proc/$pid/status" 2>/dev/null || true
    echo "$label /proc/$pid/smaps_rollup:"
    awk -F: '/^(Rss|Pss|Pss_Anon|Pss_File|Swap|SwapPss):/ {gsub(/^ +/, "", $2); print $1 ": " $2}' "/proc/$pid/smaps_rollup" 2>/dev/null || true
  else
    echo not-running
  fi
}
spring=$(pid_for spring-stars.service); quarkus=$(pid_for quarkus-stars.service); statlite=$(pid_for statlite.service)
echo '== processes =='; proc spring_boot "$spring"; proc quarkus "$quarkus"; proc statlite "$statlite"
echo '== JVM residency =='; residency spring_boot "$spring"; residency quarkus "$quarkus"
echo "combined_rss_kb: $(ps -p "$spring,$quarkus,$statlite" -o rss= 2>/dev/null | awk '{t += $1} END {print t+0}')"
echo '== data sizes =='; du -sh /opt/spring-stars/data /opt/quarkus-stars/data-quarkus /var/lib/statlite 2>/dev/null || true
echo '== endpoints =='; for url in http://127.0.0.1:8080/ http://127.0.0.1:8080/actuator/health http://127.0.0.1:8080/actuator/prometheus http://127.0.0.1:8081/ http://127.0.0.1:8081/q/metrics http://127.0.0.1:8081/q/health http://127.0.0.1:9090/ http://127.0.0.1:9090/healthz http://127.0.0.1:9090/api/summary http://127.0.0.1:9090/statlite/metrics; do printf '%s ' "$url"; curl -sS --max-time 10 -o /dev/null -w '%{http_code}\n' "$url" || true; done
echo '== service state =='; systemctl show spring-stars.service quarkus-stars.service statlite.service -p ActiveState -p SubState -p MainPID -p NRestarts -p ExecMainStartTimestamp -p ExecMainStatus
echo '== statlite summary =='; curl -sS --max-time 15 http://127.0.0.1:9090/api/summary || true; echo
echo '== recent logs =='; journalctl -u spring-stars.service -u quarkus-stars.service -u statlite.service -n 30 --no-pager
