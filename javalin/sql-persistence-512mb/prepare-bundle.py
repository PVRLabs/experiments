#!/usr/bin/env python3
"""Freeze reviewed builds and preparation checkers into a new deployment bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent
APPS=ROOT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('--statlite', required=True, type=Path, help='StatLite v0.6.0 linux_amd64 executable')
    args=parser.parse_args()
    assert args.name and '/' not in args.name and args.name not in ('.','..')
    bundle=ROOT/'prepared-bundles'/args.name
    bundle.mkdir(parents=True,exist_ok=False)
    inventory=json.loads((APPS/'reproduction-inventory.json').read_text())
    for variant,checker in [('jdbi3','RepositoryCheck'),('mybatis','MyBatisRepositoryCheck'),('jooq','JooqRepositoryCheck')]:
        module=APPS/('javalin-'+variant)
        jar=module/'target'/f'javalin-{variant}-1.0.jar'
        assert hashlib.sha256(jar.read_bytes()).hexdigest()==inventory['applications']['javalin-'+variant]['jar_sha256']
        shutil.copy2(jar,bundle/f'javalin-{variant}.jar')
        classes=module/'target/guest-check-classes'
        classes.mkdir(exist_ok=True)
        subprocess.run(['javac','-cp',str(jar),'-d',str(classes),str(APPS/'checks'/f'{checker}.java'),str(APPS/'checks'/variant/'FixtureRecoveryCheck.java')],check=True)
        subprocess.run(['jar','--create','--file',str(bundle/f'{variant}-checks.jar'),'-C',str(classes),'.'],check=True)
    for name in ['guest.sh','sampler.sh']:
        shutil.copy2(ROOT/name,bundle/name)
    expected_statlite='d95290cb37270d303460ad02489befa7efe8e9f091a650eca9a821eac2555f91'
    assert hashlib.sha256(args.statlite.read_bytes()).hexdigest()==expected_statlite, 'Expected recorded StatLite v0.6.0 linux_amd64 executable'
    shutil.copy2(args.statlite,bundle/'statlite')
    (bundle/'statlite').chmod(0o755)
    selected=['io.javalin:javalin','org.eclipse.jetty:jetty-server',
              'com.zaxxer:HikariCP','com.h2database:h2','io.micrometer:micrometer-core']
    versions={name:inventory['shared_runtime_dependencies'][name] for name in selected}
    versions.update({'jdbi':'3.55.0','mybatis':'3.5.19','jooq':'3.21.9',
                     'statlite':'v0.6.0'})
    repository=ROOT
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repository,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain','--',
               '.'],cwd=repository,text=True).strip())
    preparation={
        'source_commit':commit, 'source_uncommitted_changes':dirty,
        'source_note':'New reproduction build, not an archived measured binary; Git revision and dirty state describe this build.',
        'application_jars':{f'{name}.jar':inventory['applications'][name]['jar_sha256']
                            for name in ['javalin-jdbi3','javalin-mybatis','javalin-jooq']},
        'versions':versions,
        'jvm_flags':['-Xms16m','-Xmx80m','-XX:+UseSerialGC','-Xss512k'],
        'vm':{'cpus':1,'configured_memory_mib':512,'swap':'disabled'},
    }
    (bundle/'preparation.json').write_text(json.dumps(preparation,indent=2)+'\n')
    print(bundle)


if __name__=='__main__':
    main()
