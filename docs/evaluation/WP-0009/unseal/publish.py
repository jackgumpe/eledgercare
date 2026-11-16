"""Exact admitted-corpus publication; no generation, rendering, mapper or model calls.

Freeze this helper before use. All modes retain an exclusive attempt receipt, including
failures. Copy mode refuses existing destinations. Original custody is read-only.
"""
from __future__ import annotations
import argparse, datetime, hashlib, io, json, re, subprocess, sys, traceback
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'docs/evaluation/WP-0009/unseal'
SEALED=Path('C:/Users/jackg/eLedgerCare-Mapping/WP-0009/sealed').resolve()
DEST=ROOT/'evaluation/mapping_v1'
AUTHORITY='5685660e0188db1d9832baded7eb8e95085109c7'
SEALED_COMMIT='559c5d09490b7729be26fb9bf9d872305cae3303'
INVENTORY='inventory/sha256-r1.json'
INVENTORY_SHA='c2971612374178aaf1194f4b3a48e0c8435d14305b813b290f0e1e2b856ac322'
RESERVATION='docs/evaluation/WP-0009/reservation/reservation.json'
RESERVATION_SHA='f1490c428109e94f8b15c62a9f2ef3386039e614eb046a647957f2d0c759bdba'
SOURCE='23e023045b335540d830ce01b75be247552a63f1'
SOURCE_REVIEW='89a27d8b13b280632f4fc0e6704f8c3bdfe74355'
ADMISSION='3e5d305d0cdcb2666ba56912ba6c06dc19d74c8b'
PREFIX='evaluation/mapping_v1/'

def sha(data):return hashlib.sha256(data).hexdigest()
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
def txt(repo,*args):return git(repo,*args).decode('utf-8').strip()
def require(ok,message):
    if not ok:raise AssertionError(message)
