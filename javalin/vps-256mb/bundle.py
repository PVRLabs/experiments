#!/usr/bin/env python3
"""Host tools-mode extraction and integrity checks for a reproduction build."""
import argparse, hashlib, json, shutil, subprocess, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(data):return hashlib.sha256(data).hexdigest()
def prepare(destination):
    source=ROOT/'bundle'
    artifacts={name:digest((source/name).read_bytes()) for name in ('javalin.jar','spring.jar','statlite')}
    destination.mkdir(parents=True,exist_ok=False)
    for name in ('javalin.jar','statlite'):shutil.copy2(source/name,destination/name)
    for name in ('guest.sh','sampler.sh'):shutil.copy2(ROOT/name,destination/name)
    command=['java','-Djarmode=tools','-jar',str(source/'spring.jar'),'extract','--destination',str(destination/'spring-extracted')]
    subprocess.run(command,check=True)
    extracted=destination/'spring-extracted/spring.jar'
    with zipfile.ZipFile(source/'spring.jar') as nested, zipfile.ZipFile(extracted) as app:
        libraries=[n for n in nested.namelist() if n.startswith('BOOT-INF/lib/') and n.endswith('.jar')]
        for name in libraries:
            assert nested.read(name)==(destination/'spring-extracted/lib'/Path(name).name).read_bytes(),name
        resources=[n for n in nested.namelist() if n.startswith('BOOT-INF/classes/') and not n.endswith('/')]
        for name in resources:assert nested.read(name)==app.read(name.removeprefix('BOOT-INF/classes/')),name
        manifest=app.read('META-INF/MANIFEST.MF').decode().replace('\r\n ','').replace('\r\n','\n')
        assert 'Main-Class: lab.SpringApp\n' in manifest
        refs=next(line.removeprefix('Class-Path: ') for line in manifest.splitlines() if line.startswith('Class-Path: ')).split()
        assert all((extracted.parent/ref).is_file() for ref in refs)
        assert set(refs)=={'lib/'+Path(n).name for n in libraries}
    shutil.copyfile(ROOT/'evidence/inputs.json',destination/'recorded-inputs.json')
    evidence={'spring_original_sha256':artifacts['spring.jar'],'javalin_sha256':artifacts['javalin.jar'],
              'command':command,'launch_jar':'spring-extracted/spring.jar','library_count':len(libraries),
              'application_resource_count':len(resources),'all_library_and_resource_bytes_unchanged':True,
              'extraction_location':'host; outside measured guest','files':{str(p.relative_to(destination)):digest(p.read_bytes()) for p in destination.rglob('*') if p.is_file()}}
    (destination/'artifact-manifest.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps({k:v for k,v in evidence.items() if k!='files'},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination',type=Path);args=p.parse_args();prepare(args.destination.resolve())
