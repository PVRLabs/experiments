#!/bin/sh

set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <h2-jar> <database-path-without-extension>" >&2
    exit 2
fi

h2_jar=$1
database_path=$2
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ ! -f "$h2_jar" ]; then
    echo "H2 JAR not found: $h2_jar" >&2
    exit 2
fi

case "$database_path" in
    ""|/|.|..)
        echo "refusing unsafe database path: $database_path" >&2
        exit 2
        ;;
esac

mkdir -p "$(dirname -- "$database_path")"

java -cp "$h2_jar" org.h2.tools.RunScript \
    -url "jdbc:h2:file:$database_path" \
    -user sa \
    -password '' \
    -script "$script_dir/seed-database.sql"
