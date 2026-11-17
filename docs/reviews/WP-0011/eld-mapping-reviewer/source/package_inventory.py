"""Inventory committed reviewer evidence, preserve all prior file identities."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
SCOPE='docs/reviews/WP-0011/eld-mapping-reviewer/source/'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def listing(rev):
    rows={}
    for entry in git('ls-tree','-r','-z',rev).split(b'\0'):
        if entry:
            meta,path=entry.split(b'\t',1);rows[path.decode()]=meta.decode()
    return rows
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--deliverable',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    assert not git('status','--porcelain').strip(),'Commit evidence before inventory'
    base=listing(a.base);head=listing(a.deliverable)
    changed=[k for k,v in base.items() if head.get(k)!=v];assert not changed,changed
    added=sorted(set(head)-set(base));assert all(k.startswith(SCOPE) for k in added),added
    rows=[]
    for path in added:
        data=git('show',a.deliverable+':'+path);working=(ROOT/path).read_bytes()
        assert working==data,'Evidence working/Git bytes differ: '+path
        rows.append({'path':path,'git_mode_type_blob':head[path],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'working_bytes_equal_git':True})
    result={'schema':'eld-review-evidence-inventory/1','base_commit':a.base,'deliverable_commit':a.deliverable,
            'preserved_base_paths':len(base),'changed_existing_paths':changed,'files':rows,
            'inventory_scope':'All added committed reviewer evidence; this subsequently generated inventory is separate metadata.'}
    target=(ROOT/a.out).resolve();target.relative_to(ROOT/SCOPE)
    with target.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'files':len(rows),'preserved_base_paths':len(base),'inventory_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
