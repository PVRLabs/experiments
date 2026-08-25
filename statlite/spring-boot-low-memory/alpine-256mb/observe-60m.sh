#!/usr/bin/env bash
set -u

# Run this on the host after the Alpine VPS services are up. It uses SSH rather
# than Multipass and saves raw checkpoints locally.

SSH_TARGET="${SSH_TARGET:?set SSH_TARGET=user@host}"
SSH_PORT="${SSH_PORT:-22}"
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
RESULTS_DIR="$SCRIPT_DIR/results/observation-$STAMP"

mkdir -p "$RESULTS_DIR"

timestamp() {
	date '+%Y-%m-%dT%H:%M:%S%z'
}

remote_exec() {
	ssh -p "$SSH_PORT" "$SSH_TARGET" sh -s <<< "$1"
}

record_snapshot() {
	name="$1"
	printf '%s snapshot %s\n' "$(timestamp)" "$name" | tee -a "$RESULTS_DIR/run.log"
	if ! remote_exec /usr/local/sbin/alpine-vps-snapshot >"$RESULTS_DIR/$name.txt" 2>&1; then
		printf 'snapshot command failed: %s\n' "$name" | tee -a "$RESULTS_DIR/run.log"
	fi
}

sleep_until() {
	deadline="$1"
	now="$(date +%s)"
	remaining=$((deadline - now))
	if (( remaining > 0 )); then
		sleep "$remaining"
	fi
}

printf 'ssh_target: %s\n' "$SSH_TARGET" | tee "$RESULTS_DIR/run.log"
printf 'ssh_port: %s\n' "$SSH_PORT" | tee -a "$RESULTS_DIR/run.log"
printf 'results: %s\n' "$RESULTS_DIR" | tee -a "$RESULTS_DIR/run.log"
if ! remote_exec 'set -eu
[ -x /usr/local/sbin/alpine-vps-snapshot ]
rc-service stars status
rc-service statlite status
free -h
cat /proc/swaps
grep -q ^/ /proc/swaps' \
	>"$RESULTS_DIR/preflight.txt" 2>&1; then
	printf 'preflight failed; stopping before the one-hour observation\n' \
		| tee -a "$RESULTS_DIR/run.log" >&2
	exit 1
fi

record_snapshot spring-statlite-settled
started_at="$(date +%s)"
printf 'observation_started: %s\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"

sleep_until $((started_at + 90))
record_snapshot after-several-polls

printf '%s bounded traffic\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
remote_exec 'for i in 1 2 3 4 5 6 7 8 9 10 11 12; do for url in http://127.0.0.1:8080/actuator/health http://127.0.0.1:8080/actuator/metrics/jvm.memory.used http://127.0.0.1:9090/ http://127.0.0.1:9090/healthz http://127.0.0.1:9090/api/summary http://127.0.0.1:9090/statlite/metrics; do curl -sS --max-time 5 -o /dev/null -w "%{http_code} $url\n" "$url" || true; done; done' \
	>"$RESULTS_DIR/bounded-traffic.txt" 2>&1 || true

sleep_until $((started_at + 180))
record_snapshot after-workload

sleep_until $((started_at + 3600))
record_snapshot end-of-60-minute-observation
remote_exec 'for log in /var/log/stars/* /var/log/statlite/*; do [ -f "$log" ] && { echo "== $log =="; cat "$log"; }; done; dmesg 2>/dev/null | tail -200' \
	>"$RESULTS_DIR/services-logs-and-kernel.txt" 2>&1 || true
printf 'observation_finished: %s\n' "$(timestamp)" | tee -a "$RESULTS_DIR/run.log"
