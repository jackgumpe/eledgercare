"""Exact WP13 admitted-byte publication after explicit root unseal. No regeneration.

Each mode retains an exclusive receipt. Only the custodian's sealed repository is
read; reviewer-owned private evidence is neither opened nor mutated.
"""
from __future__ import annotations
import argparse,datetime,hashlib,io,json,re,subprocess,sys,traceback
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[4]
SEALED=Path('C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/sealed')
HERE=ROOT/'docs/evaluation/WP-0013/publication'
PREFIX='evaluation/mapping_v2/'
DEST=ROOT/PREFIX
AUTHORITY='e5c926890ae8c275a8782c8325a15b7d391f23ec'
SOURCE='c0a1af638e807803b6014b3a93ecb7f9946ce6e1'
SOURCE_TREE='4477104eb2a3c73f496ef451cef9578f54d96518'
REVIEW='bb2a731ef6969a6f87508cad4960ca5dc2bafeb1'
ADMISSION='321afab409989a1eafcb1b43f433d784d2658711'
CANONICAL='0adccecc3328fb367e8c8d79d7d29970c309f889'
SEALED_COMMIT='6bed5df03e161960ca088d4b4bb9417da11fee6a'
CORE_TREE='cca906b35b99362d5b4d0b842dd9981e9481229c'
CORE_SHA='91c4a38adeef4ceb2c3fb399eac525e141e4821e9a7dcdf0fb82803e89b86319'
INVENTORY='inventory/final-r1.json'
INVENTORY_SHA='bfb7b818ced3992a28bff3dd7968ac5003b3c47367589817b99c5c2d74039ea0'
INVENTORY_RECEIPT='evidence/inventory-final-001/receipt.json'
INVENTORY_RECEIPT_SHA='c5e631ffa637d891113cd9d7101774f5c0e0867ca2772dc4f0e5a8f82b144bad'
RESERVATION='docs/evaluation/WP-0013/reservation/reservation.json'
RESERVATION_COMMIT='b50b2a3bc22927890c8f391943f2a3fe9168d0da'
RESERVATION_SHA='533f4be35fb89efd9e288c0470201457b5ab32373eab3112ae283b42febcfea5'
CATALOG_SHA='35a99a213b80476747c7a136a4109ac45bc7944c77b0a3dcf0f348f107dd37a2'
PROTOCOL_SHA='aa0d8f183f9f0161c6e47b56a6f2cd844d6ad3f31e772b9761aa0ad618f6a372'

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
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode()
    with path.open('xb') as stream:stream.write(data)
    return data
def custody():
    require(text(SEALED,'rev-parse','HEAD')==SEALED_COMMIT and text(SEALED,'branch','--show-current')=='sealed/wp-0013','original custody identity changed')
    require(not text(SEALED,'status','--porcelain') and not text(SEALED,'remote'),'original custody must remain clean/no remote')

