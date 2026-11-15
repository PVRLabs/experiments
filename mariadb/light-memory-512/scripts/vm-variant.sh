#!/usr/bin/env bash
# Apply stock, Theory A, or Theory B and wait until MariaDB accepts a local client.
set -euo pipefail
variant=${1:?stock, a, or b}
conf=/etc/mysql/mariadb.conf.d/99-experiment.cnf
case "$variant" in
  stock)
    rm -f "$conf"
    ;;
  a|b)
    pool=64M
    [[ "$variant" == b ]] && pool=32M
    cat > "$conf" <<CONF
[mariadbd]
bind-address=127.0.0.1
innodb_buffer_pool_size=${pool}
default_time_zone='+00:00'
key_buffer_size=8M
aria_pagecache_buffer_size=16M
max_connections=10
CONF
    ;;
  *)
    exit 2
    ;;
esac
# Package defaults dump the pool at shutdown and load it at startup. Stop, delete
# that file, then start, so this variant does not inherit the previous pool contents.
systemctl stop mariadb || true
pool_dump=/var/lib/mysql/ib_buffer_pool
if [[ -f "$pool_dump" ]]; then
  rm -f "$pool_dump"
  echo "removed $pool_dump before start"
else
  echo "no $pool_dump before start"
fi
systemctl start mariadb
ready=0
for _ in $(seq 1 30); do
  if mariadb-admin --protocol=socket ping --silent; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" == 1 ]] || exit 1
mariadb --protocol=socket -N -e "SELECT @@version, @@innodb_buffer_pool_size, @@key_buffer_size, @@aria_pagecache_buffer_size, @@max_connections"
case "$variant" in
  a)
    expect_pool=67108864
    expect_key=8388608
    expect_aria=16777216
    expect_connections=10
    ;;
  b)
    expect_pool=33554432
    expect_key=8388608
    expect_aria=16777216
    expect_connections=10
    ;;
  stock)
    [[ ! -e "$conf" ]]
    exit 0
    ;;
esac
read -r version pool key aria connections < <(mariadb --protocol=socket -N -e "SELECT @@version, @@innodb_buffer_pool_size, @@key_buffer_size, @@aria_pagecache_buffer_size, @@max_connections")
[[ "$pool" == "$expect_pool" && "$key" == "$expect_key" && "$aria" == "$expect_aria" && "$connections" == "$expect_connections" ]] || {
  echo "effective settings differ: version=$version pool=$pool key=$key aria=$aria max_connections=$connections" >&2
  exit 1
}
