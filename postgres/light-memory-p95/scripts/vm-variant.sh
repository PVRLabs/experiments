#!/usr/bin/env bash
set -euo pipefail
variant=${1:?default, a or b}
conf=/etc/postgresql/18/main/conf.d/experiment.conf
case "$variant" in
 default) printf '# PostgreSQL defaults\n' > "$conf" ;;
 a|b)
 cat > "$conf" <<'CONF'
max_connections = 5
superuser_reserved_connections = 1
jit = off
max_parallel_workers_per_gather = 0
max_parallel_workers = 0
CONF
 if [[ $variant == a ]]; then
 cat >> "$conf" <<'CONF'
shared_buffers = '16MB'
work_mem = '1MB'
maintenance_work_mem = '16MB'
CONF
 else
 cat >> "$conf" <<'CONF'
shared_buffers = '32MB'
io_method = 'sync'
CONF
 fi ;;
 *) exit 2 ;;
esac
systemctl restart postgresql@18-main
sudo -u postgres pg_isready

# Check the captured baseline settings before collecting any measurements.
if [[ $variant == default ]]; then
  mismatches=$(sudo -u postgres psql -X -v ON_ERROR_STOP=1 -At -d postgres <<'SQL'
WITH expected(name, setting) AS (VALUES
  ('autovacuum','on'), ('fsync','on'), ('io_method','worker'), ('jit','on'),
  ('maintenance_work_mem','65536'), ('max_connections','100'),
  ('max_parallel_workers','8'), ('max_parallel_workers_per_gather','2'),
  ('shared_buffers','16384'), ('superuser_reserved_connections','3'),
  ('wal_level','replica'), ('work_mem','4096')
)
SELECT e.name || ': expected ' || e.setting || ', got ' || COALESCE(p.setting, '<missing>')
FROM expected e LEFT JOIN pg_settings p USING (name)
WHERE p.setting IS DISTINCT FROM e.setting ORDER BY e.name;
SQL
  )
  if [[ -n $mismatches ]]; then
    printf 'Baseline differs from recorded PostgreSQL 18 settings:\n%s\nUse a fresh, unmodified PostgreSQL 18 cluster.\n' "$mismatches" >&2
    exit 1
  fi
fi
