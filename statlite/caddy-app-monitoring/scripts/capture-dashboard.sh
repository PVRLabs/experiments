#!/bin/bash
# Run on the browser host with the dashboard forwarded to localhost:19090.
set -euo pipefail
target=${1:?target name required}
output=${2:?output prefix required}
case "$target" in express-via-caddy|spring-via-caddy|spring-direct) ;; *) exit 2 ;; esac
mkdir -p "$(dirname "$output")"
playwright-cli -s=caddy-article open "http://127.0.0.1:19090/?target=$target&range=1h"
playwright-cli -s=caddy-article resize 1440 1100
# Wait for real chart data and animation completion before the screenshot.
playwright-cli -s=caddy-article run-code 'async page => { await page.waitForFunction(() => typeof state !== "undefined" && state.renderedSeriesQuery); await page.evaluate(() => { for (const chart of Object.values(Chart.instances)) { chart.stop(); chart.update("none"); } }); }'
playwright-cli -s=caddy-article screenshot --filename="$output.png"
playwright-cli -s=caddy-article --raw eval 'async () => JSON.stringify({captured_at:new Date().toISOString(),url:location.href,series:await (await fetch("/api/series"+location.search)).json(),summary:await (await fetch("/api/summary"+location.search)).json()})' | python3 -c 'import json,sys; json.dump(json.loads(json.load(sys.stdin)),sys.stdout,indent=2); print()' >"$output-api.json"
playwright-cli -s=caddy-article close
