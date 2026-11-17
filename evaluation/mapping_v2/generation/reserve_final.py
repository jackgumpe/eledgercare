"""Complete private inventory and nonrevealing public reservation; no content disclosure."""
from __future__ import annotations
import argparse,datetime,hashlib,json,subprocess,sys,traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-custodian')
AUTHORITY='48ffd871eec58dac841e12a40c9d242aece2608c'
DOCS=PUBLIC/'docs/evaluation/WP-0013/reservation'
INVENTORY='inventory/final-r1.json'
INVENTORY_RECEIPT='evidence/inventory-final-001/receipt.json'

def sha(data):return hashlib.sha256(data).hexdigest()
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
def require(ok,message):
    if not ok:raise AssertionError(message)
def load(path):return json.loads(path.read_bytes())
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode()
    with path.open('xb') as f:f.write(data)
    return data
def tree(repo,ref):
    result={}
    for record in git(repo,'ls-tree','-r','-z',ref).split(b'\0'):
        if record:
            metadata,path=record.split(b'\t',1);mode,kind,oid=metadata.decode().split()
            result[path.decode()]={'mode':mode,'type':kind,'git_blob':oid}
    return result

def preflight(candidate,helper):
    require(ROOT.resolve()==Path('C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/sealed').resolve(),'wrong private root')
    require(git(ROOT,'rev-parse','HEAD').decode().strip()==candidate,'candidate must be exact HEAD')
    require(git(ROOT,'branch','--show-current').decode().strip()=='sealed/wp-0013' and not git(ROOT,'remote').strip(),'private branch/remote')
    require(not git(ROOT,'diff','--name-only').strip() and not git(ROOT,'diff','--cached','--name-only').strip(),'tracked private changes')
    require(git(ROOT,'show',helper+':generation/reserve_final.py')==Path(__file__).read_bytes(),'reservation helper differs from freeze')
    pins=load(ROOT/'provenance/final-source-pins.json')
    for item in pins['foundation_files']:
        data=(ROOT/item['path']).read_bytes();require(len(data)==item['bytes'] and sha(data)==item['sha256'],'foundation changed')
    manifest=load(ROOT/'corpus/r1/manifest.json')
    for entry in manifest['files']:
        data=(ROOT/'corpus/r1'/entry['path']).read_bytes();require(len(data)==entry['bytes'] and sha(data)==entry['sha256'],'frozen core changed')
    validation=load(ROOT/'evidence/validate-final-001/receipt.json');visual=load(ROOT/'evidence/validate-final-001/visual-inspection.json')
    require(validation['status']=='passed' and len(validation['checks'])==10 and validation['regenerated_equal_files']==85,'verification incomplete')
    require(visual['status']=='passed' and visual['actual_pages_inspected']==12 and not visual['independent_admission'],'author visual inspection binding')
    current=tree(ROOT,candidate)
    require(all(current.get(path)==entry for path,entry in tree(ROOT,pins['foundation_receipt']).items()),'old foundation Git objects changed')
    for path,entry in current.items():require((ROOT/path).read_bytes()==git(ROOT,'show',candidate+':'+path),'working/private Git bytes differ '+path)
    return pins,manifest,current

