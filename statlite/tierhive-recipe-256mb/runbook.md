# TierHive 256 MB runbook

This is the manual sequence used for the TierHive experiment. Run commands
labelled “workstation” on the build machine and commands labelled “VPS” in a
root shell on Alpine. Keep real credentials out of copied commands and notes.

## 1. Preflight the VPS

```sh
id
cat /etc/alpine-release
uname -m
free -m
ps -o pid,comm
rc-status
rc-update show
```

The tested guest was Alpine 3.24.1, x86_64, with about 217 MiB of RAM. Confirm
that PID 1 is `init`, OpenRC has the `default` runlevel, and the shell is root.

## 2. Transfer and run the unpublished recipe

On the workstation, copy the checked-out recipe. Replace the SSH host and
port with the TierHive values:

```sh
scp -P <mapped-ssh-port> \
  /path/to/statlite/deploy/tierhive/run.sh \
  root@<tierhive-host>:/root/statlite-tierhive-run.sh
```

On the VPS:

```sh
chmod 0700 /root/statlite-tierhive-run.sh
spring_actuator_url='http://127.0.0.1:8080/actuator' \
spring_app_name='statlite-spring-actuator-demo' \
sh /root/statlite-tierhive-run.sh
```

The first run should install StatLite, enable OpenRC, pass
`http://127.0.0.1:9090/healthz`, and initially report the Spring target as
unreachable because the demo has not started.

Verify the service and generated configuration without printing any secret
environment file:

```sh
rc-service statlite status
rc-update show | grep statlite
ps -o user,pid,comm,args | grep '[s]tatlite'
cat /etc/statlite/statlite.yaml
ls -l /etc/statlite/statlite.yaml /var/lib/statlite/statlite.sqlite
```

## 3. Open the dashboard tunnel

From a second workstation terminal:

```sh
ssh -o ExitOnForwardFailure=yes -p <mapped-ssh-port> \
  -N -L 19090:127.0.0.1:9090 \
  root@<tierhive-host>
```

Open `http://127.0.0.1:19090`. If SSH reports `administratively prohibited`,
inspect the VPS configuration:

```sh
sshd -T | grep -Ei 'allowtcpforwarding|disableforwarding|permitopen|gatewayports'
```

For this VPS, `/etc/ssh/sshd_config` contained `AllowTcpForwarding no`. The
least-privilege local-tunnel fix was:

```sh
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.before-statlite-tunnel
sed -i \
  's/^[[:space:]]*AllowTcpForwarding[[:space:]].*/AllowTcpForwarding local/' \
  /etc/ssh/sshd_config
sshd -t
rc-service sshd reload
```

Keep the original SSH session open while validating the new tunnel.

## 4. Build the demo off-box

On the workstation, from the official demo directory:

```sh
cd /path/to/statlite/examples/spring-actuator-demo
mvn -DskipTests package
scp -P <mapped-ssh-port> \
  target/spring-actuator-demo-0.0.1-SNAPSHOT.jar \
  root@<tierhive-host>:/root/
```

On the VPS:

```sh
apk add --no-cache openjdk25-jre-headless
java -version
mkdir -p /opt/statlite-spring-actuator-demo
mv /root/spring-actuator-demo-0.0.1-SNAPSHOT.jar \
  /opt/statlite-spring-actuator-demo/app.jar
chmod 0644 /opt/statlite-spring-actuator-demo/app.jar
```

## 5. Run the demo under OpenRC

On the VPS, create a non-root demo account and log directory:

```sh
addgroup -S statlite-demo 2>/dev/null || true
adduser -S -D -H -s /sbin/nologin -G statlite-demo statlite-demo 2>/dev/null || true
install -d -o statlite-demo -g statlite-demo -m 0750 \
  /var/log/statlite-spring-actuator-demo
chown -R statlite-demo:statlite-demo /opt/statlite-spring-actuator-demo
```

Create the JVM wrapper and OpenRC service. The `EOF` terminators must start in
column one when using these heredocs:

