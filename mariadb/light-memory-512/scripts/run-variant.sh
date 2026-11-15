#!/usr/bin/env bash
# One configuration. Keeps the output directory when the workload fails.
set -euo pipefail
bundle=$(cd "$(dirname "$0")" && pwd)
variant=${1:?stock, a, or b}
out=${2:?new output directory}
mode=${3:?smoke or measured}
case "$variant" in stock|a|b) ;; *) exit 2 ;; esac
case "$mode" in
  smoke) idle=3; warmup=3; duration=8 ;;
  measured) idle=5; warmup=20; duration=50 ;;
  *) exit 2 ;;
esac
swap_kib=$(awk '/^SwapTotal:/{print $2}' /proc/meminfo)
[[ "$swap_kib" == 0 ]] || { echo "swap is enabled (${swap_kib} KiB)" >&2; exit 1; }
mkdir "$out"
awk '/^oom_kill /{print "oom_kill_before="$2}' /proc/vmstat > "$out/oom.txt"
if ! "$bundle/vm-variant.sh" "$variant" > "$out/start.txt" 2>&1; then
  echo 'start_failed=1' >> "$out/oom.txt"
  exit 1
fi
server_cnf=/etc/mysql/mariadb.conf.d/50-server.cnf
if [[ -f "$server_cnf" ]]; then cp "$server_cnf" "$out/50-server.cnf"; else printf 'absent\n' > "$out/50-server.cnf"; fi
experiment_cnf=/etc/mysql/mariadb.conf.d/99-experiment.cnf
if [[ -f "$experiment_cnf" ]]; then cp "$experiment_cnf" "$out/99-experiment.cnf"; else printf 'absent\n' > "$out/99-experiment.cnf"; fi
mariadb --protocol=socket -e "SHOW GLOBAL VARIABLES WHERE Variable_name IN ('version','innodb_buffer_pool_size','innodb_buffer_pool_size_max','innodb_buffer_pool_size_auto_min','innodb_buffer_pool_dump_at_shutdown','innodb_buffer_pool_load_at_startup','innodb_buffer_pool_filename','key_buffer_size','aria_pagecache_buffer_size','max_connections','performance_schema','innodb_flush_log_at_trx_commit','sync_binlog','log_bin','innodb_flush_method','tmp_table_size','max_heap_table_size','aria_used_for_temp_tables','bind_address','default_time_zone')" > "$out/settings.txt"
bytes=/var/tmp/mdb-light-fixture-bytes.txt
if [[ -f "$bytes" && "$variant" == stock ]]; then
  pool=$(mariadb --protocol=socket -N -e "SELECT @@innodb_buffer_pool_size")
  size=$(cat "$bytes")
  if [[ "$size" -le "$pool" ]]; then
    echo "fixture ${size} bytes is not larger than stock pool ${pool} bytes" | tee "$out/fixture-warning.txt"
  fi
fi
set +e
"$bundle/driver.py" "$out/samples" --idle "$idle" --warmup "$warmup" --duration "$duration"
driver_status=$?
mariadb --protocol=socket -D experiment -e "EXPLAIN SELECT SUM(bucket) FROM (SELECT bucket FROM items WHERE id <= 12000 ORDER BY payload LIMIT 1 OFFSET 4000) s" > "$out/explain.txt" 2>&1
"$bundle/analyze.py" "$out/samples" > "$out/summary.txt" 2>&1
analyze_status=$?
set -e
awk '/^oom_kill /{print "oom_kill_after="$2}' /proc/vmstat >> "$out/oom.txt"
systemctl stop mariadb || true
[[ "$analyze_status" == 0 && "$driver_status" == 0 ]]