def tree(repo,ref):
    entries={}
    for line in git(repo,'ls-tree','-r','-z',ref).split(b'\0'):
        if line:
            meta,name=line.split(b'\t',1);mode,kind,oid=meta.decode().split()
            entries[name.decode()]={'mode':mode,'type':kind,'git_blob':oid}
    return entries
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def preflight(receipt,helper_commit):
    require(ROOT.resolve()==Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-eval-custodian').resolve(),'wrong public workspace')
    require(SEALED==Path('C:/Users/jackg/eLedgerCare-Mapping/WP-0009/sealed').resolve(),'wrong sealed path')
    require(txt(ROOT,'branch','--show-current')=='evaluation/wp-0009-fresh-families','wrong public branch')
    require(git(ROOT,'show',helper_commit+':docs/evaluation/WP-0009/unseal/publish.py')==Path(__file__).read_bytes(),'helper differs from freeze')
    git(ROOT,'merge-base','--is-ancestor',AUTHORITY,'HEAD')
    release_bytes=git(ROOT,'show',AUTHORITY+':docs/coordination/WP-0009/unseal.json')
    release=json.loads(release_bytes)
    for key,want in {'allow_content':True,'source_commit':SOURCE,'source_review_commit':SOURCE_REVIEW,
          'reservation_sha256':RESERVATION_SHA,'admission_review_commit':ADMISSION,
          'sealed_commit':SEALED_COMMIT,'publication_prefix':PREFIX}.items():
        require(release[key]==want,'unseal binding mismatch: '+key)
    for ancestor in (SOURCE,SOURCE_REVIEW,ADMISSION,'7513a9a86e6af55a6d8ca7f5a8dc0f80f054ba0b'):
        git(ROOT,'merge-base','--is-ancestor',ancestor,AUTHORITY)
    require(txt(ROOT,'rev-parse',SOURCE+':qualification/mapping_v1')==txt(ROOT,'rev-parse',AUTHORITY+':qualification/mapping_v1'),'accepted mapper tree mismatch')
    reservation_bytes=git(ROOT,'show',AUTHORITY+':'+RESERVATION)
    require(sha(reservation_bytes)==RESERVATION_SHA,'reservation committed-byte binding')
    reservation=json.loads(reservation_bytes)
    require(txt(SEALED,'rev-parse','HEAD')==SEALED_COMMIT,'sealed HEAD changed')
    require(txt(SEALED,'branch','--show-current')=='sealed/wp-0009','sealed branch changed')
    require(not txt(SEALED,'status','--porcelain'),'sealed tracked/untracked state changed')
    require(not txt(SEALED,'remote'),'sealed remote unexpectedly configured')
    invbytes=(SEALED/INVENTORY).read_bytes();require(sha(invbytes)==INVENTORY_SHA,'inventory bytes changed')
    inv=json.loads(invbytes);require(inv['file_count']==39==len(inv['files']),'inventory count')
    entries={f['path']:f for f in inv['files']}
    entries[INVENTORY]={'path':INVENTORY,'bytes':len(invbytes),'sha256':INVENTORY_SHA}
    tracked=tree(SEALED,SEALED_COMMIT)
    require(set(tracked)==set(entries) and len(tracked)==40,'admitted tracked path set')
    files=[]
    for path in sorted(entries):
        expected=entries[path];source=(SEALED/path).resolve();source.relative_to(SEALED)
        require(not source.is_symlink() and source.is_file(),'invalid source object')
        data=source.read_bytes();committed=git(SEALED,'show',SEALED_COMMIT+':'+path)
        require(data==committed and len(data)==expected['bytes'] and sha(data)==expected['sha256'],'original source identity '+path)
        files.append({'sealed_relative_path':path,'public_path':PREFIX+path,'bytes':len(data),'sha256':sha(data),
                      'sealed_git_blob':tracked[path]['git_blob']})
    core=0;pdfs=[]
    for fixture in reservation['fixtures']:
        for artifact in fixture['artifacts']:
            data=(SEALED/artifact['sealed_relative_path']).read_bytes()
            require(len(data)==artifact['bytes'] and sha(data)==artifact['sha256'],'public core identity')
            core+=1
            if artifact['role']=='pdf':
                pages=len(PdfReader(io.BytesIO(data),strict=True).pages)
                require(pages==fixture['page_count'],'PDF page count')
                pdfs.append({'fixture_id':fixture['fixture_id'],'page_count':pages,'sha256':sha(data)})
    require(core==20 and len(pdfs)==4 and sorted(f['page_count'] for f in pdfs)==[1,1,1,3],'bounded corpus counts')
    original_tree=tree(ROOT,AUTHORITY)
    receipt.update({'authority_commit':AUTHORITY,'unseal_sha256':sha(release_bytes),'release':release,
        'helper_commit':helper_commit,'helper_sha256':sha(Path(__file__).read_bytes()),
        'sealed_commit':SEALED_COMMIT,'sealed_inventory_sha256':INVENTORY_SHA,'reservation_committed_sha256':RESERVATION_SHA,
        'source_files':files,'source_file_count':40,'source_total_bytes':sum(f['bytes'] for f in files),
        'public_core_artifacts_verified':core,'pdfs':pdfs,'pages':sum(f['page_count'] for f in pdfs),
        'all_authority_input_files':len(original_tree),'original_sealed_clean_no_remote':True})
    receipt['checks'].extend(['exact unseal/source/review/admission/reservation bindings','frozen publication helper bytes',
        'clean exact no-remote sealed repository','39 inventory entries plus inventory and all original Git bytes',
        '20 reserved core artifacts and four PDFs/six pages'])
    return files,original_tree

def verify_disk(files):
    actual={str(p.relative_to(ROOT)).replace('\\','/') for p in DEST.rglob('*') if p.is_file()}
    require(actual=={f['public_path'] for f in files},'destination file set mismatch')
    for f in files:
        p=ROOT/f['public_path'];require(not p.is_symlink(),'destination symlink')
        data=p.read_bytes();require(len(data)==f['bytes'] and sha(data)==f['sha256'],'destination byte mismatch '+f['public_path'])

def verify_attributes(files,receipt):
    attrs=git(ROOT,'check-attr','--cached','-z','text','eol','filter','--',*[f['public_path'] for f in files]).split(b'\0')
    rows=[tuple(x.decode() for x in attrs[i:i+3]) for i in range(0,len(attrs)-1,3)]
    require(all(value=='unset' for path,attr,value in rows if attr=='text'),'admitted namespace must disable text conversion')
    require(all(value in ('unspecified','unset') for path,attr,value in rows if attr=='filter'),'unexpected Git filter')
    receipt['git_attributes']=[{'path':path,'attribute':attr,'value':value} for path,attr,value in rows]
    receipt['attribute_explanation']='The admitted .gitattributes file contains * -text, disabling text normalization for all 40 copied files. Inherited eol values do not re-enable an unset text attribute. No additional attributes file or root change is needed.'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('copy','verify-index','verify-commit'),required=True)
    ap.add_argument('--run-id',required=True);ap.add_argument('--helper-commit',required=True)
    ap.add_argument('--candidate');a=ap.parse_args()
    require(re.fullmatch('[a-z0-9-]+',a.run_id),'invalid run id')
    output=HERE/'attempts'/a.run_id/'receipt.json'
    require(not output.parent.exists(),'attempt path already exists')
    output.parent.mkdir(parents=True)
    result={'schema':'eld-wp09-exact-publication/1','mode':a.mode,'run_id':a.run_id,'started_utc':utc(),
        'command':[sys.executable,*sys.argv],'python':sys.version,'checks':[],'status':'running',
        'regeneration':False,'inference':False,'original_source_mutation':False}
    try:
        files,original_tree=preflight(result,a.helper_commit)
        if a.mode=='copy':
            require(not DEST.exists(),'destination already exists; coordinator disposition required')
            require(not txt(ROOT,'diff','--name-only') and not txt(ROOT,'diff','--cached','--name-only'),'tracked working/index changes before copy')
            result['destination_absent_before_copy']=True
            DEST.mkdir(parents=True)
            for f in files:
                path=ROOT/f['public_path'];path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as handle:handle.write((SEALED/f['sealed_relative_path']).read_bytes())
            verify_disk(files);result['checks'].append('exclusive copy of exactly 40 admitted files; checked-out byte parity')
        elif a.mode=='verify-index':
            verify_disk(files);verify_attributes(files,result)
            staged=txt(ROOT,'diff','--cached','--name-only').splitlines()
            require(set(staged)=={f['public_path'] for f in files},'staged scope must be exactly 40 corpus files')
            for f in files:
                data=git(ROOT,'show',':'+f['public_path'])
                require(len(data)==f['bytes'] and sha(data)==f['sha256'],'staged blob normalization '+f['public_path'])
            result['checks'].append('all 40 checked-out and staged Git blobs match admitted hashes; attributes verified')
        else:
            require(a.candidate is not None and txt(ROOT,'rev-parse','HEAD')==a.candidate,'candidate must be exact current commit')
            verify_disk(files);verify_attributes(files,result)
            current=tree(ROOT,a.candidate)
            unchanged=[p for p in original_tree if current.get(p)==original_tree[p]]
            require(len(unchanged)==len(original_tree),'preexisting authority path/object changed')
            changes=sorted(set(current)-set(original_tree))
            require(all(p.startswith(PREFIX) or p.startswith('docs/evaluation/WP-0009/unseal/') for p in changes),'unowned candidate additions')
            require({p for p in current if p.startswith(PREFIX)}=={f['public_path'] for f in files},'committed corpus path set')
            for f in files:
                data=git(ROOT,'show',a.candidate+':'+f['public_path'])
                require(len(data)==f['bytes'] and sha(data)==f['sha256'],'committed byte mismatch')
                require(current[f['public_path']]['git_blob']==f['sealed_git_blob'],'original/published Git blob identity')
            result.update({'candidate_commit':a.candidate,'authority_input_files_unchanged':len(unchanged),
                           'candidate_added_paths':changes,'all_40_original_and_public_git_blobs_equal':True})
            result['checks'].append('all 40 committed blobs equal original blobs; complete authority-input preservation')
        require(not txt(SEALED,'status','--porcelain') and txt(SEALED,'rev-parse','HEAD')==SEALED_COMMIT,'sealed state changed during operation')
        result['status']='passed'
    except Exception:
        result['status']='failed';result['failure']=traceback.format_exc()
    finally:
        result['ended_utc']=utc()
        with output.open('x',encoding='utf-8',newline='\n') as handle:json.dump(result,handle,indent=2);handle.write('\n')
        print(json.dumps({'status':result['status'],'mode':a.mode,'receipt':str(output),'checks':len(result['checks'])}))
    return 0 if result['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
