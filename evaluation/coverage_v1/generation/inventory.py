"""Exclusive full SHA256 inventory of all committed custody files; Git binds itself."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
out=a.out.resolve();out.relative_to(ROOT)
if out.exists():raise FileExistsError('Refusing to overwrite inventory')
if git('status','--porcelain').strip():raise RuntimeError('Clean committed custody required')
files=[]
for name in git('ls-files','-z').split(b'\0'):
    if name:
        path=name.decode();data=(ROOT/path).read_bytes()
        if data!=git('show','HEAD:'+path):raise AssertionError('Working/Git bytes differ '+path)
        files.append({'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
record={'schema':'eld-wp11-complete-sealed-inventory/1','source_commit':git('rev-parse','HEAD').decode().strip(),
 'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'files':files,
 'scope':'All tracked committed sources/corpus/expected/reference/annotations/rasters/evidence and helpers',
 'exclusions':['this subsequently committed inventory','Git internals','ignored byte-identical regeneration scratch and Python cache']}
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('xb') as handle:handle.write((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({'file_count':len(files),'total_bytes':record['total_bytes'],'inventory_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
