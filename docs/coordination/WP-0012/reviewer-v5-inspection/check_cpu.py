"""Root's independent CPU-only inspection of reviewer v5; grants no lease."""
import builtins
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
TARGET=ROOT/'docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/helpers/run_wp0012_reviewer_rehearsal_v5.py'
OUT=Path(__file__).with_name('result.json')
if OUT.exists():raise FileExistsError(OUT)
native_import=builtins.__import__
def blocked_import(name,*args,**kwargs):
    if name.split('.')[0] in {'torch','transformers','pypdfium2','q0harness','eledgercare_worker'}:
        raise AssertionError('Forbidden model/renderer import in root CPU inspection: '+name)
    return native_import(name,*args,**kwargs)
builtins.__import__=blocked_import
spec=importlib.util.spec_from_file_location('root_wp12_v5_cpu',TARGET)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
checks=[]
def yes(name,fn):
    fn();checks.append({'check':name,'passed':True})
def no(name,fn):
    try:fn()
    except m.ReviewerLeaseGuardError:checks.append({'check':name,'passed':True});return
    raise AssertionError('Expected guard rejection: '+name)
accepted='1851fc06f0384712a41563e80a0b45f6e43548c6'
yes('actual accepting007 Git report',lambda:m._verify_commit_has_no_non_accepting_007_report(ROOT,accepted))
for rev in ['f1b8306ef62bf1c82a9106509ce31988e94b1dab','379d8c5d607fd248d7f272e412b4ed4a97bc64f6']:
    no('existing commit without accepting007 '+rev,lambda rev=rev:m._verify_commit_has_no_non_accepting_007_report(ROOT,rev))
payload={'owner':'eld-f4-implementer','lease_id':'WP-0012-SYNTHETIC-ROOT-CPU-ONLY','lease_returned':True,'clean_return_verified':True,'returned_utc':'2026-11-17T00:00:00+00:00','status':'completed','ocr_worker_processes_running':0,'lingering_attempt_processes':[],'cleanup_errors':[]}
yes('explicit synthetic clean author return',lambda:m._validate_author_lease_return_payload(payload,'SYNTHETIC ONLY'))
no('empty author return',lambda:m._validate_author_lease_return_payload({},'SYNTHETIC ONLY'))
for key,value in [('lease_returned',False),('lease_returned','true'),('clean_return_verified',False),('owner','other'),('lease_id',''),('returned_utc',None),('ocr_worker_processes_running',False),('ocr_worker_processes_running',1),('lingering_attempt_processes',[123]),('cleanup_errors',['injected']),('status','cleanup_failed_lease_unreturned')]:
    trial=copy.deepcopy(payload);trial[key]=value
    no('reject author return '+key+'='+repr(value),lambda trial=trial:m._validate_author_lease_return_payload(trial,'SYNTHETIC ONLY'))
args=dict(lease_id='WP-0012-SYNTHETIC-ROOT-CPU-ONLY',run_error=None,cleanup_errors=[],ports_after={str(p):[] for p in m.REVIEWER_PORTS},pg_ctl_status_exit_code=3,api_stop_receipts=[],ui_stop_receipts=[],pre_ownership={},post_ownership={'sole_model_job_verified':True},q0_model_immutability_verified=True,persisted_counts={},run_directories=[],postmaster_recorded=None,secrets=[])
def receipt_check(overrides,returned):
    trial=copy.deepcopy(args);trial.update(overrides);result=m.build_reviewer_lease_return_receipt(**trial)
    assert result['lease_returned'] is returned and result['clean_return_verified'] is returned
    assert (result['returned_utc'] is not None) is returned
yes('synthetic complete clean return',lambda:receipt_check({},True))
yes('failed workflow with verified cleanup returns resource',lambda:receipt_check({'run_error':'injected first failure'},True))
for key,value in [('ports_after',{}),('ports_after',{str(p):[{'pid':123}] for p in m.REVIEWER_PORTS}),('pg_ctl_status_exit_code',0),('api_stop_receipts',[{'aliveAfter':True}]),('ui_stop_receipts',[{'aliveAfter':True}]),('post_ownership',{}),('q0_model_immutability_verified',False),('cleanup_errors',['injected'])]:
    yes('unreturned reviewer resource '+key,lambda key=key,value=value:receipt_check({key:value},False))
result={'schema':'eld-wp12-root-v5-cpu-inspection/1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_frozen_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'reviewer_publication':accepted,'helper_path':TARGET.relative_to(ROOT).as_posix(),'helper_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),'synthetic_test_only':True,'status':'PASS','checks':checks,'live_process_service_gpu_activity':False,'limits':'Focused independent real-Git acceptance and pure receipt guards only. No complete live004 workflow claim, no model/renderer import, no actual lease or resource observation. Root must semantically accept actual003 and independently acknowledge its return before004.'}
OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'status':'PASS','checks':len(checks),'output':str(OUT)}))
