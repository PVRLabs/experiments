#!/usr/bin/env bash
set -euo pipefail
[[ $# -ge 2 && $# -le 3 ]] || { echo 'Usage: capture-env.sh VM NEW_OUTPUT_DIRECTORY [GUEST_ARTIFACT_DIRECTORY]' >&2; exit 2; }
vm=$1 output=$2
tools_dir=$(cd "$(dirname "$0")" && pwd)
mkdir -- "$output"
# Partial captures are deliberately retained if a required command fails.
{
    date -u +%Y-%m-%dT%H:%M:%SZ
    uname -a
    sw_vers
    sysctl -n machdep.cpu.brand_string hw.memsize hw.logicalcpu
    limactl --version
} > "$output/host.txt"
limactl list --format yaml "$vm" > "$output/vm.yaml"
limactl list --all-fields --format json "$vm" > "$output/vm.json"
python3 - "$output" "$vm" <<'PY'
import hashlib, json, pathlib, sys
output = pathlib.Path(sys.argv[1])
records = [json.loads(line) for line in (output / 'vm.json').read_text().splitlines() if line.strip()]
if len(records) != 1 or records[0].get('name') != sys.argv[2]:
    sys.exit('expected exactly one matching Lima instance')
instance = records[0]
if not instance.get('config') or instance.get('errors'):
    sys.exit('Lima did not report a usable merged configuration')
instance_dir = pathlib.Path(instance['dir'])
global_dir = pathlib.Path(instance['LimaHome']) / '_config'
(output / 'lima-global').mkdir()
manifest = []
def capture(source, target, required=False):
    entry = {'source': str(source), 'captured_as': str(target.relative_to(output))}
    if required or source.exists() or source.is_symlink():
        data = source.read_bytes()  # An unreadable/broken configuration is an error.
        target.write_bytes(data)
        entry.update(present=True, sha256=hashlib.sha256(data).hexdigest())
    else:
        entry['present'] = False
    manifest.append(entry)
capture(instance_dir / 'lima.yaml', output / 'lima.yaml', required=True)
for name in ('default.yaml', 'override.yaml', 'base.yaml', 'networks.yaml'):
    capture(global_dir / name, output / 'lima-global' / name)
(output / 'config-files.json').write_text(json.dumps(manifest, indent=2) + '\n')
PY
"$tools_dir/vm.sh" exec "$vm" bash -s > "$output/guest.txt" <<'GUEST'
set -eu
date -u +%Y-%m-%dT%H:%M:%SZ
uname -a
cat /etc/os-release
lscpu
free -b
cat /proc/swaps
df -hT
findmnt
lsblk -b
ip address
ip route
ps -eo pid,comm,rss,args --sort=-rss
for runtime in java python3; do
    if command -v "$runtime" >/dev/null; then "$runtime" --version 2>&1; fi
done
if command -v timedatectl >/dev/null; then timedatectl || true; fi
GUEST
if [[ $# == 3 ]]; then
    "$tools_dir/vm.sh" exec "$vm" bash -s -- "$3" > "$output/artifacts.txt" <<'GUEST'
set -eu
cd "$1"
test -f .deploy-complete
cat .deploy-complete SHA256SUMS
sha256sum -c SHA256SUMS
GUEST
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$output/complete.txt"
