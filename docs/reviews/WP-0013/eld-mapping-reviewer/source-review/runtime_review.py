"""Independent release/worker/score-run checks; all fresh reads replaced with old public examples."""
import contextlib,copy,datetime,json,sys,traceback
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_checks as r
from qualification.mapping_v2 import runtime,release,scoring
from qualification.mapping_v2.protocol.scoring import score_policy,summarize_policy
def execute(out,directory):
    p=r.protocol();checks=[]
    def check(name,fn):
        row={'name':name}
        try:row.update(status='PASS',evidence=fn())
        except BaseException:row.update(status='FAIL',failure=traceback.format_exc())
        checks.append(row)
    now=datetime.datetime.now(datetime.timezone.utc)
    def envelope(owner):
        proof={'commit':'4'*40,'path':'docs/coordination/WP-0013/proof.json','sha256':'5'*64}
        return {'schema':'eld-mapping-v2-release/1','owner':owner,'source_commit':r.SOURCE,'executing_head':'2'*40,'source_tree':r.TREE,
         'protocol_sha256':r.sha((r.ROOT/'qualification/mapping_v2/runtime_protocol.json').read_bytes()),
         **{k:p[k] for k in ('comparator_tree','mapping_v1_tree','coverage_v1_tree','q0_core_tree','accepted_protocol_sha256','accepted_catalog_sha256')},
         'reservation_sha256':p['public_reservation_sha256'],'corpus_commit':'6'*40,'runtime_root':p['runtime_roots'][owner],
         'issued_utc':(now-datetime.timedelta(seconds=1)).isoformat(),'expires_utc':(now+datetime.timedelta(minutes=30)).isoformat(),
         'schedule':release.schedule(p,owner),'source_review':{**proof,'path':p['source_review_path'],'decision':'accepted','reviewed_source_commit':r.SOURCE},
         'admission_review':{**proof,'path':p['admission_review_path'],'decision':'accepted','reviewed_reservation_sha256':p['public_reservation_sha256']},
         'unseal':{**proof,'path':'docs/coordination/WP-0013/unseal.json'},
         'lease':{'id':'REVIEW-CPU-ONLY','owner':owner,'gpu_uuid':p['gpu']['uuid'],'sole_lease':True,'scope':'sole_model_job','observations':[proof]},
         'torchvision_local_sha256_TOFU_accepted':True}
    def validate(e,owner='author',execution=True):
        return release.validate_release(e,p,owner,head='2'*40,source_tree=r.TREE,protocol_digest=e['protocol_sha256'],clean=True,now=now,execution=execution)
    def gate_variation(key):
        e=envelope('author')
        if key=='wrong_owner':e['owner']='reviewer'
        if key=='source_review_missing_acceptance':e['source_review']['decision']='pending'
        if key=='admission_wrong_reservation':e['admission_review']['reviewed_reservation_sha256']='0'*64
        if key=='lease_not_sole':e['lease']['sole_lease']=False
        if key=='lease_no_observation':e['lease']['observations']=[]
        if key=='expired':e['expires_utc']=(now-datetime.timedelta(milliseconds=1)).isoformat()
        if key=='future':e['issued_utc']=(now+datetime.timedelta(seconds=1)).isoformat()
        if key=='unbounded':e['expires_utc']=(now+datetime.timedelta(hours=7)).isoformat()
        if key=='unsafe_binding':e['unseal']['path']='docs/coordination/WP-0013/../bad.json'
        try:validate(e)
        except PermissionError as exc:return str(exc)
        raise AssertionError('Envelope unexpectedly accepted')
    for name in ('wrong_owner','source_review_missing_acceptance','admission_wrong_reservation','lease_not_sole','lease_no_observation','expired','future','unbounded','unsafe_binding'):
        check('envelope/'+name,lambda n=name:gate_variation(n))
    def expired_cpu():
        e=envelope('reviewer');e['expires_utc']=(now-datetime.timedelta(milliseconds=1)).isoformat()
        validate(e,'reviewer',False);return {'expired_release_cpu_scoring_allowed':True}
    check('expired_release_same_bound_cpu_scoring',expired_cpu)
    def worker_boundary(change):
        import winjob
        owner='reviewer';e=envelope(owner);root=directory/('worker-'+change);run=root/'runs'/owner/'CPU';run.mkdir(parents=True)
        e['runtime_root']=str(root.resolve())
        identity={'pid':111,'creation_filetime_100ns':123,'created_utc':'CPU fake only'}
        plan={'release':e,'calls':release.schedule(p,owner),'job_name':'Local\\eLedgerCare-MappingV2-CPU','supervisor_pid':111,'supervisor_identity':identity}
        if change=='identity':plan['supervisor_identity']={**identity,'creation_filetime_100ns':999}
        if change=='job':plan['job_name']='Local\\Other'
        if change=='schedule':plan['calls']=plan['calls'][:-1]
        r.write(run/'plan.json',plan)
        class Boundary(Exception):pass
        seen=[]
        with patch.object(winjob,'join',side_effect=lambda job:seen.append(job)),patch.object(runtime,'read_release',return_value=e),patch.object(runtime,'protocol',return_value=p),patch.object(runtime,'process_identity',side_effect=lambda pid:identity if pid==111 else {'pid':pid,'creation_filetime_100ns':456}),patch.object(runtime,'q0_imports',side_effect=Boundary('before model-import boundary')) as imports:
            try:runtime.worker('CPU','CPU',owner,run,'Local\\eLedgerCare-MappingV2-CPU')
            except Boundary:
                r.require(change=='valid','Invalid parent reached model-import boundary')
            except PermissionError as exc:
                r.require(change!='valid','Valid owned parent rejected '+str(exc));imports.assert_not_called()
            else:raise AssertionError('Worker escaped CPU boundary')
        return {'case':change,'joined_owned_fake_job':seen,'model_import_boundary_calls':imports.call_count}
    for name in ('valid','identity','job','schedule'):check('worker/'+name,lambda n=name:worker_boundary(n))
    def actual_score(owner,mode):
        e=envelope(owner);root=directory/('score-'+owner+'-'+mode);run=root/'runs'/owner/'CPU';run.mkdir(parents=True)
        e['runtime_root']=str(root.resolve());triples={};artifacts={};calls=[]
        for fx in p['fresh_fixtures']:
            t=r.example(fx['case'],fx['family_id'])[:3];triples[fx['fixture_id']]=t
            for role,value in zip(('expected','reference','policy'),t):
                artifacts[next(a['path'] for a in fx['artifacts'] if a['role']==role)]=json.dumps(value).encode()
        for i,c in enumerate(release.schedule(p,owner)):
            raw=triples.get(c['fixture_id'],r.example()[:3])[2]['ideal_native'].encode()
            rawpath=run/(str(i)+'.raw.txt');rawpath.write_bytes(raw)
            obs={'flags':[],'raw_output':{'name':rawpath.name,'sha256_written':r.sha(raw),'truncated_by_writer':False}}
            r.write(run/(str(i)+'.obs.json'),obs)
            calls.append({**c,'status':'completed','observation':str(i)+'.obs.json','observation_status':'available'})
        result={'schema':'eld-mapping-v2-run/1','release':e,'executing_head':e['executing_head'],'failure':None,'calls':calls}
        if mode=='post_failure':result['failure']='CPU post-finalization observer failure'
        if mode=='all_absent':
            result['failure']='CPU preflight failure'
            for c in calls:c.update(status='not_run_after_failure',observation=None,observation_status='absent')
        if mode=='partial':
            result['failure']='CPU first primary failure'
            for i,c in enumerate(calls):
                if i>=2:c.update(status='failed' if i==2 else 'not_run_after_failure',observation=None,observation_status='unavailable' if i==2 else 'absent')
        if mode=='invalid_progression':
            result['failure']='CPU failed first warmup';calls[0]['status']='failed'
        r.write(run/'run-result.json',result);output=root/'scores.json'
        with patch.object(scoring,'read_release',return_value=e),patch.object(scoring,'read_artifact',side_effect=lambda rr,pp,a:artifacts[a['path']]) as reads:
            if mode=='invalid_progression':
                try:scoring.score_run(run,output,'CPU','CPU',owner)
                except PermissionError as exc:
                    r.require('after first failure' in str(exc),'Wrong rejection reason');reads.assert_not_called()
                    return {'reason':str(exc),'fresh_or_public_reference_reads':0}
                raise AssertionError('Invalid otherwise complete history accepted')
            scoring.score_run(run,output,'CPU','CPU',owner)
        packet=json.loads(output.read_text());expected_records=[]
        for c in calls:
            if c['excluded']:continue
            ex,ref,pol=triples[c['fixture_id']]
            raw=pol['ideal_native'] if c['observation'] else ''
            compare=scoring.paired(raw,ex,ref,c['status'])
            scores={key:score_policy(pred,ex,ref,pol,c['status']) for key,pred in compare['predictions'].items()}
            expected_records.append({'fixture_id':c['fixture_id'],'raw_available':c['observation'] is not None,**compare,'policy_scores':scores})
        r.require(packet['records']==expected_records,'Actual score-run omitted/changed a full record')
        r.require(len(packet['records'])==(12 if owner=='author' else 1),'Wrong owner denominator')
        if owner=='author':
            for k in ('b0','mapping_v1','mapping_v2'):r.require(packet['policy_summary'][k]==summarize_policy([v['policy_scores'][k] for v in expected_records]),'Policy population differs')
        else:r.require(packet['policy_summary']['sentinel_documents']==1,'Reviewer masquerades as author population')
        try:scoring.write(output,{})
        except FileExistsError:pass
        else:raise AssertionError('Existing score overwritten')
        return {'records':len(expected_records),'completed':sum(v['completion']=='completed' for v in expected_records),'packet_sha256':r.sha(output.read_bytes()),'no_overwrite':True}
    for owner in ('author','reviewer'):
        for mode in ('completed','post_failure','all_absent','partial','invalid_progression'):
            check('score-run/'+owner+'/'+mode,lambda o=owner,m=mode:actual_score(o,m))
    out.update(checks=checks,status='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL')
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.resolve().relative_to(r.OWN)
    out={'schema':'eld-wp13-independent-runtime-checks/1','status':'FAIL','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        r.pin(out);a.out.mkdir(parents=True,exist_ok=False);execute(out,a.out)
    except BaseException:out['failure']=traceback.format_exc()
    out['input_files']=sorted(r.INPUTS.values(),key=lambda x:x['path']);out['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r.write(a.out/'result.json',out)
    print(json.dumps({'status':out['status'],'checks':len(out.get('checks',[])),'failure':out.get('failure'),'failed':[x['name'] for x in out.get('checks',[]) if x['status']!='PASS']}))
    return int(out['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
