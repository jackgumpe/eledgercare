"""CPU-only exact-byte collection and independent published-metadata verification."""
from pathlib import Path
import argparse,datetime,json,sys,traceback
sys.path.insert(0,str(Path(__file__).resolve().parent/'preparation'))
import compare_published as c
ROOT=c.ROOT
HERE=Path(__file__).resolve().parent
EVIDENCE=ROOT/'docs/evidence/WP-0009/eld-mapping-reviewer/008/publication-attempt-2'
RUN=Path('C:/Users/jackg/eLedgerCare-Mapping/WP-0009/reviewer/runs/reviewer/20261116T211537Z-074ec88b')
SCRATCH=ROOT/'.scratch/wp0009-reviewer/runtime008-attempt-1'
BASE='69f7a79677b43228869d7c35bb5fb6d3e12e9291'
AUTHOR='73b5c5d3ce123adc33ba0397dcc74029208606c5'
AFTER='2314a32ca219116de11f2d4120afaf2133a87fec'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def identity(data):return {'bytes':len(data),'sha256':c.sha(data)}
def collect():
    c.require(c.load((RUN/'run-result.json').read_bytes())['failure'] is None,'Run failed; preserve and reconcile first')
    c.require(c.load((SCRATCH/'supervisor-tool-outcome.json').read_bytes())['supervisor_exit_code']==0,'Actual supervisor exit missing')
    copies=[];excluded=[]
    def copy(data,target,origin):
        target=EVIDENCE/target;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
        c.require(target.read_bytes()==data,'Copy mismatch')
        copies.append({'origin':origin,'published':target.relative_to(ROOT).as_posix(),**identity(data)})
    for path in sorted(RUN.rglob('*')):
        c.require(not path.is_symlink(),'Unexpected runtime symlink')
        if not path.is_file():continue
        rel=path.relative_to(RUN).as_posix();data=path.read_bytes()
        if '/' not in rel or rel.startswith('evidence/'):
            c.require(path.suffix in ('.json','.jsonl','.txt'),'Unexpected retained extension')
            copy(data,'run/'+rel,str(path))
        else:excluded.append({'path':rel,**identity(data),'reason':'task-local runtime cache; retained externally, not copied'})
    for name in ('launch.json','supervisor-tool.log','supervisor-tool-outcome.json','score-run-outcome.json','cleanup-observation.json','author-comparison-attempt-1.log'):
        copy((SCRATCH/name).read_bytes(),'launch/'+name,str(SCRATCH/name))
    copy((SCRATCH/'scores.json').read_bytes(),'scores.json',str(SCRATCH/'scores.json'))
    for rev,prefix in [(AFTER,'docs/coordination/WP-0009/reviewer-after/')]:
        for path in c.git('ls-tree','-r','--name-only',rev,'--',prefix).decode().splitlines():
            copy(c.git('show',rev+':'+path),'bindings/'+Path(path).name,rev+':'+path)
    write(EVIDENCE/'collection.json',{'helper_commit':c.git('rev-parse','HEAD').decode().strip(),'run':str(RUN),'copies':copies,'copy_count':len(copies),'absent_output_log':{'path':'score-run.log','reason':'Tee-Object created no file because score-run emitted no terminal output; actual exit0 receipt and scores retained'},'prior_collection_failure':'collection-attempt-1.json; partial publication attempt-1 retained unchanged','copied_bytes':sum(x['bytes'] for x in copies),'excluded_cache_files':excluded,'cache_file_count':len(excluded),'cache_bytes':sum(x['bytes'] for x in excluded),'empty_directories':[p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_dir() and not any(p.iterdir())]})
    return {'copies':len(copies),'excluded_cache_files':len(excluded)}

