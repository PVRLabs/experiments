#!/usr/bin/env bash
# Group VM startup, verified deployment, and environment capture in one command.
set -euo pipefail
[[ $# == 4 && -d "$2" ]] || {
    echo 'Usage: prepare.sh VM BUNDLE NEW_ABSOLUTE_GUEST_DIRECTORY NEW_CAPTURE_DIRECTORY' >&2
    exit 2
}
vm=$1 bundle=$2 destination=$3 capture=$4
[[ "$vm" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || exit 2
[[ "$destination" =~ ^/[a-zA-Z0-9_./-]+$ && "$destination" != / && "$destination" != *'/../'* && "$destination" != */.. ]] || {
    echo 'use an absolute guest path without spaces or .. components' >&2; exit 2;
}
[[ ! -e "$capture" && ! -L "$capture" ]] || {
    echo "capture destination exists: $capture" >&2; exit 1;
}
tools_dir=$(cd "$(dirname "$0")" && pwd)
state=$(limactl list --format='{{.Status}}' "$vm")
case "$state" in
    Running) ;;
    Stopped) "$tools_dir/vm.sh" start "$vm" ;;
    *) echo "VM $vm is unavailable (status: $state); refusing preparation" >&2; exit 1 ;;
esac
# Check the new destination before transfer; deploy.sh also refuses overwrite.
"$tools_dir/vm.sh" exec "$vm" bash -s -- "$destination" <<'GUEST'
set -eu
if [[ -e "$1" || -L "$1" ]]; then
    echo "guest release exists: $1" >&2
    exit 1
fi
mkdir -p -- "$(dirname "$1")"
GUEST
"$tools_dir/deploy.sh" "$vm" "$bundle" "$destination"
mkdir -p -- "$(dirname "$capture")"
"$tools_dir/capture-env.sh" "$vm" "$capture" "$destination"
echo "Preparation complete: artifacts=$destination capture=$capture"
