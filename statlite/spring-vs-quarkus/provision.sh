#!/usr/bin/env bash
set -euo pipefail

[[ "$(id -u)" == 0 ]] || { echo 'run as root' >&2; exit 1; }
JRE_ARCHIVE=/home/ubuntu/bellsoft-jre25.0.4+9-linux-amd64.tar.gz
JRE_DIR=/opt/jdk-25.0.4+9

if ! swapon --show --noheadings | awk '{found=1} END {exit found ? 0 : 1}'; then
  dd if=/dev/zero of=/swapfile bs=1M count=256 status=progress
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl file procps sqlite3

install -d -m 0755 /opt
if [[ ! -x "$JRE_DIR/bin/java" ]]; then
  tar -xzf "$JRE_ARCHIVE" -C /opt
  mv /opt/jre-25.0.4 "$JRE_DIR"
fi
ln -sfn "$JRE_DIR/bin/java" /usr/local/bin/java

for account in spring-stars quarkus-stars statlite; do
  id "$account" >/dev/null 2>&1 || useradd --system --home-dir "/opt/$account" --shell /usr/sbin/nologin "$account"
done

install -d -o spring-stars -g spring-stars -m 0750 /opt/spring-stars /opt/spring-stars/data /var/log/spring-stars
install -d -o quarkus-stars -g quarkus-stars -m 0750 /opt/quarkus-stars /opt/quarkus-stars/data-quarkus /var/log/quarkus-stars
install -d -o statlite -g statlite -m 0750 /var/lib/statlite /var/log/statlite
install -d -m 0755 /etc/statlite

install -o spring-stars -g spring-stars -m 0644 /home/ubuntu/stars-0.0.1-SNAPSHOT.jar /opt/spring-stars/stars.jar
cp -a /home/ubuntu/quarkus-app/. /opt/quarkus-stars/
chown -R quarkus-stars:quarkus-stars /opt/quarkus-stars
install -o statlite -g statlite -m 0755 /home/ubuntu/statlite /usr/local/bin/statlite
install -o statlite -g statlite -m 0644 /home/ubuntu/statlite.yaml /etc/statlite/statlite.yaml
install -m 0644 /home/ubuntu/services/*.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable spring-stars.service quarkus-stars.service statlite.service
echo 'Provisioned runtime; services remain stopped.'
