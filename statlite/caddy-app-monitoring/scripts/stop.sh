#!/bin/bash
set -euo pipefail
for service in statlite caddy spring express; do
  file="run/$service.pid"
  if [ -f "$file" ]; then
    kill "$(cat "$file")" 2>/dev/null || true
    rm "$file"
  fi
done
