#!/usr/bin/env python3
"""Regenerate the simple CSV using only saved raw evidence."""
import argparse
from common import summarize_session

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    args = parser.parse_args()
    for row in summarize_session(args.session):
        print(row['run'], row['status'], 'peak PG:', row['peak_aggregate_pg'], 'errors:', row['overall_errors'])
