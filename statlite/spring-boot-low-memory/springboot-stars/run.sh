#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
JAR="$ROOT/stars.jar"
if [[ ! -f "${JAR}" ]]; then
  JAR="$(ls -1 "$ROOT"/target/stars-*.jar 2>/dev/null | grep -v original | head -n 1 || true)"
fi
if [[ -z "${JAR}" ]]; then
  echo "No application JAR found. Run: mvn-lite -DskipTests package or copy a packaged JAR to $ROOT/stars.jar" >&2
  exit 1
fi
exec java -Xms16m -Xmx64m -Xss256k -XX:+UseSerialGC -jar "$JAR"
