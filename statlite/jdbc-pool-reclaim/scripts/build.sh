#!/usr/bin/env bash
set -euo pipefail
experiment=$(cd "$(dirname "$0")/.." && pwd)
if command -v mvn-lite >/dev/null; then
    mvn-lite -f "$experiment/app/pom.xml" package
else
    mvn -f "$experiment/app/pom.xml" package
fi
