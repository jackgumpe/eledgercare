"""Independent public CPU counterexamples; no private inputs or live observers."""
import contextlib
import copy
import datetime
import importlib.abc
import io
import json
from pathlib import Path
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT))
class CPUOnly(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':
            raise RuntimeError('Review forbids model/renderer import: '+fullname)
sys.meta_path.insert(0,CPUOnly())
from qualification.coverage_v1 import runtime,scoring,contract,diagnostics
from qualification.coverage_v1.common import protocol,sha,git,HERE,write
from qualification.coverage_v1.release import schedule
sys.path.insert(0,str(HERE/'tests'))
from test_release import valid_release  # Existing public release-shaped CPU stub only.

def fixture(condition='control',family='WP11-F01',value='R42'):
    fid=f'{family}-{condition}-v0'
    raw='<PAGE><BLOCK>text[0,0,900,30]<FORK>Work Order ID: '+value
    e={'fixture_id':fid,'family_id':family,'split':'diagnostic_eval','variant_kind':condition,'page_count':1,
       'expected_fields':[{'field_id':'work_order_id','page_number':1,'label_printed':'Work Order ID','printed_text':value,'normalized_value':value,'value_type':'identifier'}],
       'expected_tables':[],'expected_absences':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
    r={'pages':['Work Order ID: '+value],'coverage':{'status':'reviewer public synthetic'}}
    a={'schema':'eld-coverage-annotations/1','fixture_id':fid,'family_id':family,'condition':condition,'control_fixture_id':family+'-control-v0','page_count':1,
       'fields':[{'field_id':'work_order_id','page_number':1,'label_printed':'Work Order ID','label_bbox_pt':[0,0,10,10],'value_bbox_pt':[11,0,20,10]}],
       'tables':[],'absences':[],'ideal_native':raw}
    return e,r,a

def visible_probes():
    cases=[('br_false_positive','RED<br>BLUE','REDBLUE',0),('paragraph_false_positive','<p>RED</p><p>BLUE</p>','REDBLUE',0),
           ('br_space','RED<br>BLUE','RED BLUE',1),('inline_concatenation','<span>RED</span><span>BLUE</span>','REDBLUE',1),
           ('hidden_metadata','<span data-id="REDBLUE">OTHER</span><!--REDBLUE--><script>REDBLUE</script><style>REDBLUE</style>','REDBLUE',0),
           ('entity','X&amp;Y','X&Y',1),('strict_identifier','X0042','0042',0)]
    result=[]
    for name,payload,target,want in cases:
        e,r,_=fixture(value=target);raw='<PAGE><BLOCK>text[0,0,900,30]<FORK>'+payload
        d=diagnostics.diagnose(raw,e,r)
        got=d['slots'][0]['value_presence']['count']
        result.append({'case':name,'raw':raw,'target':target,'expected_count':want,'actual_count':got,'pass':got==want,
                       'eligible':d['eligible_for_presence'],'parse_errors':d['parse_errors'],'presence':d['slots'][0]['value_presence']})
    return result

def contract_probes():
    results=[]
    family=[fixture(c) for c in contract.CONDITIONS]
    for name,mutate in [('unit_present',lambda x:x['expected_fields'][0].update(quantity_unit='EA')),
                        ('unit_value',lambda x:x['expected_fields'][0].update(quantity_unit='HR'))]:
        data=copy.deepcopy(family)
        if name=='unit_value':
            for e,_,_ in data:e['expected_fields'][0]['quantity_unit']='EA'
        mutate(data[1][0])
        try:contract.validate_family(data);rejected=False
        except ValueError:rejected=True
        results.append({'case':name,'rejected':rejected,'pass':rejected})
    for name in ('unit_null','unit_empty','absence_state','absence_label'):
        e,r,a=fixture()
        if name.startswith('unit'):e['expected_fields'][0]['quantity_unit']=None if name=='unit_null' else ''
        else:
            e['expected_absences']=[{'field_id':'tenant_callback_notes','page_number':1,'label_printed':'Tenant Callback Notes','expected_state':'absent_blank'}]
            a['absences']=[{'field_id':'tenant_callback_notes','page_number':1,'label_printed':'Tenant Callback Notes','label_bbox_pt':[0,20,10,30]}]
            if name=='absence_state':e['expected_absences'][0]['expected_state']='present'
            else:a['absences'][0]['label_printed']='DIFFERENT'
        try:contract.validate(e,r,a);rejected=False
        except ValueError:rejected=True
        results.append({'case':name,'rejected':rejected,'pass':rejected})
    return results

def supervisor_probe(case,scratch):
    runtime.q0_imports()
    import q0harness.environment as env
    import q0harness.supervisor as observer
    import winjob
    with tempfile.TemporaryDirectory(dir=scratch) as tmp:
        t=Path(tmp);base=t/'stub';(base/'venv/Scripts').mkdir(parents=True);(base/'venv/Scripts/python.exe').write_bytes(b'never execute')
        p=protocol();p['read_only_q0_root']=str(base);p['free_floor_bytes']=0
        r=valid_release(p);r['runtime_root']=str(t/'runtime');root=Path(r['runtime_root']);plan=schedule(p,'author')
        class Process:
            pid=654321;returncode=0
            def poll(self):return self.returncode
            def wait(self,timeout):return self.returncode
            def kill(self):self.returncode=1
        def spawn(*args,**kwargs):
            run=next((root/'runs/author').iterdir());e=run/'evidence';e.mkdir()
            for call in plan:write(e/(call['fixture_id']+'.'+call['kind']+'.observation.json'),{'flags':[]})
            write(e/'worker-outcome.json',{'failure':None,'active_call':plan[-1]['fixture_id']+'.measured'})
            return Process()
        def observe(commands,run,tag):
            paths=[run/(tag+'-'+str(i)+'.txt') for i in range(2)]
            paths[0].write_text('timestamp, '+p['gpu']['uuid']);paths[1].write_text('')
            rows=[{'returncode':0,'bytes':f.stat().st_size,'path':str(f)} for f in paths]
            if tag=='post':
                if case=='nonzero_return':rows[0]['returncode']=1
                elif case=='timeout_row':rows[0]['returncode']=None;rows[0]['error']='TimeoutExpired';paths[0].write_text('')
                elif case=='wrong_device':paths[0].write_text('timestamp, WRONG-DEVICE')
                elif case=='empty_capture':return []
            return rows
        environment={k:str(t/'cache'/k) for k in ('TEMP','TMP','TMPDIR','HF_HOME','HF_MODULES_CACHE','CUDA_CACHE_PATH','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','USERPROFILE')};environment['PATH']=''
        capture=io.StringIO()
        with contextlib.ExitStack() as s,contextlib.redirect_stdout(capture):
            for obj,name,kw in [(runtime,'read_release',{'return_value':r}),(runtime,'protocol',{'return_value':p}),
                (runtime,'git',{'return_value':b'public-cpu-mock-head'}),(env,'build_child_env',{'return_value':environment}),
                (env,'audit_child_env',{}),(env,'resolve_host_git',{'return_value':'git'}),
                (observer,'run_observers',{'side_effect':observe}),(winjob,'create',{'return_value':42}),(winjob,'close',{}),
                (runtime.subprocess,'Popen',{'side_effect':spawn})]:s.enter_context(patch.object(obj,name,**kw))
            code=runtime.execute('CPU','CPU','author')
        result=json.loads(next(root.rglob('run-result.json')).read_text())
        return {'case':case,'exit':code,'pass':code!=0,'expected':'Non-successful/unavailable post observation cannot be successful final observation',
                'run_result':result,'stdout':capture.getvalue()}

def score_state_probe(scratch):
    p=protocol();by_path={}
    for fx in p['fresh_fixtures']:
        for role,value in zip(('expected','reference','annotations'),fixture(fx['condition'],fx['family_id'])):
            by_path[next(a['sealed_relative_path'] for a in fx['artifacts'] if a['role']==role)]=json.dumps(value).encode()
    with tempfile.TemporaryDirectory(dir=scratch) as tmp:
        root=Path(tmp);r=valid_release(p);r['runtime_root']=str(root);run=root/'runs/author/CPU';run.mkdir(parents=True)
        raw=fixture()[2]['ideal_native'].encode();(run/'raw.txt').write_bytes(raw)
        write(run/'obs.json',{'flags':[],'raw_output':{'name':'raw.txt','sha256_written':sha(raw)}})
        calls=[{**c,'status':'failed' if i==0 else 'completed','observation':'obs.json'} for i,c in enumerate(schedule(p,'author'))]
        write(run/'run-result.json',{'release':r,'calls':calls})
        with patch.object(scoring,'read_release',return_value=r),patch.object(scoring,'read_artifact',side_effect=lambda r,p,a:by_path[a['sealed_relative_path']]):
            try:scoring.score_run(run,root/'scores.json','CPU','CPU','author');error=None
            except Exception as exc:error=repr(exc)
        packet=json.loads((root/'scores.json').read_text()) if (root/'scores.json').exists() else None
        return {'case':'completed_after_failed_warmup','pass':error is not None,'rejection':error,'calls':calls,
                'actual_historical_summary':None if packet is None else packet['historical_summary'],
                'actual_pairing':None if packet is None else packet['diagnostic_pairing']}

def main():
    out=Path(sys.argv[1]).resolve();out.relative_to(Path(__file__).parent)
    assert not out.exists();assert not git('status','--porcelain').strip(),'Freeze first'
    assert git('rev-parse','HEAD:qualification/coverage_v1').decode().strip()=='ed07a273a57a71b43b0fed9cea12a2245d7c7958'
    scratch=ROOT/'.scratch/wp0011-reviewer-source';scratch.mkdir(parents=True,exist_ok=True)
    results={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executing_head':git('rev-parse','HEAD').decode().strip(),
             'source_commit':'adb51ac317db18950f3f1ef4629864127956eddc','source_tree':'ed07a273a57a71b43b0fed9cea12a2245d7c7958',
             'helper_sha256':sha(Path(__file__).read_bytes()),'visible':visible_probes(),'contract':contract_probes(),
             'supervisor':[supervisor_probe(c,scratch) for c in ('nonzero_return','timeout_row','wrong_device','empty_capture')],
             'score_state':score_state_probe(scratch)}
    results['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(out/'probes.json',results)
    print(json.dumps({'visible':[(r['case'],r['pass']) for r in results['visible']],
                      'contract':all(r['pass'] for r in results['contract']),
                      'supervisor':[(r['case'],r['pass'],r['exit']) for r in results['supervisor']],
                      'score_state':results['score_state']['pass']},indent=2))
if __name__=='__main__':main()
