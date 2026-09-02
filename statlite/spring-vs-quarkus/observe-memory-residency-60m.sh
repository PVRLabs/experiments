#!/usr/bin/env bash
set -euo pipefail
VM_NAME=${VM_NAME:-statlite-svq-512}
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
STAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR=${RESULTS_DIR:-$SCRIPT_DIR/results/memory-residency-$STAMP}
mkdir -p "$RESULTS_DIR"
timestamp() { date '+%Y-%m-%dT%H:%M:%S%z'; }
vm_exec() { multipass exec "$VM_NAME" -- bash -lc "$1"; }
snapshot() { local name=$1; printf '%s snapshot %s\n' "$(timestamp)" "$name" | tee -a "$RESULTS_DIR/run.log"; vm_exec 'sudo /usr/local/sbin/svq-snapshot' >"$RESULTS_DIR/$name.txt" 2>&1 || printf 'snapshot failed: %s\n' "$name" | tee -a "$RESULTS_DIR/run.log"; }
sleep_until() { local remain=$(( $1 - $(date +%s) )); (( remain > 0 )) && sleep "$remain"; }
deploy_phase5_scripts() {
  multipass transfer "$SCRIPT_DIR/snapshot.sh" "$VM_NAME:/home/ubuntu/phase5-snapshot.sh"
  multipass transfer "$SCRIPT_DIR/preflight.sh" "$VM_NAME:/home/ubuntu/phase5-preflight.sh"
  vm_exec 'sudo install -m 0755 /home/ubuntu/phase5-snapshot.sh /usr/local/sbin/svq-snapshot; sudo chmod 0755 /home/ubuntu/phase5-preflight.sh'
}

printf 'phase: 5 memory residency follow-up\nvm: %s\nresults: %s\n' "$VM_NAME" "$RESULTS_DIR" | tee "$RESULTS_DIR/run.log"
printf 'first_run_preserved: true\n' | tee -a "$RESULTS_DIR/run.log"
deploy_phase5_scripts
printf '%s stopping services\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
vm_exec 'sudo systemctl stop statlite.service quarkus-stars.service spring-stars.service || true; sudo systemctl reset-failed spring-stars.service quarkus-stars.service statlite.service'
printf '%s starting spring\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
vm_exec 'sudo systemctl start spring-stars.service'; vm_exec 'for i in $(seq 1 90); do curl -fsS --max-time 5 -o /dev/null http://127.0.0.1:8080/ && exit 0 || true; sleep 2; done; exit 1'
printf '%s starting quarkus\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
vm_exec 'sudo systemctl start quarkus-stars.service'; vm_exec 'for i in $(seq 1 90); do curl -fsS --max-time 5 -o /dev/null http://127.0.0.1:8081/ && exit 0 || true; sleep 2; done; exit 1'
printf '%s starting statlite\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
vm_exec 'sudo systemctl start statlite.service'; vm_exec 'for i in $(seq 1 90); do curl -fsS --max-time 5 -o /dev/null http://127.0.0.1:9090/healthz && exit 0 || true; sleep 2; done; exit 1'
vm_exec 'sudo bash /home/ubuntu/phase5-preflight.sh /home/ubuntu/phase5-preflight.txt' >"$RESULTS_DIR/preflight.txt" 2>&1
snapshot residency-settled
started_at=$(date +%s); observation_start="$(vm_exec 'date --iso-8601=seconds' | tr -d '\r')"; printf 'observation_started: %s\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"; printf 'guest_observation_start: %s\n' "$observation_start" | tee -a "$RESULTS_DIR/run.log"
sleep_until $((started_at + 90)); snapshot residency-after-90s
sleep_until $((started_at + 180)); printf '%s bounded traffic\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
vm_exec 'for url in http://127.0.0.1:8080/ http://127.0.0.1:8080/actuator/health http://127.0.0.1:8080/actuator/prometheus http://127.0.0.1:8081/ http://127.0.0.1:8081/q/metrics http://127.0.0.1:8081/q/health http://127.0.0.1:9090/ http://127.0.0.1:9090/healthz http://127.0.0.1:9090/api/summary http://127.0.0.1:9090/api/summary?target=spring-stars\&range=1h http://127.0.0.1:9090/api/series?target=spring-stars\&range=1h http://127.0.0.1:9090/api/events?target=spring-stars\&range=1h\&limit=20 http://127.0.0.1:9090/api/summary?target=quarkus-stars\&range=1h http://127.0.0.1:9090/api/series?target=quarkus-stars\&range=1h http://127.0.0.1:9090/api/events?target=quarkus-stars\&range=1h\&limit=20 http://127.0.0.1:9090/api/summary?target=statlite-self\&range=1h http://127.0.0.1:9090/api/series?target=statlite-self\&range=1h http://127.0.0.1:9090/api/events?target=statlite-self\&range=1h\&limit=20 http://127.0.0.1:9090/statlite/metrics; do printf "%s " "$url"; curl -sS --max-time 10 -o /dev/null -w "%{http_code}\n" "$url" || true; done' >"$RESULTS_DIR/bounded-traffic.txt" 2>&1
snapshot residency-after-3m
sleep_until $((started_at + 900)); snapshot residency-after-15m
sleep_until $((started_at + 1800)); snapshot residency-after-30m
sleep_until $((started_at + 3600)); snapshot residency-after-60m
vm_exec "sudo journalctl -u spring-stars.service -u quarkus-stars.service -u statlite.service --since '$observation_start' --no-pager" >"$RESULTS_DIR/services-journal.txt" 2>&1 || true
vm_exec 'sudo dmesg --ctime | tail -80' >"$RESULTS_DIR/kernel-tail.txt" 2>&1 || true
printf 'observation_finished: %s\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
