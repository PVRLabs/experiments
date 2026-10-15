#!/usr/bin/env python3
"""Prepare a new reproduction bundle, preserving the archived run manifests."""
import argparse,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('variant',choices=['javalin-jdbi3','javalin-mybatis','javalin-jooq'])
p.add_argument('destination',type=Path)
p.add_argument('--statlite',required=True,type=Path)
p.add_argument('--module',type=Path,help='Use a separate historical jOOQ module')
a=p.parse_args()
module=(a.module or ROOT/a.variant).resolve()
jar=module/'target'/(a.variant+'-1.0.jar')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(a.statlite)!='d95290cb37270d303460ad02489befa7efe8e9f091a650eca9a821eac2555f91':
    p.error('Expected the recorded StatLite 0.6.0 linux_amd64 binary')
if not jar.is_file():p.error('Build the selected module first')
a.destination.mkdir(parents=True,exist_ok=False)
for source,name in [(jar,a.variant+'.jar'),(a.statlite,'statlite'),(ROOT/'guest.sh','guest.sh'),(ROOT/'sampler.sh','sampler.sh')]:
    shutil.copy2(source,a.destination/name)
(a.destination/'statlite').chmod(0o755)
if a.variant=='javalin-jooq':
    historical=(module/'src/main/java/lab/JooqQuoteRepository.java').read_bytes()==(ROOT/'historical/jooq-release-002/JooqQuoteRepository.java').read_bytes()
    checker=ROOT/('historical/jooq-release-002/JooqRepositoryCheck.java' if historical else 'checks/JooqRepositoryCheck.java')
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['javac','-cp',str(jar),'-d',tmp,str(checker)],check=True)
        subprocess.run(['jar','--create','--file',str((a.destination/'jooq-repository-check.jar').resolve()),'-C',tmp,'.'],check=True)
files={str(f.relative_to(module)):sha(f) for f in sorted((module/'src').rglob('*')) if f.is_file()}
files['pom.xml']=sha(module/'pom.xml')
manifest={'variant':a.variant,'scope':'New reproduction build, not an archived measured binary','files':files,
          'artifacts':{f.name:sha(f) for f in sorted(a.destination.iterdir()) if f.is_file()}}
(a.destination/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(a.destination/'input-manifest.json')
