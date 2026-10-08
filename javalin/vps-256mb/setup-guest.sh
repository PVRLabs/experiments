#!/bin/sh
set -eu
test "$(cat /etc/alpine-release)" = 3.24.2
if ! grep -q /swapfile /proc/swaps; then
  if [ ! -e /swapfile ]; then
    dd if=/dev/zero of=/swapfile bs=1M count=512
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile
fi
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo 'vm.swappiness=60' > /etc/sysctl.d/90-experiment.conf
sysctl -w vm.swappiness=60
apk add bash curl openssh tar coreutils procps iproute2 util-linux openjdk25-jre-headless=25.0.4_p7-r0
mkdir -p /opt/vps256 /opt/vps256/apks
apk fetch --recursive --output /opt/vps256/apks openjdk25-jre-headless=25.0.4_p7-r0
apk info -vv > /opt/vps256/apk-versions.txt
sha256sum /opt/vps256/apks/* > /opt/vps256/apk-sha256.txt
chown -R "${SUDO_USER:?}" /opt/vps256
java -version
cat /proc/meminfo /proc/swaps