def metadata(spec):
    pub=c.GitReader(spec['publication']);prefix=spec['run_prefix']
    def read(name):return c.load(pub.read(prefix+'/'+name))
    p=c.protocol();pre=read('evidence/preflight.json');load=read('evidence/load.json');result=read('run-result.json');plan=read('plan.json')
    manifest=c.load((ROOT/p['model_manifest_path']).read_bytes())
    model={x['path']:x for x in pre['model']['files']};expected={x['path']:x for x in manifest['files']}
    c.require(len(model)==len(pre['model']['files'])==len(expected)==18 and model.keys()==expected.keys(),'Model object set mismatch')
    for name,x in expected.items():
        got=model[name];kind='sha256' if x['digest_kind']=='lfs_sha256' else x['digest_kind'];c.require(got['ok'] is True and got['size']==x['size'] and got[kind]==x[kind],'Model size/digest mismatch: '+name)
    notices={x['path']:x for x in pre['notice']['notices']}
    c.require(set(notices)=={x['path'] for x in manifest['notices']},'Notice set mismatch')
    for x in manifest['notices']:
        got=notices[x['path']];kind=x['digest_kind'];c.require(got['ok'] is True and got['size']==x['size'] and got[kind]==x[kind],'Notice digest mismatch')
    mods=load['module_cache']['modules'];c.require(len(mods)==8 and len({m['file'] for m in mods})==8,'Loaded model module set mismatch')
    for m in mods:c.require(m['identical'] is True and m['cache_sha256']==m['model_sha256']==model[m['file']]['sha256'],'Loaded model cache digest mismatch')
    c.require(pre['renderer']['distribution_version']==pre['renderer']['PYPDFIUM_INFO']==p['renderer']['version'],'pypdfium2 version mismatch')
    c.require(pre['renderer']['PDFIUM_INFO'].split('@')[0]==p['renderer']['pdfium_version'],'PDFium version mismatch')
    sys.path.insert(0,str(ROOT/'qualification/q0/harness'))
    from q0harness.locks import validate_lock,git_blob_reader
    packages=validate_lock(c.load((ROOT/p['dependency_lock_path']).read_bytes()),git_blob_reader(ROOT));wheels=pre['wheels']['wheels'];by={x['filename']:x for x in packages.values()}
    c.require(len(wheels)==len(by)==32 and {x['wheel'] for x in wheels}==by.keys(),'Wheel set mismatch')
    for w in wheels:
        e=by[w['wheel']];c.require(w['sha256']==e['effective_sha256'] and w['size']==e['size'] and w['kind']==e['effective_kind'],'Wheel identity mismatch')
        c.require(w['payload_ok'] is True and w['metadata']['ok'] is True and w['metadata']['requires_match'] is True,'Wheel payload/metadata failure')
        if e.get('published_metadata_sha256'):c.require(w['metadata']['metadata_sha256']==e['published_metadata_sha256'],'Published wheel metadata mismatch')
    c.require(pre['installed']['distributions']==33 and set(pre['installed']['forbidden_absent_find_spec_none'])=={'flash_attn','xformers','triton'} and pre['installed']['triton_policy']=='absent','Installed gate differs')
    c.require(result['failure'] is None and result['supervisor_error'] is None and not result['secondary_errors'] and not result['finalization_errors'],'Runtime finalization failure')
    c.require(result['child_returncode']==0 and result['observed_child_exit'] is True,'Child did not exit successfully')
    checks=result['gpu_process_checks'];c.require(checks and all(x['expected_device_observed'] is True for x in checks),'GPU device observation failure')
    # Exact final tool and coordinator ownership receipts are independently inspected,
    # rather than deriving supervisor success or process cleanup from child returncode.
    return {'owner':spec['owner'],'model_objects':len(model),'model_objects_manifest_exact':True,'notices_manifest_exact':True,'loaded_module_copies':len(mods),'wheel_payloads_and_metadata':len(wheels),'renderer':pre['renderer'],'installed_gate':pre['installed'],'installed_limit':'Preflight stores gate result/count, not the full installed distribution listing; acceptance also relies on immutable worker verification code.','supervisor_pid':plan['supervisor_pid'],'job_name':plan['job_name'],'worker_pid':pre['worker_pid'],'child_launcher_pid':result['child_launcher_pid'],'gpu_observers':len(result['observers']),'gpu_observer_returncodes':[x['returncode'] for x in result['observers']],'elapsed_s':result['elapsed_s'],'free_bytes_after':result['free_bytes_after'],'owned_bytes_after':result['owned_bytes_after'],'model_sha256_by_path':{k:v['sha256'] for k,v in model.items()},'input_inventory':list(pub.inputs.values())}

def trees(rev):
    result={}
    for line in c.git('ls-tree','-r',rev).decode().splitlines():
        info,path=line.split('\t',1);result[path]=info
    return result

def inventory(deliverable):
    base=trees(BASE);now=trees(deliverable);c.require(all(now.get(k)==v for k,v in base.items()),'Previously tracked content changed')
    added=sorted(set(now)-set(base));prefixes=('docs/reviews/WP-0009/eld-mapping-reviewer/008/','docs/evidence/WP-0009/eld-mapping-reviewer/008/')
    c.require(all(x.startswith(prefixes) for x in added),'Unowned path changed')
    entries=[]
    for path in added:
        data=c.git('show',deliverable+':'+path);entries.append({'path':path,'git_blob':now[path].split()[-1],**identity(data)})
    collection=c.load((EVIDENCE/'collection.json').read_bytes())
    for x in collection['copies']:
        data=c.git('show',deliverable+':'+x['published']);c.require(identity(data)=={k:x[k] for k in ('bytes','sha256')},'Published copied bytes changed')
        origin=x['origin'];original=c.git('show',origin) if not Path(origin).is_absolute() else Path(origin).read_bytes()
        c.require(data==original,'Original evidence changed')
    for x in collection['excluded_cache_files']:c.require(identity((RUN/x['path']).read_bytes())=={k:x[k] for k in ('bytes','sha256')},'Retained cache changed')
    return {'base':BASE,'deliverable':deliverable,'entries':entries,'added_paths':len(entries),'unchanged_base_paths':len(base),'original_published_copies_reverified':len(collection['copies']),'external_cache_files_reverified':len(collection['excluded_cache_files'])}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['collect','metadata','inventory']);ap.add_argument('--spec',type=Path);ap.add_argument('--deliverable');ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    result={'status':'FAILED','helper_head':c.git('rev-parse','HEAD').decode().strip(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        result['result']=collect() if a.command=='collect' else metadata(c.load(a.spec.read_bytes())) if a.command=='metadata' else inventory(a.deliverable)
        result['status']='PASS';code=0
    except Exception:result['failure']=traceback.format_exc();code=1
    write(a.out,result);print(json.dumps({'status':result['status'],'output':str(a.out)}));return code
if __name__=='__main__':raise SystemExit(main())
