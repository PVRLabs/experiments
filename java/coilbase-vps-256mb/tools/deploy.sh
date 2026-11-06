#!/usr/bin/env bash
set -euo pipefail
[[ $# == 3 && -d "$2" ]] || { echo 'Usage: deploy.sh VM SOURCE_DIRECTORY NEW_ABSOLUTE_GUEST_DIRECTORY' >&2; exit 2; }
vm=$1 source_dir=$2 destination=$3
[[ "$destination" =~ ^/[a-zA-Z0-9_./-]+$ && "$destination" != / && "$destination" != *'/../'* && "$destination" != */.. ]] || {
    echo 'use an absolute guest path without spaces or .. components' >&2; exit 2;
}
tools_dir=$(cd "$(dirname "$0")" && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
# Snapshot first, then hash exactly what will be deployed. Reject symlinks and
# special files so the bundle cannot depend on paths outside its directory.
python3 - "$source_dir" "$stage/payload" <<'PY'
import pathlib, shutil, sys
source, target = map(pathlib.Path, sys.argv[1:])
for path in [source, *source.rglob('*')]:
    if path.is_symlink() or not (path.is_file() or path.is_dir()):
        sys.exit(f'unsupported artifact: {path}')
    if '\n' in str(path) or '\r' in str(path) or '\\' in str(path):
        sys.exit(f'unsupported filename: {path!s}')
for name in ('SHA256SUMS', '.deploy-complete'):
    if (source / name).exists():
        sys.exit(f'reserved artifact name: {name}')
shutil.copytree(source, target)
PY
(
    cd "$stage/payload"
    find . -type f -print0 | while IFS= read -r -d '' file; do shasum -a 256 "$file"; done > "$stage/SHA256SUMS"
)
cp "$stage/SHA256SUMS" "$stage/payload/SHA256SUMS"
COPYFILE_DISABLE=1 tar -czf "$stage/payload.tar.gz" -C "$stage/payload" .
archive_sha=$(shasum -a 256 "$stage/payload.tar.gz" | awk '{print $1}')
remote_stage=$("$tools_dir/vm.sh" exec "$vm" mktemp -d /tmp/experiment-deploy.XXXXXXXX)
echo "Guest staging directory (retained on failure): $remote_stage" >&2
"$tools_dir/vm.sh" put "$vm" "$stage/payload.tar.gz" "$remote_stage/payload.tar.gz"
"$tools_dir/vm.sh" exec "$vm" bash -s -- "$remote_stage" "$destination" "$archive_sha" <<'GUEST'
set -euo pipefail
stage=$1 destination=$2 expected=$3
printf '%s  %s\n' "$expected" "$stage/payload.tar.gz" | sha256sum -c -
# mkdir without -p intentionally refuses existing releases.
mkdir -- "$destination"
tar -xzf "$stage/payload.tar.gz" -C "$destination"
cd "$destination"
sha256sum -c SHA256SUMS
date -u +%Y-%m-%dT%H:%M:%SZ > .deploy-complete
rm -f -- "$stage/payload.tar.gz"
rmdir -- "$stage"
GUEST
echo "Verified deployment: $destination"
