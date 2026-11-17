"""Complete reviewer-owned preparation inventory, preserving every authority input."""
import hashlib,json,subprocess
from pathlib import Path
OWN=Path(__file__).resolve().parent;ROOT=OWN.parents[4]
BASE='ddeeaba37868ee635c8f9e5641e3c0fc04404156'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def tree(ref):
    return {row.split(b'\t',1)[1].decode():row.split(b'\t',1)[0].decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row}
def main():
    assert not git('status','--porcelain').strip(),'Clean committed deliverable required'
    head=git('rev-parse','HEAD').decode().strip();before=tree(BASE);after=tree(head)
    assert all(after.get(p)==ident for p,ident in before.items()),'Prior path changed'
    prefix=OWN.relative_to(ROOT).as_posix()+'/'
    added=sorted(set(after)-set(before));assert all(p.startswith(prefix) for p in added),'Unowned addition'
    files=[]
    for p in added:
        raw=git('cat-file','blob',after[p][2]);assert raw==(ROOT/p).read_bytes(),'Git/working bytes differ'
        files.append({'path':p,'mode':after[p][0],'git_blob':after[p][2],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    result={'schema':'eld-review-helper-preparation-inventory/1','base_commit':BASE,'deliverable_commit':head,'preserved_base_paths':len(before),'files':files,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'exclusions':['this later preparation-inventory.json','its later tool receipt'],'scope':'CPU preparation only; no actual result acceptance or canonical008'}
    output=OWN/'preparation-inventory.json'
    with output.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'status':'PASS','files':len(files),'preserved_base_paths':len(before),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
