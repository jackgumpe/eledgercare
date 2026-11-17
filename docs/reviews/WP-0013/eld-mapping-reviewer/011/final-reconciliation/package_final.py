"""Verify the final independent review packet without running reviewed code."""
from pathlib import Path
import subprocess,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[6]
OWN=Path(__file__).resolve().parents[1]
BASE='c599e019908f6ff1c14bce02680ef6f1196650da'
PHASE='612aac9a3e3e6e80bb148af17f197cf78b79412b'
SOURCE='ae790497f3fdd10573e8179757416bc2d1736250'
TREE='8fd68c96bb18ca0177f227ad9a82505090d997b0'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def tree(rev):
    result={}
    for row in git('ls-tree','-r','-z',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);mode,typ,blob=meta.decode().split()
            result[path.decode()]={'mode':mode,'type':typ,'git_blob':blob}
    return result
def descriptor(path,entries):
    data=git('cat-file','blob',entries[path]['git_blob'])
    assert data==(ROOT/path).read_bytes(),path
    return {'path':path,**entries[path],'bytes_git':len(data),'sha256_git':sha(data)}
def main():
    end=git('rev-parse','HEAD').decode().strip()
    assert not git('status','--porcelain').strip()
    a,b,phase=tree(BASE),tree(end),tree(PHASE)
    assert all(b.get(k)==v for k,v in a.items()),'merged base changed'
    prefix=OWN.relative_to(ROOT).as_posix()+'/'
    files=[]
    for path in sorted(set(b)-set(a)):
        assert path.startswith(prefix),path
        files.append(descriptor(path,b))
    review_prefix='docs/reviews/WP-0013/eld-mapping-reviewer/'
    assert all(b.get(k)==v for k,v in phase.items() if k.startswith(review_prefix))
    prior=[]
    for path in sorted(set(a)-set(phase)):
        if path.startswith(review_prefix):
            assert path.startswith(prefix+'final-reconciliation/') or path==review_prefix+'008/compare_published_recovery012.py',path
            prior.append(descriptor(path,b))
    collection=json.loads((OWN/'final-evidence/attempt-1/collection.json').read_bytes())
    originals=0
    for row in collection['files']:
        original=Path(row['original']).read_bytes()
        copy=(ROOT/row['published_path']).read_bytes()
        assert len(original)==row['bytes'] and sha(original)==row['sha256'] and original==copy,row['published_path']
        assert row['published_path'] in b
        assert git('cat-file','blob',b[row['published_path']]['git_blob'])==copy
        originals+=1
    assert originals==collection['original_files']==120
    inputs=json.loads((OWN/'final-evidence/attempt-1/standard/inputs.json').read_bytes())['inputs']
    for row in inputs:
        data=git('cat-file','blob',row['git_blob']);working=(ROOT/row['path']).read_bytes()
        assert len(data)==row['bytes_git'] and sha(data)==row['sha256_git'],row['path']
        assert len(working)==row['bytes_working'] and sha(working)==row['sha256_working'],row['path']
        assert b[row['path']]['git_blob']==row['git_blob'],row['path']
    assert git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()==TREE
    corpus=git('rev-parse','HEAD:evaluation/mapping_v2').decode().strip()
    assert corpus=='af22f632c2b69531f61866ca467c6f04f386df7e'
    protocol=sha((ROOT/'qualification/mapping_v2/runtime_protocol.json').read_bytes())
    assert protocol=='ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783'
    value={'schema':'eld-wp13-final-runtime-review-inventory/1','base_commit':BASE,'phase_base_commit':PHASE,
        'deliverable_commit':end,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'files':files,'prior_frozen_phase_files':prior,'protected_prior_paths':len(a),
        'all_merged_base_paths_unchanged':True,'all_prior_reviewer_phase_paths_unchanged':True,
        'original_cpu_files_verified':originals,'original_cpu_bytes_verified':sum(r['bytes'] for r in collection['files']),
        'input_descriptors_verified':len(inputs),'source':SOURCE,'source_tree':TREE,'corpus_tree':corpus,
        'runtime_protocol_sha256':protocol,'author_013_publication':'10a635d2b9292944a54221e72f4c82566bcb464b',
        'metadata_exclusions':['final-inventory.json','final-inventory-receipt.json','canonical011 report'],
        'prior_phases_preserved':['010512b636ed38075f7c9333ce0e2094ddcc6bd7','7cbb53ede74c2aa79ef9411d388bee61be813d05',PHASE],
        'scope':'Independent CPU review and recovery comparison preparation; no inference acceptance'}
    out=OWN/'final-inventory.json'
    with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'result':'PASS','files':len(files),'bytes':sum(r['bytes_git'] for r in files),
        'prior_frozen_phase_files':len(prior),'prior_frozen_phase_bytes':sum(r['bytes_git'] for r in prior),
        'protected_prior_paths':len(a),'original_cpu_files':originals,'inputs':len(inputs),'inventory_sha256':sha(out.read_bytes())}))
if __name__=='__main__':main()
