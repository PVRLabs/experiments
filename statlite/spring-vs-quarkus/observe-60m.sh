#!/usr/bin/env bash
set -u
VM_NAME=${VM_NAME:-statlite-svq-512}
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
STAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR=${RESULTS_DIR:-$SCRIPT_DIR/results/observation-$STAMP}
mkdir -p "$RESULTS_DIR"
timestamp() { date '+%Y-%m-%dT%H:%M:%S%z'; }
vm_exec() { multipass exec "$VM_NAME" -- bash -lc "$1"; }
snapshot() { local name=$1; printf '%s snapshot %s\n' "$(timestamp)" "$name" | tee -a "$RESULTS_DIR/run.log"; vm_exec 'sudo /usr/local/sbin/svq-snapshot' >"$RESULTS_DIR/$name.txt" 2>&1 || printf 'snapshot failed: %s\n' "$name" | tee -a "$RESULTS_DIR/run.log"; }
sleep_until() { local remain=$(( $1 - $(date +%s) )); (( remain > 0 )) && sleep "$remain"; }
printf 'vm: %s\nresults: %s\n' "$VM_NAME" "$RESULTS_DIR" | tee "$RESULTS_DIR/run.log"
vm_exec 'sudo cat /home/ubuntu/preflight.txt' >"$RESULTS_DIR/preflight.txt" 2>&1 || true
snapshot side-by-side-settled
started_at=$(date +%s); printf 'observation_started: %s\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
sleep_until $((started_at + 90)); snapshot after-several-polls
printf '%s bounded traffic\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
vm_exec 'for url in http://127.0.0.1:8080/ http://127.0.0.1:8080/actuator/health http://127.0.0.1:8080/actuator/prometheus http://127.0.0.1:8081/ http://127.0.0.1:8081/q/metrics http://127.0.0.1:8081/q/health http://127.0.0.1:9090/ http://127.0.0.1:9090/healthz http://127.0.0.1:9090/api/summary http://127.0.0.1:9090/api/summary?target=spring-stars\&range=1h http://127.0.0.1:9090/api/series?target=spring-stars\&range=1h http://127.0.0.1:9090/api/events?target=spring-stars\&range=1h\&limit=20 http://127.0.0.1:9090/api/summary?target=quarkus-stars\&range=1h http://127.0.0.1:9090/api/series?target=quarkus-stars\&range=1h http://127.0.0.1:9090/api/events?target=quarkus-stars\&range=1h\&limit=20 http://127.0.0.1:9090/api/summary?target=statlite-self\&range=1h http://127.0.0.1:9090/api/series?target=statlite-self\&range=1h http://127.0.0.1:9090/api/events?target=statlite-self\&range=1h\&limit=20 http://127.0.0.1:9090/statlite/metrics; do printf "%s " "$url"; curl -sS --max-time 10 -o /dev/null -w "%{http_code}\n" "$url" || true; done' >"$RESULTS_DIR/bounded-traffic.txt" 2>&1 || true
sleep_until $((started_at + 180)); snapshot after-workload
sleep_until $((started_at + 3600)); snapshot end-of-60-minute-observation
vm_exec 'sudo journalctl -u spring-stars.service -u quarkus-stars.service -u statlite.service --since "70 minutes ago" --no-pager' >"$RESULTS_DIR/services-journal.txt" 2>&1 || true
vm_exec 'sudo dmesg --ctime | tail -80' >"$RESULTS_DIR/kernel-tail.txt" 2>&1 || true
printf 'observation_finished: %s\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
printf 'result_dir=%s\n' "$RESULTS_DIR"
