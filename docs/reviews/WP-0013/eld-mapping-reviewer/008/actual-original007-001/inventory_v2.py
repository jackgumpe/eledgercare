"""Publication inventory with explicit Git/working and working-only descriptors."""
from pathlib import Path
import subprocess,json,hashlib,datetime,sys
ROOT=Path(__file__).resolve().parents[6]
HERE=Path(__file__).resolve().parent
BASE='010512b636ed38075f7c9333ce0e2094ddcc6bd7'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def tree(rev):
    out={}
    for row in git('ls-tree','-r','-z',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);mode,typ,blob=meta.decode().split()
            out[path.decode()]={'mode':mode,'type':typ,'git_blob':blob}
    return out
def main():
    end=git('rev-parse','HEAD').decode().strip()
    assert not git('status','--porcelain').strip()
    a,b=tree(BASE),tree(end);assert all(b.get(k)==v for k,v in a.items())
    files=[]
    for path in sorted(set(b)-set(a)):
        assert path.startswith(HERE.relative_to(ROOT).as_posix()+'/')
        data=git('cat-file','blob',b[path]['git_blob']);assert data==(ROOT/path).read_bytes()
        files.append({'path':path,**b[path],'bytes_git':len(data),'sha256_git':sha(data)})
    v=json.loads((HERE/'comparison.json').read_bytes());working_only=[]
    for row in v['source_inventory']:
        working=(ROOT/row['path']).read_bytes()
        if 'git_blob' in row:
            data=git('cat-file','blob',row['git_blob'])
            assert len(data)==row['bytes_git'] and sha(data)==row['sha256_git']
            assert b[row['path']]['git_blob']==row['git_blob']
            assert len(working)==row['bytes_working'] and sha(working)==row['sha256_working']
        else:
            assert set(row)=={'path','bytes','sha256'}
            assert len(working)==row['bytes'] and sha(working)==row['sha256']
            blob=b[row['path']]['git_blob'];data=git('cat-file','blob',blob)
            assert working.replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n')
            working_only.append({'path':row['path'],'working_sha256':sha(working),'git_blob':blob,
                'bytes_git':len(data),'sha256_git':sha(data),'working_git_exact':data==working})
    trees={}
    for row in v['author']['input_inventory']:
        data=git('cat-file','blob',row['git_blob'])
        assert len(data)==row['bytes'] and sha(data)==row['sha256']
        if row['commit'] not in trees:trees[row['commit']]=tree(row['commit'])
        assert trees[row['commit']][row['path']]['git_blob']==row['git_blob']
    value={'schema':'eld-original007-review-inventory/2','base_commit':BASE,'deliverable_commit':end,
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,
        'protected_prior_paths':len(a),'source_descriptors_verified':len(v['source_inventory']),
        'working_only_descriptors':working_only,'input_descriptors_verified':len(v['author']['input_inventory']),
        'all_prior_paths_unchanged':True,'metadata_excluded':['inventory.json','inventory-receipt.json'],
        'canonical_008':False}
    with (HERE/'inventory.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'result':'PASS','files':len(files),'bytes':sum(x['bytes_git'] for x in files),
        'protected_prior_paths':len(a),'source_descriptors':len(v['source_inventory']),
        'input_descriptors':len(v['author']['input_inventory']),
        'inventory_sha256':sha((HERE/'inventory.json').read_bytes())}))
if __name__=='__main__':main()
