#!/usr/bin/env python3
"""Prepare a new deployment directory; never deploy or launch it."""
import argparse
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path);args=parser.parse_args()
    dest=args.destination.resolve();dest.mkdir(parents=True,exist_ok=False)
    for name in ['fixture','scripts']:
        shutil.copytree(ROOT/name,dest/name,ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['README.md','vm.yaml']:
        shutil.copy2(ROOT/name,dest/name)
    for variant in ['spring-jpa','coilbase-jdbi','coilbase-hibernate']:
        target=dest/variant/'target';target.mkdir(parents=True)
        if variant=='spring-jpa':shutil.copytree(ROOT/variant/'target/extracted',target/'extracted')
        else:
            shutil.copy2(ROOT/variant/'target'/f'{variant}-1.0-SNAPSHOT.jar',target)
            shutil.copytree(ROOT/variant/'target/lib',target/'lib')
        shutil.copy2(ROOT/variant/'target/runtime-dependencies.txt',target)
    (dest/'source-revision.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True))
    (dest/'source-status.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
    print(dest)
if __name__=='__main__':main()
