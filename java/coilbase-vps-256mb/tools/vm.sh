#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo 'Usage: vm.sh create NAME CONFIG | start|stop|status|inspect|delete NAME' >&2
    echo '       vm.sh exec NAME COMMAND [ARG...] | put|get NAME SOURCE DEST' >&2
    echo '       vm.sh tunnel NAME HOST_PORT GUEST_PORT' >&2
    exit 2
}
[[ $# -ge 2 ]] || usage
action=$1 vm=$2; shift 2
[[ "$vm" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || usage
case "$action" in
    create)
        [[ $# == 1 && -f "$1" ]] || usage
        existing=$(limactl list --quiet)
        if printf '%s\n' "$existing" | grep -Fxq -- "$vm"; then
            echo "instance already exists: $vm; use start to reuse it" >&2; exit 1
        fi
        exec limactl create --yes --name="$vm" "$1" ;;
    start|stop|delete)
        [[ $# == 0 ]] || usage
        exec limactl "$action" "$vm" ;;
    status)
        [[ $# == 0 ]] || usage
        exec limactl list "$vm" ;;
    inspect)
        [[ $# == 0 ]] || usage
        limactl list "$vm"
        state=$(limactl list --format='{{.Status}}' "$vm")
        [[ "$state" == Running ]] || exit 0
        # One read-only guest call captures common preparation diagnostics.
        "$0" exec "$vm" bash -s <<'GUEST'
set -eu
date -u +%Y-%m-%dT%H:%M:%SZ
uname -a
id
getent passwd "$(id -u)"
free -m
cat /proc/swaps
df -h /
ss -ltn
ps -eo pid,comm,rss,args --sort=-rss | head -25
for runtime in java python3; do
    if command -v "$runtime" >/dev/null; then "$runtime" --version 2>&1; fi
done
GUEST
        ;;
    exec)
        [[ $# -gt 0 ]] || usage
        exec limactl shell --workdir=/ "$vm" -- "$@" ;;
    put|get)
        [[ $# == 2 ]] || usage
        if [[ "$action" == put ]]; then
            exec limactl copy --backend=scp -r -- "$1" "$vm:$2"
        else
            [[ ! -e "$2" ]] || { echo "destination exists: $2" >&2; exit 1; }
            exec limactl copy --backend=scp -r -- "$vm:$1" "$2"
        fi ;;
    tunnel)
        [[ $# == 2 ]] || usage
        for port in "$@"; do
            if [[ ! "$port" =~ ^[1-9][0-9]{0,4}$ ]]; then usage; fi
            if (( port > 65535 )); then usage; fi
        done
        config=$(limactl list --format='{{.SSHConfigFile}}' "$vm")
        [[ -f "$config" ]] || { echo 'missing SSH configuration' >&2; exit 1; }
        echo "Forwarding http://127.0.0.1:$1 to $vm:127.0.0.1:$2; Ctrl-C stops the tunnel." >&2
        exec ssh -F "$config" -o ExitOnForwardFailure=yes -o ControlMaster=no \
            -o ControlPath=none -N -L "127.0.0.1:$1:127.0.0.1:$2" "lima-$vm" ;;
    *) usage ;;
esac
