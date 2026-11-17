"""File-only sentinel collection/inventory, frozen after actual execution/score."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[6]
OWN=Path(__file__).resolve().parent
OUT=OWN/'attempt-1'
BASE='b782c66990476e5cdefeaf6880aa7685debd222d'
SOURCE='ae790497f3fdd10573e8179757416bc2d1736250'
TREE='8fd68c96bb18ca0177f227ad9a82505090d997b0'
AUTHORITY='d82237366a9877433ba81751ab6ae09b2f182734'
RUN=Path('C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/reviewer/runs/reviewer/20261117T194938Z-1a2fc0f7')
CAPTURE=ROOT/'.scratch/wp0013-reviewer-sentinel/attempt-1'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def tree(rev):
    out={}
    for row in git('ls-tree','-rz',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);mode,typ,blob=meta.decode().split()
            out[path.decode()]={'mode':mode,'type':typ,'git_blob':blob}
    return out
def copy_bytes(data,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(data)
    assert target.read_bytes()==data
    return {'published_path':target.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)}
def collect(return_commit):
    assert re.fullmatch('[0-9a-f]{40}',return_commit)
    assert not git('status','--porcelain').strip()
    assert git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()==TREE
    ack=json.loads(git('show',return_commit+':docs/coordination/WP-0013/reviewer-sentinel-after/lease-return-ack.json'))
    assert ack['lease_returned'] is True and ack['clean_return_verified'] is True
    assert ack['runtime_authority']==AUTHORITY and ack['executing_head']==BASE
    assert not OUT.exists();OUT.mkdir(parents=True)
    result=json.loads((RUN/'run-result.json').read_bytes())
    assert result['executing_head']==BASE and result['release']['source_commit']==SOURCE
    assert result['failure'] is None and [r['status'] for r in result['calls']]==['completed']*3
    assert result['release']['owner']=='reviewer'
    copies=[];all_run=[];manifest=[];retained=[]
    for path in sorted(RUN.rglob('*')):
        if not path.is_file():continue
        assert not path.is_symlink() and path.resolve().is_relative_to(RUN.resolve())
        rel=path.relative_to(RUN).as_posix();data=path.read_bytes()
        row={'relative_path':rel,'original':str(path),'bytes':len(data),'sha256':sha(data)}
        if rel.split('/')[0] in ('cuda-cache','hf-modules'):
            row.update(disposition='retained_only',reason='Per-run CUDA or verified model module cache; original retained in owned runtime and fully hashed. Evidence/load.json separately records module identity.')
            retained.append(row)
        else:
            cp=copy_bytes(data,OUT/'run'/rel);copies.append({'original':str(path),**cp})
            row.update(disposition='published',published_path=cp['published_path'])
            manifest.append({'relative_path':rel,'bytes':len(data),'sha256':sha(data),'original_bytes':len(data),'original_sha256':sha(data)})
        all_run.append(row)
    assert len(all_run)==70 and len(manifest)==41 and len(retained)==29
    for path in sorted(CAPTURE.iterdir()):
        assert path.is_file() and not path.is_symlink()
        target=OUT/'scores.json' if path.name=='scores.json' else OUT/'launch'/path.name
        copies.append({'original':str(path),**copy_bytes(path.read_bytes(),target)})
    proof_rows=[]
    for rev,prefix,dest in [(AUTHORITY,'docs/coordination/WP-0013/releases/reviewer.json','bindings/release.json'),
                            (AUTHORITY,'docs/kickoffs/WP-0013-eld-mapping-reviewer-sentinel-008.md','bindings/kickoff.md')]:
        entries=tree(rev);data=git('cat-file','blob',entries[prefix]['git_blob'])
        proof_rows.append({'commit':rev,'path':prefix,'git_blob':entries[prefix]['git_blob'],**copy_bytes(data,OUT/dest)})
    entries=tree(return_commit);prefix='docs/coordination/WP-0013/reviewer-sentinel-after/'
    paths=sorted(p for p in entries if p.startswith(prefix));assert paths
    for path in paths:
        data=git('cat-file','blob',entries[path]['git_blob'])
        proof_rows.append({'commit':return_commit,'path':path,'git_blob':entries[path]['git_blob'],**copy_bytes(data,OUT/'bindings/return'/path[len(prefix):])})
    write(OUT/'run-copy-manifest.json',{'schema':'eld-review-run-copy-manifest/1','run':str(RUN),'files':manifest,'retained_only':retained,'original_count':len(all_run)})
    write(OUT/'original-run-inventory.json',{'run':str(RUN),'files':all_run,'original_count':len(all_run),'published_count':len(manifest),'retained_count':len(retained)})
    write(OUT/'collection.json',{'schema':'eld-reviewer-runtime-collection/1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'helper_head':git('rev-parse','HEAD').decode().strip(),'executing_head':BASE,'source':SOURCE,'source_tree':TREE,
        'authority':AUTHORITY,'root_return_commit':return_commit,'original_copies':copies,'git_proof_copies':proof_rows,
        'all_original_captures_copied':True,'raw_bytes_preserved':True,'runtime_cache_dispositions':'original-run-inventory.json'})
    print(json.dumps({'result':'COLLECTED','run_files':len(all_run),'published_run_files':len(manifest),'retained_cache_files':len(retained),'original_copies':len(copies),'git_proof_copies':len(proof_rows)}))
def inventory():
    assert not git('status','--porcelain').strip()
    end=git('rev-parse','HEAD').decode().strip();a,b=tree(BASE),tree(end)
    assert all(b.get(k)==v for k,v in a.items())
    rows=[];prefix=OWN.relative_to(ROOT).as_posix()+'/'
    for path in sorted(set(b)-set(a)):
        assert path.startswith(prefix),path
        data=git('cat-file','blob',b[path]['git_blob']);assert data==(ROOT/path).read_bytes()
        rows.append({'path':path,**b[path],'bytes_git':len(data),'sha256_git':sha(data)})
    collection=json.loads((OUT/'collection.json').read_bytes())
    for row in collection['original_copies']:
        data=Path(row['original']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
        assert data==git('cat-file','blob',b[row['published_path']]['git_blob'])
    for row in collection['git_proof_copies']:
        data=git('cat-file','blob',row['git_blob']);assert len(data)==row['bytes'] and sha(data)==row['sha256']
        assert data==git('cat-file','blob',b[row['published_path']]['git_blob'])
    originals=json.loads((OUT/'original-run-inventory.json').read_bytes())
    observed={p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file()}
    assert observed=={r['relative_path'] for r in originals['files']}
    for row in originals['files']:
        data=Path(row['original']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    value={'schema':'eld-review-publication-inventory/1','base_commit':BASE,'deliverable_commit':end,'files':rows,
        'protected_prior_paths':len(a),'all_prior_paths_unchanged':True,'original_copies_verified':len(collection['original_copies']),
        'git_proof_copies_verified':len(collection['git_proof_copies']),'original_runtime_files_verified':len(originals['files']),
        'source':SOURCE,'source_tree':TREE,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'metadata_exclusions':['publication-inventory.json','inventory-receipt.json'],'canonical008':False}
    write(OWN/'publication-inventory.json',value)
    print(json.dumps({'result':'PASS','files':len(rows),'bytes':sum(r['bytes_git'] for r in rows),'protected_prior_paths':len(a),
        'original_copies':len(collection['original_copies']),'proof_copies':len(collection['git_proof_copies']),
        'runtime_files':len(originals['files']),'inventory_sha256':sha((OWN/'publication-inventory.json').read_bytes())}))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['collect','inventory']);ap.add_argument('--return-commit');args=ap.parse_args()
    if args.mode=='collect':collect(args.return_commit)
    else:inventory()
