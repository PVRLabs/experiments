#!/bin/sh
set -eu

# Run as root inside Alpine. This installs the fixed experiment runtime and
# service definitions but deliberately does not start either application.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ "$#" -ne 2 ]; then
	 echo "usage: $0 STARS_JAR STATLITE_BIN" >&2
	 exit 1
fi

STARS_JAR=$1
STATLITE_BIN=$2

EXPECTED_JAVA_PACKAGE_VERSION='25.0.4_p7-r0'
EXPECTED_JAVA_PACKAGE="openjdk25-jre-headless-$EXPECTED_JAVA_PACKAGE_VERSION"
EXPECTED_JAVA_VERSION='openjdk version "25.0.4"'
EXPECTED_STATLITE_VERSION='statlite v0.3.0'
EXPECTED_STATLITE_SHA256='553d6539659759380aaec6a9b0a3e050ecbea59f989b5101b1bd0dd30ce403a4'

if [ "$(id -u)" -ne 0 ]; then
	 echo "provision.sh must run as root" >&2
	 exit 1
fi

if [ ! -f "$STARS_JAR" ]; then
	 echo "Spring Boot fat JAR not found: $STARS_JAR" >&2
	 exit 1
fi

if [ ! -f "$STATLITE_BIN" ]; then
	 echo "StatLite binary not found: $STATLITE_BIN" >&2
	 exit 1
fi

if awk 'NR > 1 && $1 != "" { found = 1 } END { exit found ? 0 : 1 }' /proc/swaps; then
	 echo "Existing swap is active; preserving the VPS swap configuration."
else
	 if [ ! -f /swapfile ]; then
		 dd if=/dev/zero of=/swapfile bs=1M count=512
	 fi
	 chmod 600 /swapfile
	 mkswap /swapfile >/dev/null
	 swapon /swapfile
	 if ! grep -q '^/swapfile ' /etc/fstab 2>/dev/null; then
		 printf '%s\n' '/swapfile none swap sw 0 0' >> /etc/fstab
	 fi
	 echo "Enabled the default 512 MiB /swapfile."
fi

HOSTNAME=$(hostname)
if [ -n "$HOSTNAME" ] && ! awk -v host="$HOSTNAME" '$1 !~ /^#/ { for (i = 2; i <= NF; i++) if ($i == host) found = 1 } END { exit found ? 0 : 1 }' /etc/hosts 2>/dev/null; then
	 printf '127.0.0.1\t%s\n' "$HOSTNAME" >> /etc/hosts
fi

apk add --no-cache ca-certificates curl file procps "openjdk25-jre-headless=$EXPECTED_JAVA_PACKAGE_VERSION"

INSTALLED_JAVA_PACKAGE=$(apk info -v openjdk25-jre-headless | head -n 1)
if [ "$INSTALLED_JAVA_PACKAGE" != "$EXPECTED_JAVA_PACKAGE" ]; then
	 echo "Unexpected JDK package: $INSTALLED_JAVA_PACKAGE (want $EXPECTED_JAVA_PACKAGE)" >&2
	 exit 1
fi

JAVA_VERSION_LINE=$(java -version 2>&1 | head -n 1)
if [ "$JAVA_VERSION_LINE" != "$EXPECTED_JAVA_VERSION" ]; then
	 echo "Unexpected Java runtime: $JAVA_VERSION_LINE (want $EXPECTED_JAVA_VERSION)" >&2
	 exit 1
fi

ARCH=$(uname -m)
FILE_INFO=$(file "$STATLITE_BIN")
printf 'statlite_binary: %s\n' "$FILE_INFO"
printf 'statlite_sha256: '
STATLITE_SHA256=$(sha256sum "$STATLITE_BIN" | awk '{ print $1 }')
printf '%s\n' "$STATLITE_SHA256"
if [ "$STATLITE_SHA256" != "$EXPECTED_STATLITE_SHA256" ]; then
	 echo "Unexpected StatLite SHA-256: $STATLITE_SHA256 (want $EXPECTED_STATLITE_SHA256)" >&2
	 exit 1
fi

STATLITE_VERSION=$("$STATLITE_BIN" --version 2>&1 | head -n 1)
if [ "$STATLITE_VERSION" != "$EXPECTED_STATLITE_VERSION" ]; then
	 echo "Unexpected StatLite version: $STATLITE_VERSION (want $EXPECTED_STATLITE_VERSION)" >&2
	 exit 1
fi

case "$ARCH" in
	 x86_64) expected_arch='x86-64' ;;
	 aarch64) expected_arch='ARM aarch64' ;;
	 *)
		 echo "Unsupported Alpine architecture for this experiment: $ARCH" >&2
		 exit 1
		 ;;
esac

case "$FILE_INFO" in
	 *ELF*"$expected_arch"*"statically linked"*) ;;
	 *)
		 echo "StatLite binary does not match $ARCH or is not static" >&2
		 exit 1
		 ;;
esac

printf '%s\n' 'java_runtime:'
java -version 2>&1

if ! grep -q '^stars:' /etc/group; then
	 addgroup -S stars
fi
if ! id stars >/dev/null 2>&1; then
	 adduser -S -D -H -s /sbin/nologin -G stars stars
fi
if ! grep -q '^statlite:' /etc/group; then
	 addgroup -S statlite
fi
if ! id statlite >/dev/null 2>&1; then
	 adduser -S -D -H -s /sbin/nologin -G statlite statlite
fi

install -d -m 0755 /opt/stars-app /etc/statlite /usr/local/sbin
install -d -o stars -g stars -m 0750 /opt/stars-app/data /var/log/stars
install -d -o statlite -g statlite -m 0750 /var/lib/statlite /var/log/statlite

install -o stars -g stars -m 0644 "$STARS_JAR" /opt/stars-app/stars.jar
install -o statlite -g statlite -m 0755 "$STATLITE_BIN" /usr/local/bin/statlite
install -o statlite -g statlite -m 0644 "$SCRIPT_DIR/statlite.yaml" /etc/statlite/statlite.yaml

install -m 0755 "$SCRIPT_DIR/stars.openrc" /etc/init.d/stars
install -m 0755 "$SCRIPT_DIR/statlite.openrc" /etc/init.d/statlite
install -m 0755 "$SCRIPT_DIR/snapshot.sh" /usr/local/sbin/alpine-vps-snapshot

rc-update add stars default
rc-update add statlite default

echo "Runtime installed. Services are enabled but stopped."
echo "Capture the initial configuration, then run: rc-service stars start"
echo "After Spring is healthy, run: rc-service statlite start"
