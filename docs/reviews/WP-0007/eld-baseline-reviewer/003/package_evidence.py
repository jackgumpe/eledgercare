"""Preserve actual owned CPU probe outputs; no corpus/model source traversal."""
import hashlib,json,shutil
from pathlib import Path

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[4]
for tag in ('97249fa6-043410','ef5e68c5-043506'):
    source=ROOT/'.scratch/wp0007-review-003'/tag
    target=OWN/'evidence'/tag/'retained-scratch'
    selected=[]
    for name in ('dev','supervisor-stub','supervisor-root','lifetime'):
        parent=source/name
        if parent.exists():selected.extend(p for p in parent.rglob('*') if p.is_file())
    if (source/'supervisor-scores.json').exists():selected.append(source/'supervisor-scores.json')
    for path in selected:
        path.resolve().relative_to(source.resolve())
        out=target/path.relative_to(source)
        out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists():raise RuntimeError('Evidence already exists: '+str(out))
        shutil.copyfile(path,out)
inventory=[]
for path in sorted((OWN/'evidence').rglob('*')):
    if path.is_file():
        data=path.read_bytes()
        inventory.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
with (OWN/'evidence-inventory.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump({'scope':'Independent reviewer actual CPU outputs; no model/GPU or held-out content','entries':inventory},f,indent=2);f.write('\n')
print(json.dumps({'files':len(inventory),'bytes':sum(x['bytes'] for x in inventory)}))
