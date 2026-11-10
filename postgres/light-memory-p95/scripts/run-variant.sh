#!/usr/bin/env bash
set -euo pipefail
bundle=$(cd "$(dirname "$0")" && pwd)
variant=${1:?a or b}
out=${2:?new output directory}
mode=${3:?smoke or measured}
case "$variant" in a|b) ;; *) exit 2 ;; esac
case "$mode" in smoke) idle=3; warmup=3; duration=8 ;; measured) idle=5; warmup=20; duration=50 ;; *) exit 2 ;; esac
mkdir "$out"
"$bundle/vm-variant.sh" "$variant" > "$out/start.txt" 2>&1
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -d experiment -c "SELECT name, setting, unit FROM pg_settings WHERE name IN ('max_connections','superuser_reserved_connections','jit','max_parallel_workers_per_gather','max_parallel_workers','shared_buffers','work_mem','maintenance_work_mem','io_method','wal_level','fsync','autovacuum') ORDER BY name" > "$out/settings.txt"
"$bundle/driver.py" "$out/samples" --idle "$idle" --warmup "$warmup" --duration "$duration"
"$bundle/analyze.py" "$out/samples" > "$out/summary.txt"
systemctl stop postgresql@18-main