def inventory(candidate,helper):
    receipt_path=ROOT/INVENTORY_RECEIPT;require(not receipt_path.parent.exists(),'existing inventory attempt must remain')
    receipt_path.parent.mkdir(parents=True)
    receipt={'schema':'eld-wp13-final-inventory-execution/1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],
      'candidate':candidate,'helper_commit':helper,'status':'running'}
    try:
        pins,manifest,current=preflight(candidate,helper);files=[]
        for path,entry in sorted(current.items()):
            data=git(ROOT,'show',candidate+':'+path);files.append({'path':path,'bytes':len(data),'sha256':sha(data),**entry})
        obj={'schema':'eld-wp13-final-sealed-inventory/1','source_commit':candidate,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'files':files,
          'core_files':85,'foundation_files_preserved':12,'protocol_source':pins['protocol_source'],'protocol_review':pins['independent_protocol_review'],
          'core_manifest_sha256':sha((ROOT/'corpus/r1/manifest.json').read_bytes()),'exclusions':['this subsequently committed inventory','this inventory execution receipt','ignored scratch/cache and Git internals']}
        data=write(ROOT/INVENTORY,obj);receipt.update(status='passed',inventory_sha256=sha(data),inventory_bytes=len(data),inventoried_files=len(files),inventoried_bytes=obj['total_bytes'],foundation_files_preserved=12,all_working_git_bytes_equal=True)
    except Exception:receipt.update(status='failed',failure=traceback.format_exc())
    finally:
        receipt['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(receipt_path,receipt)
        print(json.dumps({k:receipt.get(k) for k in ('status','inventory_sha256','inventoried_files','inventoried_bytes')}))
    return 0 if receipt['status']=='passed' else 1

def publish(candidate,helper):
    pins,manifest,current=preflight(candidate,helper)
    require(not git(ROOT,'status','--porcelain').strip(),'public reservation needs clean final private receipt')
    inv=load(ROOT/INVENTORY);execution=load(ROOT/INVENTORY_RECEIPT)
    require(execution['status']=='passed' and sha((ROOT/INVENTORY).read_bytes())==execution['inventory_sha256'],'inventory receipt binding')
    require(set(current)=={f['path'] for f in inv['files']}|{INVENTORY,INVENTORY_RECEIPT},'complete final custody inventory scope')
    for entry in inv['files']:
        data=(ROOT/entry['path']).read_bytes();require(sha(data)==entry['sha256'] and len(data)==entry['bytes'] and current[entry['path']]['git_blob']==entry['git_blob'],'private inventory changed')
    require(git(PUBLIC,'rev-parse','HEAD').decode().strip()==AUTHORITY and git(PUBLIC,'branch','--show-current').decode().strip()=='evaluation/wp-0013-vocabulary-families','public authority/branch mismatch')
    require(not git(PUBLIC,'diff','--name-only').strip() and not git(PUBLIC,'diff','--cached','--name-only').strip(),'public tracked edits')
    paths=[DOCS/p for p in ('.gitattributes','reservation.json','README.md','verification.json')]
    require(all(not p.exists() for p in paths),'public reservation path exists; preserve it')
    fixtures=[]
    for item in manifest['fixtures']:
        artifacts=[{'role':a['role'],'path':'evaluation/mapping_v2/corpus/r1/'+a['path'],'bytes':a['bytes'],'sha256':a['sha256']} for a in item['artifacts'] if a['role'] in ('pdf','expected','reference','policy')]
        require(len(artifacts)==4,'four public artifact roles')
        fixtures.append({'fixture_id':item['fixture_id'],'family_id':item['family_id'],'case':item['case'],'page_count':1,'artifacts':artifacts})
    reservation={'schema':'eld-mapping-v2-reservation/1','status':'frozen_for_independent_admission_before_mapper_implementation','root_authority':AUTHORITY,
      'protocol_publication':pins['protocol_publication'],'protocol_review':pins['independent_protocol_review'],'protocol_source':pins['protocol_source'],'protocol_tree':pins['protocol_tree'],
      'catalog_sha256':pins['catalog_sha256'],'protocol_sha256':pins['protocol_sha256'],'foundation_publication':'51b02bf592c766334694f005939cff9b4400794f',
      'foundation_public_receipt_sha256':'b6bedcbc300c7e649091b24d406441873cebb34d2264c3dcde78062381ddbe99',
      'families':4,'documents':12,'pages':12,'cases':['supported','conflict','unsupported'],'sentinel':'WP13-F04-conflict-v0','core_files':85,'core_manifest_sha256':sha((ROOT/'corpus/r1/manifest.json').read_bytes()),
      'private_inventory':{'sha256':sha((ROOT/INVENTORY).read_bytes()),'bytes':(ROOT/INVENTORY).stat().st_size,'entries':inv['file_count'],'entries_bytes':inv['total_bytes']},
      'inventory_execution_receipt':{'sha256':sha((ROOT/INVENTORY_RECEIPT).read_bytes()),'bytes':(ROOT/INVENTORY_RECEIPT).stat().st_size},
      'complete_private_files':len(current),'complete_private_bytes':sum((ROOT/p).stat().st_size for p in current),'fixtures':fixtures,
      'custody':{'local_git':True,'clean':True,'no_remote':True,'exact_private_path_commit':'provided separately only to root and independent reviewer','procedural_not_os_access_denial':True},
      'author_checks':{'generation_first_attempt':'passed','validation_groups':10,'contract_cases':12,'paired_families':4,'regenerated_equal_files':85,'actual_visually_inspected_pages':12,'independent_admission':False},
      'limits':['Four independent families with three cases each; twelve documents are not twelve independent samples.','Public dictionary was frozen and known; this evaluates fresh documents and guards, not inference of unseen aliases.','No OCR/model output, mapper prediction, tuning, semantic task or normalization change was used to prepare these inputs.','Identifying contents, layouts, wording, truths and generation source remain sealed until explicit root unseal.'],
      'gates':{'canonical_003':'accepted independent corpus004','mapper_005':'root binding of accepted002 and this exact reservation','unseal':'accepted implementation006 plus explicit root release'}}
    readme='''# WP-0013 final sealed reservation

The [reservation](reservation.json) freezes twelve one-page cases across four independent new fictional families, each with supported, conflict and unsupported cases. It binds 48 PDF/expected/reference/policy descriptors and the complete private source/render/evidence inventory. Future artifact paths are reserved under `evaluation/mapping_v2/corpus/r1/`; no corpus content is published here.

The accepted public contract is author /001 `9b90528f4dbd0ea1ff61c86d0d4040decf178a0a`, independent /002 `bb66c7261339a1e5b36a826e949b1eb6f8d62cd8`, tested source `6207daf1dc9cbdd141d083ca2d8d1e7507c63b09`, released by root `48ffd871eec58dac841e12a40c9d242aece2608c`. Exact catalog/protocol hashes are in the reservation. The earlier [foundation receipt](foundation/receipt.json) remains unchanged.

Final generation, source validation and inventory were frozen before their decisive executions. All ten author verification groups passed first attempt: all twelve accepted-contract cases, four matched families, complete actual PDF text and reading order, faithful ideal-native reference structure, actual render equality and byte-identical regeneration of all 85 core files. Author visual inspection covered all twelve actual rendered pages. Original foundation facts, layouts and custody records remain intact. These author checks do not self-accept ground truth.

Known truth, ambiguous/unknown truth, explicit blank absence and required abstention remain separate under the accepted interface. Every expected row has a grounded known canonical row key. No OCR/model output, mapper prediction or unit repair was used to select or tune the corpus. Public metadata contains counts, hashes and fixed identifiers only. Exact private commit and location go separately only to root and independent reviewer; custody is procedural, not an OS access-denial guarantee.

Root must verify this reservation and bind independent admission /004. Canonical custodian /003 waits accepted /004. Mapper /005 requires root binding of accepted /002 and these frozen bytes. Contents stay sealed until independently accepted implementation /006 and explicit root unseal. No inference, GPU lease or corpus publication is released by this metadata. The future unseal must copy the admitted originals unchanged.
'''
    outputs={'.gitattributes':b'* -text\n','reservation.json':reservation,'README.md':readme.encode()};public_files=[]
    for name,value in outputs.items():
        data=write(DOCS/name,value);public_files.append({'path':str((DOCS/name).relative_to(PUBLIC)).replace('\\','/'),'bytes':len(data),'sha256':sha(data)})
    proof={'schema':'eld-wp13-public-reservation-verification/1','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed','authority_base':AUTHORITY,
      'authority_paths_preserved':len(tree(PUBLIC,AUTHORITY)),'frozen_private_helper_sha256':sha(Path(__file__).read_bytes()),'foundation_files_preserved':12,
      'core_files_verified':85,'public_descriptors_verified':48,'private_inventory_entries_verified':inv['file_count'],'complete_private_files_verified':len(current),
      'private_clean_no_remote':True,'all_private_working_git_bytes_equal':True,'metadata_files':public_files,'exclusions':['this later verification metadata file'],
      'private_identifying_content_disclosed':False,'exact_private_revision_binding':'sent separately to root and independent reviewer','canonical_report_written':False,'model_inference':False}
    write(DOCS/'verification.json',proof)
    print(json.dumps({'status':'passed','public_reservation_sha256':sha((DOCS/'reservation.json').read_bytes()),'private_files':len(current),'descriptors':48,'public_files':4}))
    return 0

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('inventory','publish-metadata'),required=True);p.add_argument('--candidate',required=True);p.add_argument('--helper-commit',required=True);a=p.parse_args()
    return inventory(a.candidate,a.helper_commit) if a.mode=='inventory' else publish(a.candidate,a.helper_commit)

if __name__=='__main__':raise SystemExit(main())
