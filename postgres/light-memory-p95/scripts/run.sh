#!/usr/bin/env bash
# Guest only. Creates a new result directory and preserves partial results.
set -euo pipefail
bundle=$(cd "$(dirname "$0")" && pwd)
out=${1:?new output directory required}
mkdir "$out"
for variant in default a b; do
  "$bundle/vm-variant.sh" "$variant" > "$out/$variant-start.txt" 2>&1
  sudo -u postgres psql -X -d experiment -c "SELECT name, setting, unit FROM pg_settings WHERE name IN ('max_connections','superuser_reserved_connections','jit','max_parallel_workers_per_gather','max_parallel_workers','shared_buffers','work_mem','maintenance_work_mem','io_method','wal_level','fsync','autovacuum') ORDER BY name" > "$out/$variant-settings.txt"
  "$bundle/driver.py" "$out/$variant" --idle 5 --warmup 20 --duration 50
  "$bundle/analyze.py" "$out/$variant" > "$out/$variant-summary.txt"
  systemctl stop postgresql@18-main
done
