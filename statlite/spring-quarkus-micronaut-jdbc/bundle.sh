#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 && -f "$1" ]] || { echo 'Usage: bundle.sh LINUX_AMD64_STATLITE NEW_OUTPUT_DIRECTORY' >&2; exit 2; }
statlite=$1 output=$2
experiment_dir=$(cd "$(dirname "$0")" && pwd)
model_dir="$experiment_dir/model-app"
spring="$model_dir/spring-app/target/market-replay-spring-0.1.0-SNAPSHOT.jar"
micronaut="$model_dir/micronaut-app/target/market-replay-micronaut-0.1.0-SNAPSHOT.jar"
quarkus="$model_dir/quarkus-app/target/quarkus-app"
for artifact in "$spring" "$micronaut" "$quarkus/quarkus-run.jar"; do
    [[ -f "$artifact" ]] || { echo "build artifact missing: $artifact" >&2; exit 1; }
done
file "$statlite" | grep -Eq 'ELF 64-bit.*x86-64' || { echo 'StatLite must be a Linux amd64 binary' >&2; exit 1; }
mkdir -- "$output"
mkdir "$output/spring" "$output/micronaut" "$output/fixture"
cp "$spring" "$output/spring/app.jar"
cp "$micronaut" "$output/micronaut/app.jar"
cp -R "$quarkus" "$output/quarkus"
cp "$statlite" "$output/statlite"
cp "$experiment_dir/runner.py" "$output/runner.py"
chmod +x "$output/statlite"
cp "$model_dir/fixture/server.py" "$output/fixture/"
cp -R "$model_dir/fixture/data" "$output/fixture/data"
echo "Bundle prepared: $output; deploy with tools/deploy.sh"
