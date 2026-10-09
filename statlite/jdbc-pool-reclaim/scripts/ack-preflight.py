#!/usr/bin/env python3
"""Record the operator's VM checks and optional dashboard observation; does not interact with a browser."""
import argparse
from pathlib import Path
import datetime
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preflight', type=Path)
    parser.add_argument('--host-url')
    parser.add_argument('--checked-vm-clock-and-1gib-config', action='store_true', required=True)
    parser.add_argument('--checked-two-targets-and-host-metrics', action='store_true')
    args = parser.parse_args()
    data = json.loads(args.preflight.read_text())
    if not data.get('automated_pass'):
        raise SystemExit('Automated preflight has not passed')
    data.update(environment_acknowledged=True,
                manual_ui_checked=args.checked_two_targets_and_host_metrics, manual_host_url=args.host_url,
                manual_check_time=datetime.datetime.now(datetime.timezone.utc).isoformat())
    args.preflight.write_text(json.dumps(data, indent=2) + '\n')
    print('Manual checks recorded; no measured run started.')
