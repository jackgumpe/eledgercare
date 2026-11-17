"""Exact-byte collection after bound lease return; no runtime/observer execution."""
import argparse
import datetime
import json
import os
from pathlib import Path
import stat
import traceback
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import execute_wrapper as w

CACHES={'tmp','home','hf-home','hf-modules','torch-home','triton-cache','inductor-cache','cuda-cache','xdg-cache','pip-cache','uv-cache'}
EVIDENCE=w.ROOT/'docs/evidence/WP-0011/eld-mapping-reviewer/006'

def files(root):
    """No-follow walk rejects junctions/symlinks before recursion or file read."""
    root=Path(root)
    def visit(path):
        info=path.stat(follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ValueError('Reparse evidence path: '+str(path))
        if stat.S_ISDIR(info.st_mode):
            for entry in sorted(os.scandir(path),key=lambda e:e.name):yield from visit(Path(entry.path))
        elif stat.S_ISREG(info.st_mode):yield path
        else:raise ValueError('Unsupported evidence entry')
    yield from visit(root)

def copy_file(source,target,copies):
    data=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(data)
    if target.read_bytes()!=data:raise ValueError('Copied bytes changed')
    copies.append({'origin':str(source),'published':target.relative_to(w.ROOT).as_posix(),'bytes':len(data),'sha256':w.sha(data)})

def collect_files(run,attempt,dest):
    copies=[];excluded=[];missing=[];manifest=[]
    if dest.exists():raise FileExistsError('New failure-preserving publication namespace required')
    dest.mkdir(parents=True);(dest/'.gitattributes').write_bytes(b'* -text\n')
    for path in files(run):
        rel=path.relative_to(run);name=rel.as_posix();data=path.read_bytes()
        if len(rel.parts)==1 or rel.parts[0]=='evidence':
            if path.suffix not in ('.json','.jsonl','.txt','.log'):raise ValueError('Unexpected evidence extension: '+name)
            copy_file(path,dest/'run'/rel,copies)
            manifest.append({'relative_path':name,'bytes':len(data),'sha256':w.sha(data),'original_bytes':len(data),'original_sha256':w.sha(data)})
        elif rel.parts[0] in CACHES:excluded.append({'path':name,'bytes':len(data),'sha256':w.sha(data),'reason':'Retained task-local cache; not copied'})
        else:raise ValueError('Unclassified runtime subtree: '+name)
    for path in files(attempt):
        if path.parent!=attempt or path.suffix not in ('.json','.txt','.log'):raise ValueError('Unexpected wrapper artifact: '+str(path))
        copy_file(path,dest/'launch'/path.name,copies)
    for name in ('execute-launch.json','execute-started.json','execute-completion.json','execute.stdout.txt','execute.stderr.txt','score-launch.json','score-completion.json','score.stdout.txt','score.stderr.txt','scores.json'):
        if not (attempt/name).exists():missing.append({'path':name,'status':'absent','limit':'No empty file fabricated; actual receipts/results remain separate.'})
    for row in copies:
        if w.identity(Path(row['origin']))['sha256']!=row['sha256']:raise ValueError('Original changed during collection')
    w.write(dest/'run-copy-manifest.json',{'schema':'eld-review-run-copy-manifest/1','files':manifest,
        'provenance':'Direct retained original-file reads and byte-preserving copies, each rehashed before completing collection.'})
    return {'copies':copies,'copy_count':len(copies),'run_files':len(manifest),'excluded_cache_files':excluded,'missing_wrapper_artifacts':missing}

def main():
    p=argparse.ArgumentParser();p.add_argument('--authority',required=True);p.add_argument('--after',required=True)
    p.add_argument('--run',required=True);p.add_argument('--attempt',required=True);p.add_argument('--destination',required=True);a=p.parse_args()
    r=json.loads(w.git('show',a.authority+':'+w.RELEASE_PATH));afterpath='docs/coordination/WP-0011/reviewer-after/lease-return.json'
    after=json.loads(w.git('show',a.after+':'+afterpath))
    if r['owner']!='reviewer' or after.get('owner')!='reviewer' or after.get('decision')!='RETURNED_OBSERVED' or after.get('lease_id')!=r['lease']['id']:
        raise ValueError('Exact returned reviewer lease required before collection')
    run=w.inside(a.run,Path(r['runtime_root'])/'runs/reviewer');attempt=w.inside(a.attempt,w.SCRATCH);dest=w.inside(a.destination,EVIDENCE)
    if run.parent!=(Path(r['runtime_root'])/'runs/reviewer').resolve():raise ValueError('Exact direct owned run required')
    result={'status':'FAILED','started_utc':w.now(),'helper_head':w.git('rev-parse','HEAD').decode().strip(),
            'runtime_authority':a.authority,'after_authority':a.after,'run':str(run),'attempt':str(attempt),'destination':str(dest)}
    try:
        result.update(collect_files(run,attempt,dest))
        prefix='docs/coordination/WP-0011/reviewer-after/'
        result['bound_root_copies']=[]
        for path in w.git('ls-tree','-r','--name-only',a.after,'--',prefix).decode().splitlines():
            data=w.git('show',a.after+':'+path);target=dest/'root-after'/Path(path).name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(data)
            result['bound_root_copies'].append({'origin':a.after+':'+path,'published':target.relative_to(w.ROOT).as_posix(),'bytes':len(data),'sha256':w.sha(data)})
        result['status']='PASS'
    except BaseException:result['error']=traceback.format_exc()
    result['finished_utc']=w.now();w.write(dest/'collection.json',result)
    print(json.dumps({'status':result['status'],'destination':str(dest),'copy_count':result.get('copy_count')}))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
