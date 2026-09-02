#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
JAR="$(ls -1 "$ROOT"/target/stars-*.jar 2>/dev/null | grep -v original | head -n 1 || true)"
if [[ -z "${JAR}" ]]; then
  echo "No packaged jar found. Run: mvn-lite -DskipTests package" >&2
  exit 1
fi
exec java -Xmx64m -XX:+UseSerialGC -Xss256k -jar "$JAR"
