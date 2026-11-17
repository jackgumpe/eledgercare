"""Publish only the 28 exact accepted admission artifacts; original repository is read-only."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import traceback

ROOT=Path(__file__).resolve().parents[5]
OWN=Path(__file__).resolve().parent
PRIVATE=Path('C:/Users/jackg/eLedgerCare-Coverage/WP-0011/admission')
RECEIPT='a9a7ca6ae1b2d0e8536e00c190accd520b2a75ee'
AUTHORITY='e47def37be1ceaf04722125a8aee7ddb49e4159e'
INVENTORY_SHA='e04cc2ef8d006d27b708efd03b7be749851fc85ff980b94c6b227a669da4f3ef'
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args])
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def entries(root,rev):
    result={}
    for row in git(root,'ls-tree','-r','-z',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);result[path.decode()]=meta.decode()
    return result
def verify_private():
    assert git(PRIVATE,'rev-parse','HEAD').decode().strip()==RECEIPT
    assert not git(PRIVATE,'status','--porcelain').strip() and not git(PRIVATE,'remote').strip()
    inventory=(PRIVATE/'final-inventory.json').read_bytes();assert sha(inventory)==INVENTORY_SHA
    declared=json.loads(inventory);assert len(declared['files'])==declared['file_count']==27
    rows={f['path']:f for f in declared['files']};rows['final-inventory.json']={'path':'final-inventory.json','bytes':len(inventory),'sha256':INVENTORY_SHA}
    tracked=entries(PRIVATE,RECEIPT);assert set(rows)==set(tracked) and len(tracked)==28
    data={}
    for name,row in rows.items():
        path=(PRIVATE/name).resolve();path.relative_to(PRIVATE)
        raw=path.read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],name
        assert raw==git(PRIVATE,'show',RECEIPT+':'+name),name
        data[name]=raw
    return rows,tracked,data
def authority():
    value=json.loads(git(ROOT,'show',AUTHORITY+':docs/coordination/WP-0011/unseal.json'))
    assert value['allow_content'] is True and value['source_review_commit']=='bfac3057ce0142dcd37372dee26398d682238202'
    assert any(r['head']==RECEIPT and r['inventory_sha256']==INVENTORY_SHA and r['clean'] and r['no_remote'] for r in value['custody_checks'])
def verify_public(rows,tracked,data,committed):
    preserved=OWN/'preserved';actual={p.relative_to(preserved).as_posix() for p in preserved.rglob('*') if p.is_file()}
    assert actual==set(rows),'Extra or missing published original'
    mapping=[];head=entries(ROOT,'HEAD') if committed else None
    for name,row in sorted(rows.items()):
        target=preserved/name;public=target.relative_to(ROOT).as_posix();raw=target.read_bytes();assert raw==data[name]
        item={'private_relative_path':name,'public_path':public,'bytes':len(raw),'sha256':sha(raw),'private_git_mode_type_blob':tracked[name],'working_bytes_equal_private':True}
        if committed:
            assert git(ROOT,'show','HEAD:'+public)==raw and head[public]==tracked[name]
            item['public_git_mode_type_blob']=head[public];item['committed_bytes_equal_private']=True
        mapping.append(item)
    return mapping
def preservation():
    base=entries(ROOT,AUTHORITY);head=entries(ROOT,'HEAD')
    assert all(head.get(k)==v for k,v in base.items())
    prefix=OWN.relative_to(ROOT).as_posix()+'/'
    assert all(k.startswith(prefix) for k in set(head)-set(base))
    return len(base)
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('copy','verify','inventory'));a=p.parse_args()
    assert not git(ROOT,'status','--porcelain').strip(),'Freeze/commit before each phase'
    authority();rows,tracked,data=verify_private();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result={'mode':a.mode,'authority':AUTHORITY,'executing_head':git(ROOT,'rev-parse','HEAD').decode().strip(),'private_receipt':RECEIPT,
            'private_inventory_sha256':INVENTORY_SHA,'helper_sha256':sha(Path(__file__).read_bytes()),'started_utc':started}
    try:
        if a.mode=='copy':
            target=OWN/'preserved';assert not target.exists();target.mkdir()
            for name,raw in data.items():
                path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as f:f.write(raw)
            result['mapping']=verify_public(rows,tracked,data,False)
        else:
            result['mapping']=verify_public(rows,tracked,data,True);result['preserved_authority_paths']=preservation()
            if a.mode=='inventory':
                prefix=OWN.relative_to(ROOT).as_posix()+'/'
                files=[]
                for path,meta in sorted(entries(ROOT,'HEAD').items()):
                    if path.startswith(prefix):
                        raw=git(ROOT,'show','HEAD:'+path);assert raw==(ROOT/path).read_bytes()
                        files.append({'path':path,'git_mode_type_blob':meta,'bytes':len(raw),'sha256':sha(raw),'working_bytes_equal_git':True})
                result['deliverable_commit']=result['executing_head'];result['files']=files
                result['scope']='Every committed publication artifact; this new inventory is subsequent metadata.'
        verify_private();result['private_still_clean_exact_no_remote']=True;result['status']='PASS'
    except BaseException:
        result['status']='FAIL';result['traceback']=traceback.format_exc();write(OWN/('failure-'+a.mode+'.json'),result);raise
    result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    output=OWN/({'copy':'copy-verification.json','verify':'committed-verification.json','inventory':'publication-inventory.json'}[a.mode])
    write(output,result);print(json.dumps({'status':'PASS','mode':a.mode,'original_artifacts':len(rows),'output':output.name,'sha256':sha(output.read_bytes()),'files':len(result.get('files',[]))}))
if __name__=='__main__':main()
