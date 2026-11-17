"""Released finite packet scoring; original B0/v1 scores and new diagnostics separate."""
import json
from pathlib import Path
from .common import load_json,sha,write,paired,summarize
from .diagnostics import diagnose,paired_conditions
from .release import read_release,protocol,schedule,fixture,read_artifact,require

def validated_calls(result,p,owner,run):
    """Validate every scheduled call, including excluded warmups, before credit.

    A post-finalization failure may coexist with completed calls. A first call
    failure/gap may only be followed by not-run rows. Invalid histories reject
    the packet; legitimate failed/not-run rows keep their expected denominators.
    """
    require(isinstance(result,dict) and result.get('schema')=='eld-coverage-v1-run/1' and
            'failure' in result and (result['failure'] is None or isinstance(result['failure'],str)),'Malformed run result')
    calls=result.get('calls');plan=schedule(p,owner)
    require(isinstance(calls,list) and len(calls)==len(plan),'Finite run denominator mismatch')
    stopped=False
    for call,wanted in zip(calls,plan):
        require(isinstance(call,dict) and all(call.get(k)==v for k,v in wanted.items()),'Finite call order mismatch')
        require({'status','observation','observation_status'}<=call.keys(),'Incomplete call record')
        state=call['status'];obs=call['observation'];availability=call['observation_status']
        require(state in ('completed','failed','not_run_after_failure'),'Unknown call status')
        require(availability in ('available','absent','unavailable'),'Unknown observation status')
        require(not stopped or state=='not_run_after_failure','Call executed after first failure/unavailable call')
        if state!='completed':stopped=True
        if state=='not_run_after_failure':require(obs is None,'Not-run call has a scored observation')
        elif state=='completed':require(isinstance(obs,str) and bool(obs) and availability=='available','Completed call observation unavailable')
        if obs is not None:require(isinstance(obs,str) and bool(obs) and availability=='available','Malformed observation reference')
    require(not stopped or bool(result['failure']),'Incomplete calls without run failure')
    raws=[]
    for call in calls:
        raw=None
        if call['observation'] is not None:
            path=(run/call['observation']).resolve();path.relative_to(run);obs=load_json(path)
            require(isinstance(obs,dict) and isinstance(obs.get('flags'),list),'Malformed call observation')
            if call['status']=='completed':
                require(not obs['flags'] and not obs.get('error') and isinstance(obs.get('raw_output'),dict),'Completed call contains failure or missing raw metadata')
                require(obs['raw_output'].get('truncated_by_writer') is False,'Completed raw capture unavailable/truncated')
            if 'raw_output' in obs:
                meta=obs['raw_output'];require(isinstance(meta,dict) and isinstance(meta.get('name'),str) and bool(meta['name']),'Malformed raw metadata')
                raw_path=(path.parent/meta['name']).resolve();raw_path.relative_to(run)
                data=raw_path.read_bytes();require(sha(data)==meta.get('sha256_written'),'Raw hash mismatch');raw=data.decode('utf-8')
        raws.append(raw)
    return calls,raws

def score_run(run,output,authority,release_path,owner):
    r=read_release(authority,release_path,owner,execution=False);p=protocol();run=Path(run).resolve()
    run.relative_to(Path(r['runtime_root']).resolve()/'runs'/owner)
    result=load_json(run/'run-result.json');require(result['release']==r,'Run/release mismatch')
    calls,raws=validated_calls(result,p,owner,run)
    records=[];diagnostics=[]
    for call,raw in zip(calls,raws):
        if call['excluded']:continue
        fx=fixture(p,call['fixture_id']);art={a['role']:a for a in fx['artifacts']}
        expected,reference,annotations=[json.loads(read_artifact(r,p,art[role])) for role in ('expected','reference','annotations')]
        pair=paired(raw or '',expected,reference,call['status'])
        diagnostic=diagnose(raw,expected,reference,call['status'],annotations,pair);diagnostics.append(diagnostic)
        records.append({'fixture_id':fx['fixture_id'],**pair,'diagnostic':{k:v for k,v in diagnostic.items() if k!='historical_scores'}})
    packet={'schema':'eld-coverage-paired/1','owner':owner,'run_result_sha256':sha((run/'run-result.json').read_bytes()),'records':records,
        'historical_summary':{key:summarize([x['scores'][key] for x in records]) for key in ('b0','mapping_v1')},
        'diagnostic_pairing':paired_conditions(diagnostics) if owner=='author' else {'sentinel_documents':1,'preselected_id':p['reviewer_sentinel'],'limit':'Reviewer sentinel is not the twelve-author-document population.'},
        'interpretation':'Unchanged B0/v1 full metrics plus separately versioned stage evidence; no quality treatment or causal certainty.'}
    write(output,packet)
