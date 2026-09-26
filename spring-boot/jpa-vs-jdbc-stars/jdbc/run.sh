#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
JAR="$ROOT/extracted/stars-jdbc.jar"
if [[ ! -f "$JAR" ]]; then
  JAR="$ROOT/stars-jdbc.jar"
fi
if [[ ! -f "$JAR" ]]; then
  JAR="$ROOT/target/stars-jdbc-0.0.1-SNAPSHOT.jar"
fi
if [[ ! -f "$JAR" ]]; then
  echo "Copy stars-jdbc.jar here or build with Maven: mvn -DskipTests package (or mvn-lite)" >&2
  exit 1
fi
mkdir -p "$ROOT/data"
cd "$ROOT"
exec java -Xms16m -Xmx80m -Xss256k -XX:+UseSerialGC \
  -XX:TieredStopAtLevel=1 -XX:ReservedCodeCacheSize=32m \
  -XX:+UseCompactObjectHeaders -jar "$JAR" "$@"
