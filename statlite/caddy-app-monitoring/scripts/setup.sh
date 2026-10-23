#!/bin/bash
set -euo pipefail
# Run inside the disposable Ubuntu guest, from the experiment directory.
sudo apt-get update -qq
sudo apt-get install -y -qq curl ca-certificates xz-utils maven openjdk-25-jdk-headless
case "$(uname -m)" in
  x86_64) node_arch=x64; caddy_arch=amd64 ;;
  aarch64) node_arch=arm64; caddy_arch=arm64 ;;
  *) echo 'Unsupported architecture' >&2; exit 1 ;;
esac
mkdir -p run/downloads run/bin
cd run/downloads
curl -fLO "https://nodejs.org/dist/v24.21.0/node-v24.21.0-linux-${node_arch}.tar.xz"
curl -fLo node-SHASUMS256.txt https://nodejs.org/dist/v24.21.0/SHASUMS256.txt
grep " node-v24.21.0-linux-${node_arch}.tar.xz$" node-SHASUMS256.txt | sha256sum -c -
tar -xf "node-v24.21.0-linux-${node_arch}.tar.xz"
sudo cp -a "node-v24.21.0-linux-${node_arch}/." /usr/local/
curl -fLO "https://github.com/caddyserver/caddy/releases/download/v2.11.4/caddy_2.11.4_linux_${caddy_arch}.tar.gz"
curl -fLo caddy-checksums.txt https://github.com/caddyserver/caddy/releases/download/v2.11.4/caddy_2.11.4_checksums.txt
grep " caddy_2.11.4_linux_${caddy_arch}.tar.gz$" caddy-checksums.txt | sha512sum -c -
tar -xf "caddy_2.11.4_linux_${caddy_arch}.tar.gz" -C ../bin caddy
cd ../..
sudo setcap cap_net_bind_service=+ep run/bin/caddy
if ! grep -q 'spring.test express.test' /etc/hosts; then
  echo '127.0.0.1 spring.test express.test' | sudo tee -a /etc/hosts
fi
(cd express && npm ci --no-audit --no-fund)
if command -v mvn-lite >/dev/null; then
  (cd spring && mvn-lite -DskipTests package)
else
  (cd spring && mvn -q -DskipTests package)
fi
run/bin/caddy validate --config Caddyfile --adapter caddyfile
