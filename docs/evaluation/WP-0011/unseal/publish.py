"""Publish admitted WP-0011 bytes after exact unseal; never regenerate or infer.

Each mode uses an exclusive retained attempt receipt. Inventory hashes committed bytes
and compares working bytes. Original repositories are read-only. No process/service/GPU
query, model, rendering, mapper or scorer execution is present.
"""
from __future__ import annotations
import argparse,datetime,hashlib,io,json,re,subprocess,sys,traceback
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'docs/evaluation/WP-0011/unseal'
SEALED=Path('C:/Users/jackg/eLedgerCare-Coverage/WP-0011/sealed').resolve()
PREFIX='evaluation/coverage_v1/'
DEST=ROOT/PREFIX
AUTHORITY='e47def37be1ceaf04722125a8aee7ddb49e4159e'
SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'
SOURCE_TREE='6bdab544c9fe26cbf093cc765212db2a2e7a97a5'
PROTOCOL_SHA='03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000'
REVIEW='bfac3057ce0142dcd37372dee26398d682238202'
ADMISSION='021dc265790c90ae83f1afa24fc3f2a71eae41e1'
INTEGRATION='55b4ac15d7d989669e6515b66aa6f0c7f885b18a'
SEALED_COMMIT='6583715067d3a027dd2502ed9623cf02c545391d'
INVENTORY='inventory/sha256-r1.json'
INVENTORY_SHA='bd37f4020a4b5b185379d9d7d2e529b39ebc0d3fa0aa37802d2bccc0546c4330'
RESERVATION='docs/evaluation/WP-0011/reservation/reservation.json'
RESERVATION_COMMIT='98a3a3f73df0e578ae98ebf3923db7ba4882d018'
RESERVATION_SHA='ac58c97459b199232cb541ba2216159cada61db73b8e44abaa4128a22284cddc'

def sha(data):return hashlib.sha256(data).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
def text(repo,*args):return git(repo,*args).decode().strip()
def require(ok,message):
    if not ok:raise AssertionError(message)
def tree(repo,ref):
    result={}
    for row in git(repo,'ls-tree','-r','-z',ref).split(b'\0'):
        if row:
            metadata,path=row.split(b'\t',1);mode,kind,oid=metadata.decode().split()
            result[path.decode()]={'mode':mode,'type':kind,'git_blob':oid}
    return result
