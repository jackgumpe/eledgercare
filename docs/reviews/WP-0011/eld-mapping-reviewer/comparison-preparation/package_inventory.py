"""Complete owned preparation inventory; original source/reports remain exact."""
import hashlib
import json
from pathlib import Path
import subprocess

OWN=Path(__file__).resolve().parent;ROOT=OWN.parents[4]
BASE='ff04d44adcb6d799f0a6e7f30e578b3da4b9cdf2'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def listing(rev):
    return {x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0].decode() for x in git('ls-tree','-r','-z',rev).split(b'\0') if x}
def main():
    assert not git('status','--porcelain').strip(),'Commit deliverable before inventory'
    head=git('rev-parse','HEAD').decode().strip();base=listing(BASE);current=listing(head)
    assert all(current.get(k)==v for k,v in base.items())
    prefix=OWN.relative_to(ROOT).as_posix()+'/'
    added=sorted(set(current)-set(base));assert all(k.startswith(prefix) for k in added)
    files=[]
    for path in added:
        data=git('show',head+':'+path);assert data==(ROOT/path).read_bytes()
        files.append({'path':path,'git_mode_type_blob':current[path],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'working_bytes_equal_git':True})
    result={'schema':'eld-review-helper-preparation-inventory/1','base_commit':BASE,'deliverable_commit':head,
            'preserved_base_paths':len(base),'files':files,'scope':'All added preparation artifacts; this subsequent inventory is separate metadata. No actual run acceptance.'}
    target=OWN/'preparation-inventory.json'
    with target.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'files':len(files),'preserved_base_paths':len(base),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
