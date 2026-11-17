"""Verify complete initial-correction finding packet; no runtime/source execution."""
from pathlib import Path
import subprocess,json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[6]
OWN=Path(__file__).resolve().parents[1]
BASE='66b61eb8da64bc5987ee744f92709d50ffd7b199'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def tree(rev):
    result={}
    for row in git('ls-tree','-r','-z',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);mode,typ,blob=meta.decode().split()
            result[path.decode()]={'mode':mode,'type':typ,'git_blob':blob}
    return result
def main():
    end=git('rev-parse','HEAD').decode().strip();assert not git('status','--porcelain').strip()
    a,b=tree(BASE),tree(end);assert all(b.get(k)==v for k,v in a.items())
    files=[]
    for path in sorted(set(b)-set(a)):
        assert path.startswith(OWN.relative_to(ROOT).as_posix()+'/')
        data=git('cat-file','blob',b[path]['git_blob']);assert data==(ROOT/path).read_bytes()
        files.append({'path':path,**b[path],'bytes_git':len(data),'sha256_git':sha(data)})
    originals=0
    for attempt in ['corrected-attempt-1','shadow-attempt-1']:
        collection=json.loads((OWN/attempt/'collection.json').read_bytes())
        for row in collection['files']:
            original=Path(row['original']).read_bytes();copy=(ROOT/row['published_path']).read_bytes()
            assert len(original)==row['bytes'] and sha(original)==row['sha256'] and original==copy
            assert row['published_path'] in b and git('cat-file','blob',b[row['published_path']]['git_blob'])==copy
            originals+=1
    inputs=json.loads((OWN/'corrected-attempt-1/inputs.json').read_bytes())['inputs']
    for row in inputs:
        data=git('cat-file','blob',row['git_blob']);working=(ROOT/row['path']).read_bytes()
        assert len(data)==row['bytes_git'] and sha(data)==row['sha256_git']
        assert len(working)==row['bytes_working'] and sha(working)==row['sha256_working']
    value={'schema':'eld-wp13-initial-correction-review-inventory/1','base_commit':BASE,'deliverable_commit':end,
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'protected_prior_paths':len(a),
        'all_prior_paths_unchanged':True,'original_cpu_files_verified':originals,'input_descriptors_verified':len(inputs),
        'source_tree':git('rev-parse','HEAD:qualification/mapping_v2').decode().strip(),
        'corpus_tree':git('rev-parse','HEAD:evaluation/mapping_v2').decode().strip(),
        'metadata_exclusions':['findings-inventory.json','findings-inventory-receipt.json'],
        'finding':'F011-01','canonical_011':False}
    with (OWN/'findings-inventory.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'result':'PASS','files':len(files),'bytes':sum(x['bytes_git'] for x in files),'protected_prior_paths':len(a),
        'original_cpu_files':originals,'inputs':len(inputs),'inventory_sha256':sha((OWN/'findings-inventory.json').read_bytes())}))
if __name__=='__main__':main()
