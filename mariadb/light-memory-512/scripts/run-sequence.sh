#!/usr/bin/env bash
# Stock, Theory A, then Theory B. An OOM kill stops the sequence for a reboot.
# Resume in the same directory after that reboot: run-sequence.sh OUT MODE a
set -euo pipefail
bundle=$(cd "$(dirname "$0")" && pwd)
out=${1:?output directory}
mode=${2:?smoke or measured}
start=${3:-stock}
case "$mode" in smoke|measured) ;; *) exit 2 ;; esac
case "$start" in stock|a|b) ;; *) exit 2 ;; esac
if [[ "$start" == stock ]]; then
  mkdir "$out"
else
  [[ -d "$out" ]] || { echo "resume directory missing: $out" >&2; exit 1; }
  echo "resume start=$start mode=$mode" | tee -a "$out/sequence.txt"
fi
oom() { awk '/^oom_kill /{print $2}' /proc/vmstat; }
variants=(stock a b)
begin=0
for index in "${!variants[@]}"; do
  [[ "${variants[$index]}" == "$start" ]] && begin=$index
done
failed=0
for ((index=begin; index<${#variants[@]}; index++)); do
  variant=${variants[$index]}
  if [[ -e "$out/$variant" ]]; then
    echo "variant directory already exists: $out/$variant" >&2
    exit 1
  fi
  before=$(oom)
  set +e
  "$bundle/run-variant.sh" "$variant" "$out/$variant" "$mode"
  status=$?
  set -e
  after=$(oom)
  echo "$variant exit=$status oom_before=$before oom_after=$after" | tee -a "$out/sequence.txt"
  if [[ "$after" != "$before" ]]; then
    echo "oom during $variant; reboot, then resume this directory at the next variant" | tee -a "$out/stop.txt"
    exit 1
  fi
  if [[ "$variant" != stock && "$status" != 0 ]]; then
    failed=1
  fi
done
exit "$failed"