def preflight(receipt,helper):
    require(ROOT.resolve()==Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-custodian').resolve(),'wrong owned public root')
    require(text(ROOT,'branch','--show-current')=='evaluation/wp-0013-vocabulary-families','wrong public branch')
    DEST.resolve().relative_to(ROOT.resolve())
    require(git(ROOT,'show',helper+':docs/evaluation/WP-0013/publication/publish.py')==Path(__file__).read_bytes(),'helper differs from frozen commit')
    git(ROOT,'merge-base','--is-ancestor',AUTHORITY,'HEAD')
    for ancestor in (SOURCE,REVIEW,ADMISSION,CANONICAL,RESERVATION_COMMIT):git(ROOT,'merge-base','--is-ancestor',ancestor,AUTHORITY)
    release_bytes=git(ROOT,'show',AUTHORITY+':docs/coordination/WP-0013/unseal.json');release=json.loads(release_bytes)
    for key,value in {'schema':'eld-mapping-v2-unseal/1','allow_content':True,'source_commit':SOURCE,'source_tree':SOURCE_TREE,'source_review_commit':REVIEW,
      'admission_review_commit':ADMISSION,'reservation_sha256':RESERVATION_SHA,'sealed_final_commit':SEALED_COMMIT,'sealed_file_count':120,'publication_prefix':PREFIX,'runtime_authorized':False}.items():
        require(release[key]==value,'unseal mismatch '+key)
    for role,commit in (('source_review',REVIEW),('admission_review',ADMISSION)):
        data=git(ROOT,'show',commit+':'+release[role+'_path'])
        require(sha(data)==release[role+'_sha256'] and data==git(ROOT,'show',AUTHORITY+':'+release[role+'_path']),'independent review binding')
    require(text(ROOT,'rev-parse',SOURCE+':qualification/mapping_v2')==text(ROOT,'rev-parse',AUTHORITY+':qualification/mapping_v2')==SOURCE_TREE,'accepted implementation tree')
    for name,digest in (('catalog.json',CATALOG_SHA),('protocol.json',PROTOCOL_SHA)):
        require(sha(git(ROOT,'show',SOURCE+':qualification/mapping_v2/protocol/'+name))==digest,'accepted catalog/protocol bytes')
    reservation_bytes=git(ROOT,'show',AUTHORITY+':'+RESERVATION)
    require(sha(reservation_bytes)==RESERVATION_SHA and reservation_bytes==git(ROOT,'show',RESERVATION_COMMIT+':'+RESERVATION),'immutable reservation')
    reservation=json.loads(reservation_bytes);custody()
    inventory_bytes=(SEALED/INVENTORY).read_bytes();execution_bytes=(SEALED/INVENTORY_RECEIPT).read_bytes()
    require(sha(inventory_bytes)==INVENTORY_SHA and sha(execution_bytes)==INVENTORY_RECEIPT_SHA,'admitted inventory/receipt identity')
    inventory=json.loads(inventory_bytes);require(inventory['file_count']==118==len(inventory['files']),'118 inventory entries')
    entries={x['path']:x for x in inventory['files']}
    entries[INVENTORY]={'bytes':len(inventory_bytes),'sha256':INVENTORY_SHA}
    entries[INVENTORY_RECEIPT]={'bytes':len(execution_bytes),'sha256':INVENTORY_RECEIPT_SHA}
    original=tree(SEALED,SEALED_COMMIT);require(len(original)==120 and set(original)==set(entries),'120 complete admitted tracked paths')
    files=[]
    for path in sorted(entries):
        source=(SEALED/path).resolve();source.relative_to(SEALED.resolve())
        require(source.is_file() and not source.is_symlink() and '.git' not in Path(path).parts,'invalid original tracked path')
        data=source.read_bytes();bound=entries[path]
        require(data==git(SEALED,'show',SEALED_COMMIT+':'+path) and len(data)==bound['bytes'] and sha(data)==bound['sha256'],'original disk/Git/inventory identity '+path)
        files.append({'sealed_relative_path':path,'public_path':PREFIX+path,'bytes':len(data),'sha256':sha(data),'sealed_git_blob':original[path]['git_blob'],'mode':original[path]['mode']})
    require(sum(f['bytes'] for f in files)==reservation['complete_private_bytes']==5270705,'complete admitted byte count')
    require(text(SEALED,'rev-parse',SEALED_COMMIT+':corpus/r1')==CORE_TREE and sha((SEALED/'corpus/r1/manifest.json').read_bytes())==CORE_SHA,'core tree/manifest binding')
    roles=0;pdfs=[]
    require(len(reservation['fixtures'])==12,'twelve fixtures')
    by_public={f['public_path']:f for f in files}
    for fixture in reservation['fixtures']:
        require({a['role'] for a in fixture['artifacts']}=={'pdf','expected','reference','policy'},'four artifact roles')
        for artifact in fixture['artifacts']:
            bound=by_public[artifact['path']];require(bound['bytes']==artifact['bytes'] and bound['sha256']==artifact['sha256'],'reserved artifact identity');roles+=1
            if artifact['role']=='pdf':
                pages=len(PdfReader(io.BytesIO((SEALED/bound['sealed_relative_path']).read_bytes()),strict=True).pages)
                require(pages==fixture['page_count']==1,'actual one-page PDF count');pdfs.append({k:fixture[k] for k in ('fixture_id','family_id','case','page_count')})
    require(roles==48 and len(pdfs)==12 and len({f['family_id'] for f in pdfs})==4,'bounded descriptor/family/page counts')
    prior=tree(ROOT,AUTHORITY)
    receipt.update({'authority_commit':AUTHORITY,'unseal_sha256':sha(release_bytes),'unseal':release,'helper_commit':helper,'helper_sha256':sha(Path(__file__).read_bytes()),
      'sealed_commit':SEALED_COMMIT,'sealed_root_tree':text(SEALED,'rev-parse',SEALED_COMMIT+'^{tree}'),'inventory_sha256':INVENTORY_SHA,
      'inventory_execution_sha256':INVENTORY_RECEIPT_SHA,'core_tree':CORE_TREE,'core_manifest_sha256':CORE_SHA,'reservation_sha256':RESERVATION_SHA,
      'files':files,'source_file_count':120,'source_total_bytes':5270705,'reserved_artifacts':48,'pdfs':pdfs,'pages':12,'families':4,'authority_input_files':len(prior),
      'original_custody_clean_no_remote':True,'reviewer_private_evidence_accessed':False})
    receipt['checks'].extend(['exact root unseal and accepted implementation/review/admission/reservation bindings','frozen publication helper and immutable catalog/protocol',
      'clean no-remote original custody; all120 disk/Git/inventory identities','48 reserved role/path/hash descriptors; twelve actual one-page PDFs/four families'])
    return files,prior

def disk(files):
    actual={str(p.relative_to(ROOT)).replace('\\','/') for p in DEST.rglob('*') if p.is_file()}
    require(actual=={f['public_path'] for f in files},'destination exact path set')
    require(not any(p.name=='.git' for p in DEST.rglob('*')),'private Git database copied')
    for item in files:
        target=ROOT/item['public_path'];require(not target.is_symlink(),'public symlink')
        data=target.read_bytes();require(len(data)==item['bytes'] and sha(data)==item['sha256'],'public disk identity')

def attributes(files,receipt):
    values=git(ROOT,'check-attr','--cached','-z','text','eol','filter','--',*[f['public_path'] for f in files]).split(b'\0')
    attrs=[tuple(x.decode() for x in values[i:i+3]) for i in range(0,len(values)-1,3)]
    require(all(v=='unset' for p,a,v in attrs if a=='text'),'text normalization enabled')
    require(all(v in ('unspecified','unset') for p,a,v in attrs if a=='filter'),'unexpected Git filter')
    receipt['attributes']=[{'path':p,'attribute':a,'value':v} for p,a,v in attrs]
    receipt['line_endings']='The original admitted .gitattributes (* -text) is copied unchanged as one of120 files. It disables inherited eol normalization; no root or copied-file edit is needed. Separate publication-doc attributes preserve new metadata bytes.'

def committed(files,prior,candidate,receipt):
    require(text(ROOT,'rev-parse','HEAD')==candidate,'candidate must be exact current HEAD')
    disk(files);attributes(files,receipt);current=tree(ROOT,candidate)
    require(all(current.get(p)==v for p,v in prior.items()),'preexisting authority input changed')
    added=sorted(set(current)-set(prior));require(all(p.startswith(PREFIX) or p.startswith('docs/evaluation/WP-0013/publication/') for p in added),'unowned addition')
    require({p for p in current if p.startswith(PREFIX)}=={f['public_path'] for f in files},'committed corpus path set')
    for f in files:
        data=git(ROOT,'show',candidate+':'+f['public_path'])
        require(len(data)==f['bytes'] and sha(data)==f['sha256'] and current[f['public_path']]['git_blob']==f['sealed_git_blob'] and current[f['public_path']]['mode']==f['mode'],'public/private committed byte/blob/mode mismatch')
    require(text(ROOT,'rev-parse',candidate+':evaluation/mapping_v2')==receipt['sealed_root_tree'],'entire published/admitted Git trees differ')
    receipt.update({'candidate_commit':candidate,'authority_input_files_unchanged':len(prior),'added_paths':added,'all120_private_public_blobs_modes_equal':True,'entire_private_public_namespace_tree_equal':True})
    return current,added

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('copy','verify-index','verify-commit','inventory'),required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--helper-commit',required=True);p.add_argument('--candidate');a=p.parse_args()
    require(bool(re.fullmatch('[a-z0-9-]+',a.run_id)),'invalid attempt ID');out=HERE/'attempts'/a.run_id/'receipt.json'
    require(not out.parent.exists(),'existing attempt must be retained');out.parent.mkdir(parents=True)
    receipt={'schema':'eld-wp13-exact-publication/1','mode':a.mode,'started_utc':utc(),'command':[sys.executable,*sys.argv],'python':sys.version,'checks':[],
      'status':'running','regeneration':False,'rendering':False,'mapper_execution':False,'model_inference':False,'reviewer_private_evidence_accessed':False}
    try:
        files,prior=preflight(receipt,a.helper_commit)
        if a.mode=='copy':
            require(not DEST.exists(),'unexpected existing destination; preserve and obtain coordinator disposition')
            require(not text(ROOT,'diff','--name-only') and not text(ROOT,'diff','--cached','--name-only'),'tracked/index edits before copy')
            receipt['destination_absent_before_copy']=True;DEST.mkdir(parents=True)
            for f in files:write(ROOT/f['public_path'],(SEALED/f['sealed_relative_path']).read_bytes())
            disk(files);write(HERE/'authority-tree.json',{'authority':AUTHORITY,'file_count':len(prior),'files':[{'path':p,**v} for p,v in sorted(prior.items())]})
            receipt['checks'].append('exclusive120-file copy, full public disk identity and protected-authority path inventory')
        elif a.mode=='verify-index':
            disk(files);attributes(files,receipt)
            require(set(text(ROOT,'diff','--cached','--name-only').splitlines())=={f['public_path'] for f in files},'staged scope must be exactly120 corpus files')
            for f in files:
                data=git(ROOT,'show',':'+f['public_path']);require(len(data)==f['bytes'] and sha(data)==f['sha256'],'staged byte mismatch')
            receipt['checks'].append('all120 exact staged blobs and byte-preserving attribute semantics')
        else:
            require(a.candidate is not None,'candidate required');current,added=committed(files,prior,a.candidate,receipt)
            receipt['checks'].append('all120 committed blobs/modes, entire namespace tree and complete authority preservation')
            if a.mode=='verify-commit':
                manifest={'schema':'eld-wp13-byte-copy-manifest/1','authority_commit':AUTHORITY,'corpus_commit':a.candidate,'sealed_commit':SEALED_COMMIT,
                  'private_public_tree':receipt['sealed_root_tree'],'file_count':120,'total_bytes':5270705,'files':files,'reservation_sha256':RESERVATION_SHA,'reserved_artifacts':48,
                  'inventory_sha256':INVENTORY_SHA,'core_manifest_sha256':CORE_SHA,'unchanged_authority_paths':len(prior),'regeneration':False}
                data=write(HERE/'byte-copy-manifest.json',manifest);receipt['byte_copy_manifest_sha256']=sha(data)
            else:
                entries=[]
                for path in added:
                    data=git(ROOT,'show',a.candidate+':'+path);require(data==(ROOT/path).read_bytes(),'publication metadata working/Git bytes differ')
                    entries.append({'path':path,'bytes':len(data),'sha256':sha(data),**current[path],'role':'admitted_corpus' if path.startswith(PREFIX) else 'publication_helper_or_evidence'})
                inventory={'schema':'eld-wp13-publication-inventory/1','authority_commit':AUTHORITY,'source_commit':a.candidate,'file_count':len(entries),'total_bytes':sum(e['bytes'] for e in entries),
                  'files':entries,'admitted_corpus_files':120,'authority_input_files_preserved':len(prior),'exclusions':['this subsequently committed inventory','this inventory attempt receipt']}
                data=write(HERE/'publication-inventory.json',inventory);receipt.update(publication_inventory_sha256=sha(data),publication_inventory_entries=len(entries))
                receipt['checks'].append('complete committed/working corpus and metadata inventory')
        custody();receipt['status']='passed'
    except Exception:receipt.update(status='failed',failure=traceback.format_exc())
    finally:
        receipt['ended_utc']=utc();write(out,receipt)
        print(json.dumps({'status':receipt['status'],'mode':a.mode,'checks':len(receipt['checks']),'receipt':str(out)}))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
