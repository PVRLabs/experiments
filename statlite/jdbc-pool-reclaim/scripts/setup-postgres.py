#!/usr/bin/env python3
"""Create only dedicated experiment databases/role; never install or reset a cluster."""
import argparse
import json
import os
from pathlib import Path
import pwd
import secrets
import subprocess


def sql(query, port):
    return subprocess.check_output(['runuser', '-u', 'postgres', '--', 'psql', '-X', '-qAt',
                                    '-p', str(port), '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-c', query],
                                   text=True, timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='/etc/pool-reclaim.json')
    parser.add_argument('--guest-user', required=True)
    parser.add_argument('--port', type=int, default=5432)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run as guest root (sudo)')
    user = pwd.getpwnam(args.guest_user)
    if user.pw_uid == 0:
        parser.error('Choose a non-root guest user for Java and StatLite')
    target = Path(args.config)
    if target.exists():
        raise SystemExit('Configuration exists; inspect/reuse it instead of reprovisioning')
    role, databases = 'pool_reclaim', ['pool_reclaim', 'pool_reclaim_smoke']
    if sql("SELECT count(*) FROM pg_roles WHERE rolname='pool_reclaim'", args.port).strip() != '0':
        raise SystemExit('Role already exists; refuse to alter existing credentials')
    if sql("SELECT count(*) FROM pg_database WHERE datname IN ('pool_reclaim','pool_reclaim_smoke')", args.port).strip() != '0':
        raise SystemExit('Database already exists; inspect it first')
    password = secrets.token_hex(24)
    # Send DDL on stdin: do not expose passwords in ps command arguments.
    subprocess.run(['runuser', '-u', 'postgres', '--', 'psql', '-X', '-q', '-p', str(args.port),
                    '-d', 'postgres', '-v', 'ON_ERROR_STOP=1'],
                   input=f"CREATE ROLE {role} LOGIN PASSWORD '{password}';\n" + ''.join(
                       f'CREATE DATABASE {db} OWNER {role};\n' for db in databases),
                   text=True, check=True, timeout=20)
    data = {'role': role, 'password': password, 'port': args.port,
            'database': databases[0], 'smoke_database': databases[1],
            'guest_user': user.pw_name, 'java': '/opt/jdbc-jdk/bin/java'}
    # Interrupted provisioning may leave dedicated resources: preserve and diagnose.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
    print(f'Created dedicated role/databases; secret configuration: {target} (0600). No server tuning changed.')
