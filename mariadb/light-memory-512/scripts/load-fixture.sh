#!/usr/bin/env bash
# Build the fixture under Theory B. This is preparation, not a measured phase.
# Theory A was OOM-killed while inserting on the 204 MiB guest. The measured
# run still restarts into stock, A, and B.
set -euo pipefail
bundle=$(cd "$(dirname "$0")" && pwd)
bytes=/var/tmp/mdb-light-fixture-bytes.txt
swap_kib=$(awk '/^SwapTotal:/{print $2}' /proc/meminfo)
[[ "$swap_kib" == 0 ]] || { echo "swap is enabled (${swap_kib} KiB)" >&2; exit 1; }
[[ ! -e "$bytes" ]] || { echo "fixture record already exists: $bytes" >&2; exit 1; }
"$bundle/vm-variant.sh" b
mariadb --protocol=socket <<'SQL'
CREATE DATABASE experiment CHARACTER SET latin1 COLLATE latin1_swedish_ci;
CREATE USER 'experiment'@'127.0.0.1' IDENTIFIED BY 'experiment';
GRANT SELECT ON experiment.* TO 'experiment'@'127.0.0.1';
CREATE TABLE experiment.items (
  id INT NOT NULL,
  bucket INT NOT NULL,
  payload VARCHAR(256) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  PRIMARY KEY (id),
  KEY items_bucket_idx (bucket)
) ENGINE=InnoDB;
SQL
# Small commits, then drop clean page cache. Cache dropping stays in fixture preparation.
for ((start=1; start<=520000; start+=2000)); do
  end=$((start + 1999))
  [[ "$end" -gt 520000 ]] && end=520000
  mariadb --protocol=socket -D experiment -e "INSERT INTO items (id, bucket, payload) SELECT seq, seq % 10000, REPEAT(MD5(seq), 8) FROM seq_${start}_to_${end}"
  sync
  echo 3 > /proc/sys/vm/drop_caches
  echo "loaded ${end}" >&2
done
mariadb --protocol=socket -D experiment -e "ANALYZE TABLE items"
size=$(mariadb --protocol=socket -N -e "SELECT data_length + index_length FROM information_schema.tables WHERE table_schema='experiment' AND table_name='items'")
printf '%s\n' "$size" | tee "$bytes"
[[ "$size" -gt 134217728 ]] || { echo "fixture is ${size} bytes, at or below 128 MiB" >&2; exit 1; }
mariadb --protocol=socket -N -e "SELECT COUNT(*) FROM experiment.items"
systemctl stop mariadb
