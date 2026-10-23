#!/bin/bash
set -euo pipefail
case "$*" in
  ""|--fresh-history) ;;
  *) echo "Usage: $0 [--fresh-history]" >&2; exit 2 ;;
esac
mkdir -p run
# Refuse to overwrite live PID records on an accidental second start.
for pidfile in run/*.pid; do
  [ -f "$pidfile" ] || continue
  if kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "Already running: $pidfile; stop the environment first" >&2; exit 1
  fi
done
# Archive the complete SQLite file family only after all service PID checks pass.
if [ "${1:-}" = --fresh-history ]; then
  history_archive=""
  for file in run/statlite.sqlite{,-wal,-shm,-journal}; do
    [ -e "$file" ] || continue
    if [ -z "$history_archive" ]; then
      history_archive=$(mktemp -d run/history-XXXXXXXX)
    fi
    mv "$file" "$history_archive/"
  done
  if [ -n "$history_archive" ]; then
    printf 'Previous observation database preserved in %s\n' "$history_archive"
  fi
fi
nohup node express/app.js >run/express.log 2>&1 & echo $! >run/express.pid
nohup java -Xmx256m -jar spring/target/spring-0.0.1-SNAPSHOT.jar >run/spring.log 2>&1 & echo $! >run/spring.pid
XDG_DATA_HOME="$PWD/run/caddy-data" nohup run/bin/caddy run --config Caddyfile --adapter caddyfile >run/caddy.log 2>&1 & echo $! >run/caddy.pid
for attempt in {1..60}; do
  if curl -fsS http://127.0.0.1:8081/actuator/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:3000/ok >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8081/actuator/health
# Trust only this guest's local Caddy CA; no macOS trust-store change.
sudo run/bin/caddy trust --address 127.0.0.1:2019
curl -fsS https://express.test/ok
curl -fsS https://spring.test/ok
nohup run/bin/statlite --config statlite.yaml >run/statlite.log 2>&1 & echo $! >run/statlite.pid