def write_exclusive(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write((json.dumps(value,indent=2)+'\n').encode())

def preflight(receipt,helper_commit):
    require(ROOT.resolve()==Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-custodian').resolve(),'wrong owned public root')
    require(text(ROOT,'branch','--show-current')=='evaluation/wp-0011-diagnostic-families','wrong owned branch')
    DEST.resolve().relative_to(ROOT.resolve())
    require(git(ROOT,'show',helper_commit+':docs/evaluation/WP-0011/unseal/publish.py')==Path(__file__).read_bytes(),'publication helper differs from freeze')
    git(ROOT,'merge-base','--is-ancestor',AUTHORITY,'HEAD')
    release_bytes=git(ROOT,'show',AUTHORITY+':docs/coordination/WP-0011/unseal.json');release=json.loads(release_bytes)
    bindings={'schema':'eld-coverage-v1-unseal/1','allow_content':True,'source_commit':SOURCE,
      'source_tree':SOURCE_TREE,'protocol_sha256':PROTOCOL_SHA,'source_review_commit':REVIEW,
      'admission_review_commit':ADMISSION,'reservation_sha256':RESERVATION_SHA,'accepted_integration':INTEGRATION}
    for key,value in bindings.items():require(release[key]==value,'unseal mismatch '+key)
    custody=next(c for c in release['custody_checks'] if Path(c['repository']).resolve()==SEALED)
    require(custody['head']==SEALED_COMMIT and custody['clean'] and custody['no_remote'] and custody['inventory_sha256']==INVENTORY_SHA,'unseal custody binding')
    for ancestor in (SOURCE,REVIEW,ADMISSION,INTEGRATION,RESERVATION_COMMIT):git(ROOT,'merge-base','--is-ancestor',ancestor,AUTHORITY)
    require(text(ROOT,'rev-parse',SOURCE+':qualification/coverage_v1')==text(ROOT,'rev-parse',AUTHORITY+':qualification/coverage_v1')==SOURCE_TREE,'accepted diagnostic source tree')
    require(sha(git(ROOT,'show',SOURCE+':qualification/coverage_v1/protocol.json'))==PROTOCOL_SHA,'accepted protocol bytes')
    reservation_bytes=git(ROOT,'show',AUTHORITY+':'+RESERVATION)
    require(sha(reservation_bytes)==RESERVATION_SHA and reservation_bytes==git(ROOT,'show',RESERVATION_COMMIT+':'+RESERVATION),'original reservation binding')
    reservation=json.loads(reservation_bytes)
    require(text(SEALED,'rev-parse','HEAD')==SEALED_COMMIT and text(SEALED,'branch','--show-current')=='sealed/wp-0011','original custody HEAD/branch')
    require(not text(SEALED,'status','--porcelain') and not text(SEALED,'remote'),'original custody must remain clean/no remote')
    invbytes=(SEALED/INVENTORY).read_bytes();require(sha(invbytes)==INVENTORY_SHA,'original inventory hash')
    inv=json.loads(invbytes);require(inv['file_count']==108==len(inv['files']),'original inventory count')
    entries={f['path']:f for f in inv['files']};entries[INVENTORY]={'bytes':len(invbytes),'sha256':INVENTORY_SHA}
    original_tree=tree(SEALED,SEALED_COMMIT)
    require(len(original_tree)==109 and set(original_tree)==set(entries),'109 admitted tracked identities')
    files=[]
    for path in sorted(entries):
        original=(SEALED/path).resolve();original.relative_to(SEALED)
        require(original.is_file() and not original.is_symlink(),'invalid original path')
        data=original.read_bytes();bound=entries[path]
        require(data==git(SEALED,'show',SEALED_COMMIT+':'+path) and len(data)==bound['bytes'] and sha(data)==bound['sha256'],'original file identity '+path)
        files.append({'sealed_relative_path':path,'public_path':PREFIX+path,'bytes':len(data),
                      'sha256':sha(data),'sealed_git_blob':original_tree[path]['git_blob'],'mode':original_tree[path]['mode']})
    core=0;pdfs=[]
    require(len(reservation['fixtures'])==12,'reserved fixture count')
    for fixture in reservation['fixtures']:
        require({a['role'] for a in fixture['artifacts']}=={'pdf','expected','reference','annotations'},'four artifact roles')
        for artifact in fixture['artifacts']:
            relative=artifact['sealed_relative_path'];require(artifact['path']==PREFIX+relative,'reserved publication path')
            data=(SEALED/relative).read_bytes();require(len(data)==artifact['bytes'] and sha(data)==artifact['sha256'],'reserved core artifact bytes');core+=1
            if artifact['role']=='pdf':
                pages=len(PdfReader(io.BytesIO(data),strict=True).pages);require(pages==fixture['page_count']==1,'one-page PDF count')
                pdfs.append({k:fixture[k] for k in ('fixture_id','family_id','condition','page_count')})
    require(core==48 and len(pdfs)==12 and len({f['family_id'] for f in pdfs})==3,'bounded admitted corpus counts')
    prior=tree(ROOT,AUTHORITY)
    receipt.update({'authority_commit':AUTHORITY,'unseal_sha256':sha(release_bytes),'release':release,
        'helper_commit':helper_commit,'helper_sha256':sha(Path(__file__).read_bytes()),
        'sealed_commit':SEALED_COMMIT,'inventory_sha256':INVENTORY_SHA,'reservation_sha256':RESERVATION_SHA,
        'source_file_count':109,'source_total_bytes':sum(f['bytes'] for f in files),'files':files,
        'core_artifacts_verified':48,'pdfs':pdfs,'pages':12,'families':3,
        'authority_input_files':len(prior),'original_custody_clean_no_remote':True})
    receipt['checks'].extend(['exact accepted source/protocol/review/admission/unseal bindings','original reservation hash and publication-prefix bindings',
      'frozen publication helper','clean no-remote original custody at exact receipt','108 inventory entries plus inventory; original working/Git bytes',
      '48 reserved artifact hashes and actual twelve one-page PDF counts'])
    return files,prior

def verify_disk(files):
    actual={str(p.relative_to(ROOT)).replace('\\','/') for p in DEST.rglob('*') if p.is_file()}
    require(actual=={f['public_path'] for f in files},'destination exact path set')
    for f in files:
        p=ROOT/f['public_path'];require(not p.is_symlink(),'destination symlink')
        data=p.read_bytes();require(len(data)==f['bytes'] and sha(data)==f['sha256'],'destination byte mismatch')

def attributes(files,receipt):
    values=git(ROOT,'check-attr','--cached','-z','text','eol','filter','--',*[f['public_path'] for f in files]).split(b'\0')
    attrs=[tuple(v.decode() for v in values[i:i+3]) for i in range(0,len(values)-1,3)]
    require(all(v=='unset' for p,a,v in attrs if a=='text'),'text conversion unexpectedly enabled')
    require(all(v in ('unspecified','unset') for p,a,v in attrs if a=='filter'),'unexpected Git filter')
    receipt['attributes']=[{'path':p,'attribute':a,'value':v} for p,a,v in attrs]
    receipt['line_endings']='Original admitted .gitattributes contains * -text and is copied byte-exact as one of109. It disables text normalization even when inherited eol=lf is present. No extra corpus attributes file/root change is needed.'

def committed(files,prior,candidate,receipt):
    require(text(ROOT,'rev-parse','HEAD')==candidate,'candidate must be current exact HEAD')
    verify_disk(files);attributes(files,receipt)
    current=tree(ROOT,candidate)
    require(all(current.get(p)==v for p,v in prior.items()),'preexisting authority input changed')
    added=sorted(set(current)-set(prior))
    require(all(p.startswith(PREFIX) or p.startswith('docs/evaluation/WP-0011/unseal/') for p in added),'unowned additions')
    require({p for p in current if p.startswith(PREFIX)}=={f['public_path'] for f in files},'committed corpus path set')
    for f in files:
        data=git(ROOT,'show',candidate+':'+f['public_path'])
        require(len(data)==f['bytes'] and sha(data)==f['sha256'],'committed corpus byte mismatch')
        require(current[f['public_path']]['git_blob']==f['sealed_git_blob'] and current[f['public_path']]['mode']==f['mode'],'original/public Git object/mode identity')
    receipt.update({'candidate_commit':candidate,'authority_input_files_unchanged':len(prior),'candidate_added_paths':added,'all109_original_public_blobs_and_modes_equal':True})
    return current,added

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('copy','verify-index','verify-commit','inventory'),required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--helper-commit',required=True);p.add_argument('--candidate');a=p.parse_args()
    require(bool(re.fullmatch('[a-z0-9-]+',a.run_id)),'invalid attempt name')
    output=HERE/'attempts'/a.run_id/'receipt.json';require(not output.parent.exists(),'existing attempt must be retained');output.parent.mkdir(parents=True)
    receipt={'schema':'eld-wp11-exact-publication/1','mode':a.mode,'started_utc':utc(),'command':[sys.executable,*sys.argv],
      'python':sys.version,'checks':[],'status':'running','regeneration':False,'model_inference':False,'rendering':False,'source_mutation':False}
    try:
        files,prior=preflight(receipt,a.helper_commit)
        if a.mode=='copy':
            require(not DEST.exists(),'unexpected existing destination: preserve and request coordinator disposition')
            require(not text(ROOT,'diff','--name-only') and not text(ROOT,'diff','--cached','--name-only'),'tracked/index edits before copy')
            receipt['destination_absent_before_copy']=True;DEST.mkdir(parents=True)
            for f in files:
                target=ROOT/f['public_path'];target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as handle:handle.write((SEALED/f['sealed_relative_path']).read_bytes())
            verify_disk(files);receipt['checks'].append('exclusive109-file copy and checked-out byte identity')
        elif a.mode=='verify-index':
            verify_disk(files);attributes(files,receipt)
            require(set(text(ROOT,'diff','--cached','--name-only').splitlines())=={f['public_path'] for f in files},'staged scope must be exactly109 admitted files')
            for f in files:
                data=git(ROOT,'show',':'+f['public_path']);require(len(data)==f['bytes'] and sha(data)==f['sha256'],'staged Git byte mismatch')
            receipt['checks'].append('all109 disk/staged blobs and attribute semantics verified')
        else:
            require(a.candidate is not None,'candidate commit required')
            current,added=committed(files,prior,a.candidate,receipt)
            receipt['checks'].append('all109 committed blobs/modes plus complete authority-input preservation')
            if a.mode=='inventory':
                entries=[]
                for path in added:
                    data=git(ROOT,'show',a.candidate+':'+path);require(data==(ROOT/path).read_bytes(),'metadata working/Git bytes differ')
                    entries.append({'path':path,'bytes':len(data),'sha256':sha(data),**current[path],
                       'role':'admitted_corpus' if path.startswith(PREFIX) else 'publication_helper_or_evidence'})
                inventory={'schema':'eld-wp11-publication-inventory/1','authority_base':AUTHORITY,'source_commit':a.candidate,
                  'file_count':len(entries),'total_bytes':sum(e['bytes'] for e in entries),'files':entries,
                  'admitted_corpus_files':109,'authority_inputs_preserved':len(prior),
                  'exclusions':['this subsequently committed inventory','this inventory attempt receipt','later canonical /008 report']}
                path=HERE/'publication-inventory.json';write_exclusive(path,inventory)
                receipt.update(publication_inventory_sha256=sha(path.read_bytes()),publication_inventory_entries=len(entries))
                receipt['checks'].append('complete changed-path inventory from committed/working bytes')
        require(text(SEALED,'rev-parse','HEAD')==SEALED_COMMIT and not text(SEALED,'status','--porcelain') and not text(SEALED,'remote'),'original custody changed during operation')
        receipt['status']='passed'
    except Exception:
        receipt['status']='failed';receipt['failure']=traceback.format_exc()
    finally:
        receipt['ended_utc']=utc();write_exclusive(output,receipt)
        print(json.dumps({'status':receipt['status'],'mode':a.mode,'checks':len(receipt['checks']),'receipt':str(output)}))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
