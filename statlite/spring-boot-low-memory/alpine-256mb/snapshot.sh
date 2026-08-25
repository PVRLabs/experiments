#!/bin/sh
set -u

# Manual checkpoint for this Alpine experiment. This is not a background
# monitor and intentionally uses the fixed experiment paths.

printf 'snapshot_time: '
date '+%Y-%m-%dT%H:%M:%S%z'
printf '\n'

printf '%s\n' '== release and kernel =='
cat /etc/alpine-release 2>/dev/null || true
uname -a
uname -m

printf '%s\n' '== runtime identity =='
java -version 2>&1 || true
file /usr/local/bin/statlite 2>/dev/null || true
printf 'statlite_sha256: '
sha256sum /usr/local/bin/statlite 2>/dev/null | awk '{ print $1 }' || true

printf '%s\n' '== uptime and load =='
uptime

printf '%s\n' '== memory =='
free -h

printf '%s\n' '== swap =='
cat /proc/swaps 2>/dev/null || true
free -h | awk 'NR == 1 || NR == 3 { print }'

printf '%s\n' '== root filesystem =='
df -h /

service_pid() {
	service=$1
	pidfile="/run/${service}.pid"
	if [ -r "$pidfile" ]; then
		pid=$(cat "$pidfile" 2>/dev/null || true)
		case "$pid" in
			''|*[!0-9]*) ;;
			*) printf '%s\n' "$pid"; return ;;
		esac
	fi
	printf '%s\n' ''
}

print_process() {
	label=$1
	pid=$2
	if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
		printf '%s: not running\n' "$label"
		return
	fi
	printf '%s:\n' "$label"
	ps -p "$pid" -o pid=,rss=,vsz=,pcpu=,etime=,args= 2>/dev/null || true
}

STARS_PID=$(service_pid stars)
STATLITE_PID=$(service_pid statlite)

printf '%s\n' '== processes =='
print_process spring_boot "$STARS_PID"
print_process statlite "$STATLITE_PID"

if [ -n "$STARS_PID" ] && [ -n "$STATLITE_PID" ]; then
	combined_rss=$(ps -p "$STARS_PID,$STATLITE_PID" -o rss= 2>/dev/null \
		| awk '{ total += $1 } END { print total + 0 }')
	printf 'combined_rss_kb: %s\n' "$combined_rss"
else
	printf '%s\n' 'combined_rss_kb: unavailable (both services are not running)'
fi

print_size() {
	label=$1
	path=$2
	if [ -e "$path" ]; then
		printf '%s: ' "$label"
		du -sh "$path"
	else
		printf '%s: unavailable (%s does not exist)\n' "$label" "$path"
	fi
}

printf '%s\n' '== data sizes =='
print_size h2_data /opt/stars-app/data
print_size statlite_sqlite_data /var/lib/statlite

printf '%s\n' '== openrc =='
for service in stars statlite; do
	printf -- '-- %s --\n' "$service"
	rc-service "$service" status 2>&1 || true
done

printf '%s\n' '== application logs =='
for log in /var/log/stars/* /var/log/statlite/*; do
	if [ -f "$log" ]; then
		printf -- '-- %s (tail) --\n' "$log"
		tail -40 "$log"
	fi
done

printf '%s\n' '== kernel tail =='
dmesg 2>/dev/null | tail -40 || true
