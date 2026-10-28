#!/usr/bin/env bash
set -euo pipefail
# Explicitly reset only the dedicated experiment DB, with the app stopped.
# Run as root in the dedicated VM, outside startup and workload timing.
[[ ${1:-} == --confirm-experiment-reset ]] || { echo 'Require --confirm-experiment-reset' >&2; exit 2; }
here=$(cd -- "$(dirname -- "$0")" && pwd)
mariadb <<'SQL'
DROP DATABASE IF EXISTS market_replay;
CREATE DATABASE market_replay CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER IF NOT EXISTS 'market_replay'@'127.0.0.1' IDENTIFIED BY '';
GRANT SELECT, INSERT, UPDATE, DELETE ON market_replay.* TO 'market_replay'@'127.0.0.1';
SQL
mariadb market_replay < "$here/schema.sql"
