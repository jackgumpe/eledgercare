"""Focused dev checks for the new reviewer helper; never inspects the active B0 run."""
import copy,datetime,json,sys,traceback
from pathlib import Path
OWN=Path(__file__).resolve().parent
sys.path.insert(0,str(OWN))
import reproduce as r
from corpus import fixtures

def main():
    out=Path(sys.argv[1]);require_clean=not r.git('status','--porcelain').strip()
    r.require(require_clean,'Freeze helper before decisive preparation checks')
    allowed={str((r.ROOT/f[k]).resolve()).casefold() for f in fixtures() if f['split']=='dev' for k in ('file_path','expected_ground_truth_path','source_record_path')};seen=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],str):
            p=Path(args[0]).resolve()
            if 'evaluation/synthetic/' in p.as_posix():
                if str(p).casefold() not in allowed:raise PermissionError('Preparation permits dev content only')
                seen.append(str(p))
        if event=='import' and str(args[0]).split('.')[0] in ('torch','transformers'):raise PermissionError('No model imports')
    sys.addaudithook(audit)
    evidence=r.GitBlobs('e22c6730d19a6d616f0e7afb00b9416635799c16')
    q0='qualification/q0/harness/evidence/004-gpu-trial/9e73ef86/run-20261115T202627Z-eb5bf7da/evidence'
    p=r.protocol();calls=[];blobs={};root='CPU-PREPARATION-ONLY';results=[]
    # Three complete synthetic call records reuse existing historical dev Q0 bytes.
    # This repackaging is test input, not a B0 result or any runtime authorization.
    for n,item in enumerate(r.schedule(p,'dev')):
        status='completed' if n<3 else 'failed' if n==3 else 'not_run_after_failure'
        call={**item,'status':status,'observation':None};calls.append(call)
        if n>=3:continue
        family='F07' if item['fixture_id'].startswith('SYN-MP') else 'F01'
        obs=json.loads(evidence(q0+'/'+family+'.warm1.observation.json'))
        obs.update(label=item['fixture_id']+'.'+item['kind'],kind=item['kind'],excluded_from_warm_statistics=item['excluded'],repeat=1)
        path='evidence/'+obs['label']+'.observation.json';call['observation']=path
        blobs[root+'/'+path]=json.dumps(obs).encode()
        for key in ('raw_output','token_ids_file'):
            blobs[root+'/evidence/'+obs[key]['name']]=evidence(q0+'/'+obs[key]['name'])
    def check(name,fn):
        try:detail=fn();results.append({'name':name,'passed':True,'detail':detail})
        except Exception as e:results.append({'name':name,'passed':False,'error':repr(e),'traceback':traceback.format_exc()})
    result={'calls':calls};reproduced,checks=r.reproduce(blobs.__getitem__,root,result,p,'dev')
    def dev_score():
        old=json.loads(evidence('docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev/F01.score.json'));old.pop('source');old['raw_sha256']=r.sha(evidence(q0+'/F01.warm1.raw.txt'))
        r.require(reproduced['scores'][0]==old,'Historical dev score mismatch')
        r.require(len(reproduced['scores'])==13 and checks['completion_counts']=={'completed':1,'failed':1,'not_run_after_failure':11},'Incomplete measured accounting')
        return {'full_historical_F01_score_equal':True,'measured_documents':13,'completion_counts':checks['completion_counts']}
    check('historical_dev_raw_score_and_complete_failed_schedule',dev_score)
    def refusals():
        cases=[calls[:-1],calls+[calls[-1]],calls[::-1]];count=0
        for bad in cases:
            try:r.validate_schedule(bad,p,'dev')
            except ValueError:count+=1
        r.require(count==3,'Incomplete/duplicate/reordered schedule accepted');return count
    check('missing_duplicate_and_reordered_plan_refusals',refusals)
    def raw_integrity():
        obs=json.loads(blobs[root+'/'+calls[0]['observation']]);mutated=dict(blobs);key=root+'/evidence/'+obs['raw_output']['name'];mutated[key]+=b'x'
        try:r.retained(mutated.__getitem__,root+'/evidence',obs['raw_output'])
        except ValueError:return 'Mutated raw bytes refused before parsing'
        raise AssertionError('Mutated raw accepted')
    check('raw_digest_length_refusal',raw_integrity)
    def numeric_refusals():
        bad=copy.deepcopy(reproduced['summary']);bad['dev']['families']['F01']['metrics']['fields']['mean']+=0.1
        try:r.independent_means(reproduced['scores'],bad)
        except ValueError:return 'Altered family mean refused'
        raise AssertionError('Altered mean accepted')
    check('independent_aggregate_check_detects_changed_mean',numeric_refusals)
    def gate():
        try:r.split_gate('eval_holdout',False)
        except PermissionError:return 'Held-out split refused before any evidence read'
        raise AssertionError('Held-out split permitted')
    check('pre_read_heldout_permission_gate',gate)
    original_release={'owner':'author','source_commit':r.SOURCE,'source_tree':r.TREE,'accepted_review_commit':r.REVIEW,'accepted_review_path':r.REVIEW_PATH,'executing_head':r.REVIEW,'protocol_sha256':r.sha((r.HERE/'protocol.json').read_bytes()),'mapping_sha256':r.sha((r.HERE/'mapping.json').read_bytes()),'lock_sha256':p['dependency_lock_sha256']}
    plan={'release':original_release,'executing_head':r.REVIEW,'authority_commit':'CPU-PREP-NOT-A-LEASE','release_path':'CPU-PREP-NOT-A-LEASE'}
    frozen_result={'release':original_release,'executing_head':r.REVIEW}
    def original_binding():
        r.validate_original(original_release,frozen_result,plan,'CPU-PREP-NOT-A-LEASE','CPU-PREP-NOT-A-LEASE',p)
        bad=copy.deepcopy(frozen_result);bad['executing_head']='0'*40
        try:r.validate_original(original_release,bad,plan,'CPU-PREP-NOT-A-LEASE','CPU-PREP-NOT-A-LEASE',p)
        except ValueError:return 'Pure source/release/result binding accepts consistent fixture and rejects changed original HEAD'
        raise AssertionError('Changed HEAD accepted')
    check('pure_original_binding_identity_check',original_binding)
    final={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'helper_execution_head':r.git('rev-parse','HEAD').decode().strip(),'accepted_source':r.SOURCE,'preparation_authority':'9926d3b1153dcb417d401362e7d93ba9cbece601','python':sys.version,'checks':results,'passed':all(x['passed'] for x in results),'immutable_dev_artifacts_read':evidence.reads,'synthetic_content_paths':sorted(set(seen)),'model_modules':[m for m in sys.modules if m in ('torch','transformers')],'limitations':['No completed new B0 evidence exists in this test.','Synthetic schedule/release-shaped fixtures are clearly test-only.','No active run path, GPU, model, held-out content or author CLI authority was used.']}
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(final,f,indent=2);f.write('\n')
    print(json.dumps({'passed':final['passed'],'checks':len(results),'dev_content_paths':len(set(seen)),'output':str(out)}))
    return int(not final['passed'])
if __name__=='__main__':raise SystemExit(main())
