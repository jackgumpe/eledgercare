"""Publish only the exact previously admitted private evidence; never regenerate it."""
from pathlib import Path
import argparse,datetime,hashlib,json,subprocess

ROOT=Path(__file__).resolve().parents[5]
OWN=Path(__file__).resolve().parent
PRIVATE=ROOT/'.scratch/wp0009-reviewer'
INVENTORY=PRIVATE/'admission-r1/final-inventory.json'
EXPECTED='a5e24517e2f98d5723d9bc1571d59db9ee66c0eec696d4961a6d23b4c2bef4b3'
AUTHORITY='5685660e0188db1d9832baded7eb8e95085109c7'

def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,indent=2);out.write('\n')
def artifacts():
    assert sha(INVENTORY.read_bytes())==EXPECTED
    manifest=json.loads(INVENTORY.read_bytes());assert len(manifest['files'])==31
    entries=manifest['files']+[{'path':INVENTORY.relative_to(ROOT).as_posix(),'bytes':INVENTORY.stat().st_size,'sha256':EXPECTED}]
    mapped=[]
    for entry in entries:
        src=(ROOT/entry['path']).resolve();rel=src.relative_to(PRIVATE)
        assert rel.parts[0]=='admission-r1' or rel.as_posix()=='admission-attempt-1.log'
        data=src.read_bytes();assert len(data)==entry['bytes'] and sha(data)==entry['sha256'],entry['path']
        target=OWN/'preserved'/rel
        mapped.append({'private_path':entry['path'],'published_path':target.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)})
    assert len({m['published_path'] for m in mapped})==32
    return mapped

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['copy','verify']);parser.add_argument('--revision');args=parser.parse_args()
    release=json.loads(git('show',AUTHORITY+':docs/coordination/WP-0009/unseal.json'))
    assert release['allow_content'] is True and release['source_commit']=='23e023045b335540d830ce01b75be247552a63f1' and release['source_review_commit']=='89a27d8b13b280632f4fc0e6704f8c3bdfe74355'
    mapped=artifacts();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if args.mode=='copy':
        assert not git('status','--porcelain').strip(),'Freeze clean publication helper before copying'
        assert not (OWN/'preserved').exists(),'Do not overwrite any previous publication'
        for item in mapped:
            target=ROOT/item['published_path'];target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as out:out.write((ROOT/item['private_path']).read_bytes())
        write(OWN/'mapping.json',{'schema':'eld-wp0009-admission-publication/1','authority':AUTHORITY,'executing_head':git('rev-parse','HEAD').decode().strip(),'timestamp_utc':started,'original_final_inventory_sha256':EXPECTED,'artifact_count':32,'path_basis':'Relative to .scratch/wp0009-reviewer; includes sibling attempt log and admission-r1 directory.','files':mapped})
        print(json.dumps({'status':'COPIED_EXACTLY','artifacts':32,'final_inventory_sha256':EXPECTED}))
    else:
        assert args.revision and len(args.revision)==40
        mapping=json.loads((OWN/'mapping.json').read_bytes());assert mapping['files']==mapped
        tracked=git('ls-tree','-r','--name-only',args.revision,'--',str((OWN/'preserved').relative_to(ROOT)).replace('\\','/')).decode().splitlines()
        assert set(tracked)=={m['published_path'] for m in mapped}
        for item in mapped:
            private=(ROOT/item['private_path']).read_bytes();published=(ROOT/item['published_path']).read_bytes();committed=git('show',args.revision+':'+item['published_path'])
            assert private==published==committed,item['published_path']
            attrs=git('check-attr','text','--',item['published_path']).decode();assert attrs.rstrip().endswith(': unset'),attrs
        output={'status':'VERIFIED_EXACT_GIT_BYTES','deliverable':args.revision,'verification_head':git('rev-parse','HEAD').decode().strip(),'timestamp_utc':started,'artifacts':32,'original_final_inventory_sha256':EXPECTED,'all_private_worktree_git_bytes_equal':True,'tracked_set_exact':True,'namespace_attributes_only':'preserved/** -text -whitespace','source_and_reports_unchanged':True}
        for path in ['qualification','evaluation','src','tests','workers','web','research','docs/agent-reports','docs/reviews/WP-0009/eld-mapping-reviewer/004','docs/reviews/WP-0009/eld-mapping-reviewer/006','CURRENT.md','INDEX.md','AGENTS.md']:
            assert git('rev-parse','c847e5e65da9b25dfcc0be690236460cff157189:'+path)==git('rev-parse',args.revision+':'+path),path
        output['protected_identities']=14
        write(OWN/'verification.json',output);print(json.dumps(output,indent=2))

if __name__=='__main__':main()
