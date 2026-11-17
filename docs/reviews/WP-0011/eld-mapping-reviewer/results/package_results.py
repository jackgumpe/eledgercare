"""CPU-only complete publication inventory and exact retained-original verification."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import execute_wrapper as w
import collect_evidence_v2 as collector

BASE='08313e4bc3457dab2c0cee0ff238b3c61c668ddb'
PACKET='docs/evidence/WP-0011/eld-mapping-reviewer/006/attempt-1'
ALLOWED=('docs/reviews/WP-0011/eld-mapping-reviewer/results/',
         'docs/evidence/WP-0011/eld-mapping-reviewer/006/',
         'docs/reviews/WP-0011/eld-mapping-reviewer/comparison-preparation/actual-author-',
         'docs/reviews/WP-0011/eld-mapping-reviewer/comparison-preparation/actual-combined-')
def require(ok,message):
    if not ok:raise ValueError(message)
def entries(rev):
    return {x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0].decode() for x in w.git('ls-tree','-r','-z',rev).split(b'\0') if x}
def verify_originals(head):
    c=w.load(w.ROOT/PACKET/'collection.json');require(c['status']=='PASS','Collection incomplete')
    for row in c['copies']:
        original=Path(row['origin']).read_bytes();published=w.git('show',head+':'+row['published'])
        require(original==published and len(original)==row['bytes'] and w.sha(original)==row['sha256'],'Original/copy mismatch: '+row['published'])
    for row in c['bound_root_copies']:
        original=w.git('show',row['origin']);published=w.git('show',head+':'+row['published'])
        require(original==published and len(original)==row['bytes'] and w.sha(original)==row['sha256'],'Root proof mismatch')
    run=Path(c['run']);manifest=w.load(w.ROOT/PACKET/'run-copy-manifest.json')
    copied={x['relative_path'] for x in manifest['files']};caches={x['path'] for x in c['excluded_cache_files']}
    actual={x.relative_to(run).as_posix() for x in collector.files(run)}
    require(not copied&caches and actual==copied|caches,'Incomplete original run inventory')
    for row in c['excluded_cache_files']:
        data=(run/row['path']).read_bytes();require(len(data)==row['bytes'] and w.sha(data)==row['sha256'],'Retained cache changed')
    return {'original_copies':len(c['copies']),'root_proof_copies':len(c['bound_root_copies']),
            'runtime_files':len(actual),'copied_runtime_files':len(copied),'retained_cache_files':len(caches),
            'missing_wrapper_artifacts':c['missing_wrapper_artifacts'],'all_original_and_git_bytes_equal':True}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    target=w.inside(a.output,w.HERE);require(not target.exists(),'Never overwrite an inventory')
    require(not w.git('status','--porcelain').strip(),'Commit delivery before inventory')
    head=w.git('rev-parse','HEAD').decode().strip();base=entries(BASE);end=entries(head)
    require(all(end.get(k)==v for k,v in base.items()),'Previously committed path changed')
    added=sorted(set(end)-set(base));require(all(x.startswith(ALLOWED) for x in added),'Unowned delivery path')
    rows=[]
    for path in added:
        raw=w.git('show',head+':'+path);working=(w.ROOT/path).read_bytes()
        require(raw==working,'Working/Git byte mismatch: '+path)
        mode,kind,blob=end[path].split()
        rows.append({'path':path,'mode':mode,'type':kind,'git_blob':blob,'bytes_git':len(raw),'sha256_git':w.sha(raw),
                     'bytes_working':len(working),'sha256_working':w.sha(working)})
    receipt={'schema':'eld-review-publication-inventory/1','base_commit':BASE,'deliverable_commit':head,
             'preserved_base_paths':len(base),'files':rows,'original_verification':verify_originals(head),
             'source_tree':w.git('rev-parse','HEAD:qualification/coverage_v1').decode().strip(),
             'scope':'Reviewer result artifacts only. This inventory is subsequent metadata; canonical report follows separately.'}
    w.write(target,receipt)
    print(json.dumps({'files':len(rows),'preserved_base_paths':len(base),'sha256':w.sha(target.read_bytes()),'original_verification':receipt['original_verification']}))
if __name__=='__main__':main()
