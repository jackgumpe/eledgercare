"""Inventory only this public hash-only admission dossier; no private access."""
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[4]
BASE='ad7309f2079ed11bc4a63e52567e6a1e5fba1868'
PREFIX=OWN.relative_to(ROOT).as_posix()+'/'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def require(ok,why):
    if not ok:raise AssertionError(why)
def tree(ref):
    result={}
    for row in git('ls-tree','-rz',ref).split(b'\0'):
        if row:
            identity,path=row.split(b'\t',1);result[path.decode()]=identity.decode().split()
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    require(not git('status','--porcelain').strip(),'Expected clean candidate')
    require(git('rev-parse','HEAD').decode().strip()==a.candidate,'Wrong candidate')
    before=tree(BASE);after=tree(a.candidate)
    require(all(after.get(path)==identity for path,identity in before.items()),'Prior path changed')
    added=sorted(set(after)-set(before))
    require(added and all(path.startswith(PREFIX) for path in added),'Wrong addition ownership')
    entries=[]
    for path in added:
        raw=git('show',a.candidate+':'+path)
        require(raw==(ROOT/path).read_bytes(),'Working/Git bytes differ')
        entries.append({'path':path,'mode':after[path][0],'type':after[path][1],'git_blob':after[path][2],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    receipt=json.loads((OWN/'receipt.json').read_text())
    reservation=git('show',receipt['public_reservation']+':docs/evaluation/WP-0013/reservation/reservation.json')
    require(hashlib.sha256(reservation).hexdigest()==receipt['public_reservation_sha256'],'Public reservation mismatch')
    audit=json.loads(git('show',BASE+':docs/coordination/WP-0013/final-corpus-reservation-audit.json'))
    for own,key in [('complete_custody_files','complete_private_files'),('complete_custody_bytes','complete_private_bytes'),('preserved_early_files','preserved_early_private_files'),('public_artifact_descriptors','public_artifact_descriptors_verified'),('families','families'),('documents','documents'),('pages','pages')]:
        require(receipt['counts'][own]==audit[key],'Public custody count mismatch')
    require(git('rev-parse',a.candidate+':qualification/mapping_v2').decode().strip()==receipt['protocol_tree'],'Protocol tree changed')
    out={'schema':'eld-wp13-public-admission-inventory/1','status':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':BASE,'candidate':a.candidate,'unchanged_prior_paths':len(before),'file_count':len(entries),'files':entries,'private_access':False,'limits':'Checks public identity/count consistency only. Private admission evidence is separately inventoried.','exclusions':['this later inventory','its later execution receipt','the later canonical report']}
    a.out.resolve().relative_to(OWN)
    with a.out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(out,stream,indent=2);stream.write('\n')
    print(json.dumps({'status':'PASS','files':len(entries),'unchanged_prior_paths':len(before)}))
if __name__=='__main__':main()
