#!/usr/bin/env python3
"""Build a new host-side deployment directory; extraction is outside measurement."""
import argparse, hashlib, json, shutil, subprocess, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def prepare(destination, statlite):
    destination=destination.resolve()
    destination.mkdir(parents=True,exist_ok=False)
    coil=ROOT/'coilbase-app/target'
    shutil.copytree(coil/'lib',destination/'coilbase/lib')
    shutil.copy2(coil/'coilbase-app-0.1.0-preview3.jar',destination/'coilbase/app.jar')
    spring=ROOT/'spring-app/target/spring-app-1.0.jar'
    subprocess.run(['java','-Djarmode=tools','-jar',str(spring),'extract','--destination',str(destination/'spring')],check=True)
    # Verify extracted classes/resources and dependency bytes against the built executable.
    with zipfile.ZipFile(spring) as original, zipfile.ZipFile(destination/'spring/spring-app-1.0.jar') as extracted:
        for name in original.namelist():
            if name.endswith('/'): continue
            if name.startswith('BOOT-INF/lib/'):
                assert original.read(name)==(destination/'spring/lib'/Path(name).name).read_bytes(),name
            elif name.startswith('BOOT-INF/classes/'):
                assert original.read(name)==extracted.read(name.removeprefix('BOOT-INF/classes/')),name
    shutil.copy2(statlite,destination/'statlite')
    for name in ['guest.sh','sampler.sh']: shutil.copy2(ROOT/name,destination/name)
    with zipfile.ZipFile(destination/'coilbase/app.jar') as app:
        manifest=app.read('META-INF/MANIFEST.MF').decode().replace('\r\n ','').replace('\r\n','\n')
        refs=next(line.removeprefix('Class-Path: ') for line in manifest.splitlines() if line.startswith('Class-Path: ')).split()
        assert set(refs)=={'lib/'+p.name for p in (destination/'coilbase/lib').glob('*.jar')}, 'stale or missing runtime libraries; clean build required'
    hashes={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination/'artifact-manifest.json').write_text(json.dumps({'files':hashes,'spring_extraction_verified':True,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.is_file() and (p.suffix in ('.java','.xml','.properties','.csv','.py','.sh','.yaml')) and not any(part in ('target','results','prepared-bundles','__pycache__') for part in p.relative_to(ROOT).parts)}},indent=2)+'\n')
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path)
    parser.add_argument('--statlite',type=Path,required=True)
    args=parser.parse_args();print(prepare(args.destination,args.statlite.resolve()))
