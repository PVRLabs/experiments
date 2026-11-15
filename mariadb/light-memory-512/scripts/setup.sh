#!/usr/bin/env bash
# Dedicated mdb-light guest only. Disables unattended upgrades on this VM.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y mariadb-server python3-pymysql
systemctl disable --now apt-daily.timer apt-daily-upgrade.timer || true
systemctl disable --now unattended-upgrades.service || true
# The package starts MariaDB. Keep it stopped so a reboot does not launch stock
# beside cloud-init on this 256 MiB guest. Variant scripts start it explicitly.
systemctl disable --now mariadb
mariadb --version
awk '/^MemTotal:|^SwapTotal:/{print}' /proc/meminfo
