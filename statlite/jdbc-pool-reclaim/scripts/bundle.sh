#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 && ( -f "$1" || "$1" == - ) ]] || { echo 'Usage: bundle.sh LINUX_AMD64_STATLITE_OR_DASH NEW_OUTPUT_DIRECTORY' >&2; exit 2; }
experiment=$(cd "$(dirname "$0")/.." && pwd)
artifact="$experiment/app/target/jdbc-pool-reclaim-0.1.0.jar"
[[ -f "$artifact" ]] || { echo 'Run scripts/build.sh first' >&2; exit 1; }
if [[ "$1" != - ]]; then
    file "$1" | grep -Eq 'ELF 64-bit.*x86-64' || { echo 'StatLite must be Linux amd64 (or use - to omit it)' >&2; exit 1; }
fi
mkdir -- "$2"
cp "$artifact" "$2/app.jar"
if [[ "$1" != - ]]; then
    cp "$1" "$2/statlite"
    chmod +x "$2/statlite"
fi
mkdir "$2/scripts" "$2/inputs"
cp "$experiment/scripts/runner.py" "$experiment/scripts/common.py" "$experiment/scripts/summarize.py" \
    "$experiment/scripts/setup-postgres.py" "$experiment/scripts/ack-preflight.py" "$2/scripts/"
cp "$experiment/app/pom.xml" "$2/inputs/"
cp -R "$experiment/app/src" "$2/inputs/"
git -C "$experiment" rev-parse HEAD > "$2/inputs/repository-revision.txt"
echo "Prepared $2. No application started."