```sh
cat >/usr/local/sbin/statlite-spring-actuator-demo <<'EOF'
#!/bin/sh
exec /usr/bin/java \
  -Xms16m \
  -Xmx80m \
  -Xss256k \
  -XX:+UseSerialGC \
  -XX:TieredStopAtLevel=1 \
  -XX:ReservedCodeCacheSize=32m \
  -XX:+UseCompactObjectHeaders \
  -jar /opt/statlite-spring-actuator-demo/app.jar \
  --server.port=8080
EOF
chmod 0755 /usr/local/sbin/statlite-spring-actuator-demo

cat >/etc/init.d/statlite-spring-actuator-demo <<'EOF'
#!/sbin/openrc-run

name="StatLite Spring Actuator demo"
command="/usr/local/sbin/statlite-spring-actuator-demo"
command_args=""
command_user="statlite-demo:statlite-demo"
directory="/opt/statlite-spring-actuator-demo"
command_background="yes"
pidfile="/run/${RC_SVCNAME}.pid"
output_log="/var/log/statlite-spring-actuator-demo/demo.log"
error_log="/var/log/statlite-spring-actuator-demo/demo.err"
retry="SIGTERM/20/SIGKILL/5"
required_files="/opt/statlite-spring-actuator-demo/app.jar"
required_dirs="/opt/statlite-spring-actuator-demo /var/log/statlite-spring-actuator-demo"

depend() {
  need net
}
EOF
chmod 0755 /etc/init.d/statlite-spring-actuator-demo
rc-update add statlite-spring-actuator-demo default
rc-service statlite-spring-actuator-demo start
```

The demo took roughly 40 seconds to become ready on the tested guest. Verify
it directly before waiting for the next StatLite poll:

```sh
curl -fsS http://127.0.0.1:8080/actuator/health
ps -o user,pid,rss,vsz,comm,args | grep -E '[j]ava|[s]tatlite'
```

## 6. Verify self-monitoring and workload

The final generated configuration should contain the Spring target and:

```yaml
- name: "statlite-self"
  type: "statlite-metrics"
  url: "http://127.0.0.1:9090/statlite/metrics"
```

For a recipe revision that predates this fixed target, add it to the existing
config without replacing the file:

```sh
cp /etc/statlite/statlite.yaml /etc/statlite/statlite.yaml.before-self
printf '%s\n' \
  '' \
  '  - name: "statlite-self"' \
  '    type: "statlite-metrics"' \
  '    url: "http://127.0.0.1:9090/statlite/metrics"' \
  >> /etc/statlite/statlite.yaml
chown root:statlite /etc/statlite/statlite.yaml
chmod 0640 /etc/statlite/statlite.yaml
rc-service statlite restart
```

Verify the local profile and then wait for the 30-second poll:

```sh
curl -fsS http://127.0.0.1:9090/statlite/metrics
```

The dashboard should show both targets as `UP`, with application charts on the
Spring target and host CPU, memory, disk, and StatLite runtime charts on
`statlite-self`.

Copy and run the canonical traffic generator from the workstation if desired:

```sh
scp -P <mapped-ssh-port> \
  /path/to/statlite/examples/spring-actuator-demo/generate-traffic.sh \
  root@<tierhive-host>:/root/
```

Then on the VPS:

```sh
mv /root/generate-traffic.sh /opt/statlite-spring-actuator-demo/
chmod 0755 /opt/statlite-spring-actuator-demo/generate-traffic.sh
chown statlite-demo:statlite-demo \
  /opt/statlite-spring-actuator-demo/generate-traffic.sh
su -s /bin/sh statlite-demo -c \
  /opt/statlite-spring-actuator-demo/generate-traffic.sh
```

## 7. Exercise lifecycle and capture resources

Restart the demo and StatLite separately, wait for each service to become
ready, and confirm the dashboard history remains available:

```sh
rc-service statlite-spring-actuator-demo restart
rc-service statlite restart
curl -fsS http://127.0.0.1:9090/healthz
rc-service statlite-spring-actuator-demo status
rc-service statlite status
```

Capture the resource constraint honestly:

```sh
free -h
df -h /
df -ih /
ps -o user,pid,rss,vsz,comm,args | grep -E '[j]ava|[s]tatlite'
sha256sum /var/lib/statlite/statlite.sqlite
```

On the tested VPS, available memory reached about 45.5 MiB with no swap while
the Java process used about 121 MiB RSS and StatLite about 14 MiB RSS. Disk
space remained plentiful. Record any SSH, memory, startup, or networking
friction separately from the recipe's functional result.
