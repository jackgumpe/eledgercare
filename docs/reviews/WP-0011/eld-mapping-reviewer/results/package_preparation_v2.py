"""Preparation-only complete owned inventory and baseline preservation."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import execute_wrapper as w
BASE='ba3debdf4f9ec866e52739640e0f837721ac7550'
def entries(rev):return {x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0].decode() for x in w.git('ls-tree','-r','-z',rev).split(b'\0') if x}
def main():
    assert not w.git('status','--porcelain').strip()
    head=w.git('rev-parse','HEAD').decode().strip();base=entries(BASE);current=entries(head)
    assert all(current.get(k)==v for k,v in base.items());added=sorted(set(current)-set(base))
    prefix=w.HERE.relative_to(w.ROOT).as_posix()+'/'
    assert all(x.startswith(prefix) for x in added)
    files=[]
    for path in added:
        raw=w.git('show',head+':'+path);assert raw==(w.ROOT/path).read_bytes()
        files.append({'path':path,'git_mode_type_blob':current[path],'bytes':len(raw),'sha256':w.sha(raw),'working_bytes_equal_git':True})
    result={'schema':'eld-reviewer-execution-preparation-inventory/1','base_commit':BASE,'deliverable_commit':head,'preserved_base_paths':len(base),'files':files,
            'scope':'CPU preparation artifacts only; this inventory is subsequent metadata, no runtime release.'}
    target=w.HERE/'preparation-inventory.json';w.write(target,result)
    print(json.dumps({'files':len(files),'preserved_base_paths':len(base),'sha256':w.sha(target.read_bytes())}))
if __name__=='__main__':main()
