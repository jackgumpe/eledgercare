"""Create an exclusive SHA256 inventory of the exact committed local custody tree.

The inventory cannot hash itself; the subsequent Git receipt binds its bytes.
Git internals, ignored byte-identical regeneration scratch, and Python cache are excluded.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])

ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
out=a.out.resolve();out.relative_to(ROOT)
if out.exists():raise FileExistsError('Refusing to overwrite inventory')
if git('status','--porcelain').strip():raise RuntimeError('Inventory requires clean committed tree')
files=[]
for raw in git('ls-files','-z').split(b'\0'):
    if not raw:continue
    name=raw.decode('utf-8');path=ROOT/name
    files.append({'path':name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
value={'schema':'eld-wp09-complete-sealed-inventory/1','source_commit':git('rev-parse','HEAD').decode().strip(),
       'scope':'every tracked file at source_commit, including helpers, source, PDFs, expected, references, operators and evidence',
       'excluded':['this subsequently written inventory (bound by following Git commit)','Git internals','ignored regeneration duplicates and Python cache'],
       'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'files':files}
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps({'inventory_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'file_count':len(files),'source_commit':value['source_commit']}))
