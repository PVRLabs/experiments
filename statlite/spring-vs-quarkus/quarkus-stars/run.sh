#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
JAR="$ROOT/target/quarkus-app/quarkus-run.jar"
if [[ ! -f "$JAR" ]]; then
  echo "No packaged application found. Run: mvn-lite -DskipTests package" >&2
  exit 1
fi
exec java -Xmx64m -XX:+UseSerialGC -Xss256k -jar "$JAR"
