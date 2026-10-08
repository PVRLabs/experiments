#!/usr/bin/env bash
set -euo pipefail
run=$1
sleeper=''
trap '[[ -z "$sleeper" ]] || kill "$sleeper" 2>/dev/null || true' USR1
echo 'epoch,uptime,mem_total_kib,mem_available_kib,swap_used_kib,pswpin_pages,pswpout_pages,cpu_total_ticks,cpu_idle_ticks,cpu_iowait_ticks,cpu_steal_ticks,java_pid,java_rss_kib,java_swap_kib,java_threads,java_cpu_ticks,monitor_pid,monitor_rss_kib,monitor_swap_kib,monitor_cpu_ticks' > "$run/os.csv"
proc() {
  local pid=0 rss=0 swap=0 threads=0 ticks=0
  if [[ -f "$run/$1.pid" ]]; then read -r pid < "$run/$1.pid"; fi
  if [[ -r /proc/$pid/status ]]; then
    read -r rss swap threads < <(awk '/^VmRSS:/{r=$2}/^VmSwap:/{s=$2}/^Threads:/{t=$2}END{print r+0,s+0,t+0}' "/proc/$pid/status")
    ticks=$(awk '{print $14+$15}' "/proc/$pid/stat")
  fi
  if [[ $1 == java ]]; then echo "$pid,$rss,$swap,$threads,$ticks"; else echo "$pid,$rss,$swap,$ticks"; fi
}
while [[ ! -e "$run/stop-sampler" ]]; do
  read -r up _ < /proc/uptime
  mem=$(awk '/^MemTotal:/{t=$2}/^MemAvailable:/{a=$2}/^SwapTotal:/{s=$2}/^SwapFree:/{f=$2}END{printf "%d,%d,%d",t,a,s-f}' /proc/meminfo)
  paging=$(awk '$1=="pswpin"{i=$2}$1=="pswpout"{o=$2}END{printf "%d,%d",i,o}' /proc/vmstat)
  printf "%s " "$(date +%s.%N)" >> "$run/proc-stat-cpu.txt"
  sed -n '1p' /proc/stat >> "$run/proc-stat-cpu.txt"
  cpu=$(awk '/^cpu /{for(i=2;i<=9;i++)t+=$i;printf "%d,%d,%d,%d",t,$5,$6,$9;exit}' /proc/stat)
  echo "$(date +%s.%N),$up,$mem,$paging,$cpu,$(proc java),$(proc monitor)" >> "$run/os.csv"
  cadence=5; [[ ! -e "$run/cadence" ]] || read -r cadence < "$run/cadence"
  sleep "$cadence" & sleeper=$!
  wait "$sleeper" || true
  sleeper=''
done
