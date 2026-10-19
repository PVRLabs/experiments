#!/bin/sh
set -eu
test "$(cat /etc/alpine-release)" = 3.24.2
swapoff -a
cp -n /etc/fstab /etc/fstab.before-512mb || true
awk '$3 != "swap"' /etc/fstab > /etc/fstab.512mb
cat /etc/fstab.512mb > /etc/fstab
test "$(awk 'END {print NR}' /proc/swaps)" = 1
mkdir -p /opt/sql512
chown "${SUDO_USER:?}" /opt/sql512
java -version
cat /proc/meminfo /proc/swaps
rc-status -a
