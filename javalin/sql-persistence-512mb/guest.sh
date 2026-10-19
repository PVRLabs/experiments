#!/usr/bin/env bash
set -euo pipefail
action=$1 variant=$2 run=$3 release=$4
case "$variant" in javalin|spring|javalin-jdbi3|javalin-mybatis|javalin-jooq) ;; *) exit 2;; esac
case "$action" in
  init)
    mkdir "$run"
    echo 5 > "$run/cadence"
    nohup bash "$release/sampler.sh" "$run" > "$run/sampler.log" 2>&1 < /dev/null & echo $! > "$run/sampler.pid"
    ;;
  monitor)
    cat > "$run/statlite.yaml" <<EOF
server:
  listen: "127.0.0.1:9090"
storage:
  sqlite_path: "$run/statlite.sqlite"
polling:
  interval: "30s"
  timeout: "5s"
targets:
  - name: statlite-self
    type: statlite-metrics
    url: http://127.0.0.1:9090/statlite/metrics
  - name: $variant
EOF
    if [[ $variant != spring ]]; then
      cat >> "$run/statlite.yaml" <<EOF
    type: statlite-metrics
    url: http://127.0.0.1:8080/statlite/metrics
EOF
    else
      cat >> "$run/statlite.yaml" <<EOF
    type: spring
    url: http://127.0.0.1:8080/actuator
    metrics_source: actuator
    collect_host_metrics: false
EOF
    fi
    nohup "$release/statlite" -config "$run/statlite.yaml" > "$run/monitor.log" 2>&1 < /dev/null & echo $! > "$run/monitor.pid"
    ;;
  java)
    jar="$release/javalin.jar"
    [[ $variant != javalin-jdbi3 ]] || jar="$release/javalin-jdbi3.jar"
    [[ $variant != javalin-mybatis ]] || jar="$release/javalin-mybatis.jar"
    [[ $variant != javalin-jooq ]] || jar="$release/javalin-jooq.jar"
    [[ $variant != spring ]] || jar="$release/spring-extracted/spring.jar"
    test -f "$jar"
    echo 1 > "$run/cadence"
    kill -USR1 "$(cat "$run/sampler.pid")" 2>/dev/null || true
    date -u +%Y-%m-%dT%H:%M:%S.%NZ > "$run/java-launch-utc.txt"
    printf '%s\n' "java -Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k -Drun.dir=$run -jar $jar" >> "$run/java-commands.txt"
    nohup java -Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k "-Drun.dir=$run" -jar "$jar" > "$run/java.log" 2>&1 < /dev/null & echo $! > "$run/java.pid"
    ;;
  check)
    short=${variant#javalin-}
    main=lab.JooqRepositoryCheck
    [[ $short != jdbi3 ]] || main=RepositoryCheck
    [[ $short != mybatis ]] || main=lab.MyBatisRepositoryCheck
    java -Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k -cp "$release/$variant.jar:$release/$short-checks.jar" "$main" "$run/repository-db" > "$run/repository-check.txt" 2>&1
    java -Xms16m -Xmx80m -XX:+UseSerialGC -Xss512k -cp "$release/$variant.jar:$release/$short-checks.jar" lab.FixtureRecoveryCheck "$run/fixture-db" > "$run/fixture-check.txt" 2>&1
    ;;
  diagnostics)
    ps -eo pid,comm,rss,args > "$run/processes-diagnostic.txt"
    sudo dmesg > "$run/kernel-diagnostic.txt"
    cat /proc/meminfo /proc/swaps > "$run/memory-diagnostic.txt"
    ;;
  slow) echo 5 > "$run/cadence" ;;
  cutoff) touch "$run/stop-sampler" ;;
  stop-java|stop)
    for service in java; do
      [[ ! -f "$run/$service.pid" ]] || kill -TERM "$(cat "$run/$service.pid")" 2>/dev/null || true
    done
    for i in {1..30}; do
      pid=$(cat "$run/java.pid" 2>/dev/null || echo 0)
      [[ ! -r /proc/$pid/status ]] && break
      [[ $(awk '/^State:/{print $2}' /proc/$pid/status) == Z ]] && break
      sleep 1
    done
    pid=$(cat "$run/java.pid" 2>/dev/null || echo 0)
    if [[ -r /proc/$pid/status ]] && [[ $(awk '/^State:/{print $2}' /proc/$pid/status) != Z ]]; then
      echo "Java shutdown timed out after 30 seconds (PID $pid); refusing to continue" >&2
      exit 1
    fi
    if [[ $action == stop ]]; then
      [[ ! -f "$run/monitor.pid" ]] || kill -TERM "$(cat "$run/monitor.pid")" 2>/dev/null || true
      touch "$run/stop-sampler"
      sleep 6
      # Preserve OOM evidence without dumping the complete kernel on success.
      sudo dmesg | awk '/[Oo]ut of memory|oom-kill|Killed process/' > "$run/oom-events.txt"
      if [[ -s "$run/oom-events.txt" ]]; then
        ps -eo pid,comm,rss,args > "$run/processes-diagnostic.txt"
        sudo dmesg > "$run/kernel-diagnostic.txt"
        cat /proc/meminfo /proc/swaps > "$run/memory-diagnostic.txt"
      fi
    fi
    ;;
  *) exit 2 ;;
esac
