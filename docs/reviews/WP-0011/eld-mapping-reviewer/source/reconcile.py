"""Final source reconciliation using public synthetic cases and exposed history."""
import contextlib
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import traceback
import unittest
from unittest.mock import patch

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[4];sys.path.insert(0,str(ROOT))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
probes=module('reviewer_original_probes',OWN/'probes_v2.py')  # Installs CPU-only import guard.
repro=module('reviewer_original_reproduction',OWN/'reproduce_v3.py')
from qualification.coverage_v1 import scoring,diagnostics,runtime
from qualification.coverage_v1.common import HERE,git,sha,write,protocol,verify_frozen_mappers
from qualification.coverage_v1.release import schedule
SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'
TREE='6bdab544c9fe26cbf093cc765212db2a2e7a97a5'
LEDGER='docs/research/WP-0011/eld-mapping-author/009/attempt-1/author-suite/diagnostic-ledger.json'

def score_cases(scratch):
    p=protocol();by_path={}
    for fx in p['fresh_fixtures']:
        for role,value in zip(('expected','reference','annotations'),probes.fixture(fx['condition'],fx['family_id'])):
            by_path[next(a['sealed_relative_path'] for a in fx['artifacts'] if a['role']==role)]=json.dumps(value).encode()
    receipts=[]
    for owner in ('author','reviewer'):
        for case in ('normal','post_failure','all_not_run','failed_first','partial','after_failed_first','after_gap','missing_status','unknown_status','missing_observation','truncated_raw','incomplete_without_failure'):
            with tempfile.TemporaryDirectory(dir=scratch) as tmp:
                root=Path(tmp);r=probes.valid_release(p,owner);r['runtime_root']=str(root);run=root/'runs'/owner/'CPU';run.mkdir(parents=True)
                raw=probes.fixture()[2]['ideal_native'].encode();(run/'raw.txt').write_bytes(raw)
                obs={'flags':[],'raw_output':{'name':'raw.txt','sha256_written':sha(raw),'truncated_by_writer':False}}
                calls=[{**c,'status':'completed','observation':'obs.json','observation_status':'available'} for c in schedule(p,owner)]
                result={'schema':'eld-coverage-v1-run/1','release':r,'failure':None,'calls':calls}
                if case=='post_failure':result['failure']='POST_OBSERVER_VALIDATION_FAILURE'
                if case in ('all_not_run','failed_first','partial','after_failed_first','after_gap','incomplete_without_failure'):
                    result['failure']='PUBLIC_CPU_FAILURE'
                if case in ('all_not_run','failed_first','incomplete_without_failure'):
                    for c in calls:c.update(status='not_run_after_failure',observation=None,observation_status='absent')
                if case=='failed_first':calls[0].update(status='failed',observation='obs.json',observation_status='available')
                if case=='partial' and owner=='author':
                    calls[3].update(status='failed',observation=None,observation_status='unavailable')
                    for c in calls[4:]:c.update(status='not_run_after_failure',observation=None,observation_status='absent')
                if case=='after_failed_first':calls[0]['status']='failed'
                if case=='after_gap':calls[0].update(status='not_run_after_failure',observation=None,observation_status='absent')
                if case=='missing_status':calls[0].pop('status')
                if case=='unknown_status':calls[0]['status']='success'
                if case=='missing_observation':calls[0]['observation']=None
                if case=='truncated_raw':obs['raw_output']['truncated_by_writer']=True
                if case=='incomplete_without_failure':result['failure']=None
                write(run/'obs.json',obs);write(run/'run-result.json',result)
                valid=case in ('normal','post_failure','all_not_run','failed_first','partial')
                with patch.object(scoring,'read_release',return_value=r),patch.object(scoring,'read_artifact',side_effect=lambda r,p,a:by_path[a['sealed_relative_path']]) as reads:
                    try:scoring.score_run(run,root/'scores.json','CPU','CPU',owner);error=None
                    except Exception as exc:error={'type':type(exc).__name__,'message':str(exc)}
                entry={'owner':owner,'case':case,'expected_valid':valid,'error':error,'artifact_reads':reads.call_count,'input_packet':result}
                assert (error is None)==valid,(owner,case,error)
                if not valid:
                    assert not (root/'scores.json').exists() and reads.call_count==0
                    if case in ('after_failed_first','after_gap'):assert 'after first failure' in error['message']
                else:
                    packet=json.loads((root/'scores.json').read_text());n=12 if owner=='author' else 1
                    correct=0 if case in ('all_not_run','failed_first') else 1 if case=='partial' else n
                    assert len(packet['records'])==n
                    for mapper in ('b0','mapping_v1'):
                        assert sum(x['scores'][mapper]['fields']['total'] for x in packet['records'])==n
                        assert sum(x['scores'][mapper]['fields']['correct'] for x in packet['records'])==correct
                    if owner=='author':assert packet['diagnostic_pairing']['paired_comparisons']==9
                    else:assert packet['diagnostic_pairing']['preselected_id']=='WP11-F03-degraded-v0'
                    entry['full_packet']=packet
                entry['pass']=True;receipts.append(entry)
    return receipts

def extra_visibility():
    e,r,a=probes.fixture();native=a['ideal_native']+'<BLOCK>text[0,60,900,90]<FORK><unknown-panel>R42</unknown-panel>'
    d=diagnostics.diagnose(native,e,r)
    assert not d['eligible_for_presence'] and d['presence_denominator']['unavailable_slots']==1
    assert d['slots'][0]['local_visible_payload_evidence_not_rate']['count']==1
    assert d['slots'][0]['value_presence']['count'] is None
    assert d['visibility_errors'][0]['unsupported_html_tags']==['unknown-panel']
    return {'input':native,'diagnostic':d,'pass':True}

def observer_rows(scratch):
    p=protocol();results=[]
    with tempfile.TemporaryDirectory(dir=scratch) as tmp:
        root=Path(tmp);paths=[root/'device.txt',root/'processes.txt']
        for case in ('valid_desktop','wrong_device','stderr','size_mismatch','truncation','boolean_return','error_despite_zero'):
            paths[0].write_text('timestamp, '+('OTHER-DEVICE' if case=='wrong_device' else p['gpu']['uuid']))
            paths[1].write_text('123, desktop.exe, [N/A]'+('\n--- stderr --- error' if case=='stderr' else ''))
            rows=[{'returncode':0,'bytes':f.stat().st_size,'path':str(f)} for f in paths]
            if case=='size_mismatch':rows[0]['bytes']+=1
            if case=='truncation':rows[0]['bytes']=65536
            if case=='boolean_return':rows[0]['returncode']=False
            if case=='error_despite_zero':rows[0]['error']='error'
            try:accepted=runtime.verify_device_observation(rows,p);error=None
            except Exception as exc:accepted=None;error=str(exc)
            assert (error is None)==(case=='valid_desktop')
            results.append({'case':case,'rows':rows,'capture_text':[f.read_text() for f in paths],'accepted':accepted,'error':error,'pass':True})
    return results

def main():
    out=Path(sys.argv[1]).resolve();out.relative_to(OWN)
    assert not out.exists() and not git('status','--porcelain').strip(),'Freeze first'
    assert git('rev-parse','HEAD:qualification/coverage_v1').decode().strip()==TREE
    assert sha((HERE/'protocol.json').read_bytes())=='03b13a41a0047c827af32e71209933700457a5dfd6d38ec106daed82ef5b9000'
    verify_frozen_mappers();out.mkdir(parents=True)
    scratch=ROOT/'.scratch/wp0011-reviewer-reconciliation';scratch.mkdir(parents=True,exist_ok=True)
    receipt={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executing_head':git('rev-parse','HEAD').decode().strip(),
             'source_commit':SOURCE,'source_tree':TREE,'helper_sha256':sha(Path(__file__).read_bytes()),'python':sys.version}
    try:
        with (out/'tests-stdout.txt').open('x',encoding='utf-8',newline='') as stdout,(out/'tests-stderr.txt').open('x',encoding='utf-8',newline='') as stderr:
            with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                tests=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.discover(str(HERE/'tests')))
        receipt['tests']={'run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors),'skipped':len(tests.skipped)}
        assert tests.wasSuccessful() and tests.testsRun==27
        checks={'visible':probes.visible_probes(),'contract':probes.contract_probes(),'extra_visibility':extra_visibility(),
                'supervisor':[probes.supervisor_probe(c,scratch) for c in ('nonzero_return','timeout_row','wrong_device','empty_capture')],
                'observer_rows':observer_rows(scratch),'score_cases':score_cases(scratch)}
        for name in ('visible','contract','supervisor','observer_rows','score_cases'):assert all(x['pass'] for x in checks[name]),name
        for case in checks['supervisor']:
            result=case['run_result'];assert result['failure'] and result['finalization_errors']
            assert result['final_observation_status']['post_observers']=='unavailable'
            assert all(c['status']=='completed' for c in result['calls']) and result['observed_child_exit'] is True
        write(out/'affected-probes.json',checks)
        original_load=repro.load
        repro.load=lambda path:original_load(LEDGER if path==repro.AUTHOR+'/attempt-2/diagnostic-ledger.json' else path)
        full=repro.reproduce();write(out/'historical-reproduction.json',full)
        prior=json.loads((OWN/'reproduction-3/reproduction.json').read_text())
        assert len(prior['records'])==len(full['records'])==31
        assert all(a['full_pair_sha256_canonical']==b['full_pair_sha256_canonical'] for a,b in zip(prior['records'],full['records']))
        candidate=json.loads((ROOT/LEDGER).read_text());old=json.loads((ROOT/repro.AUTHOR/'attempt-2/diagnostic-ledger.json').read_text())
        changes=[]
        for a,b in zip(old['documents'],candidate['documents']):
            if a['presence_denominator']!=b['presence_denominator']:
                changes.append({'fixture_id':b['fixture_id'],'prior':a['presence_denominator'],'corrected':b['presence_denominator'],
                                'visibility_errors':b['visibility_errors']})
        assert full['summary']['expected_field_cell_slots']==2291 and full['summary']['presence_eligible_slots']==1849 and full['summary']['presence_unavailable_slots']==442
        assert len(changes)==2 and sum(x['corrected']['unavailable_slots']-x['prior']['unavailable_slots'] for x in changes)==247
        receipt['historical_summary']=full['summary'];receipt['all_31_full_pair_hashes_equal_initial']=True;receipt['diagnostic_denominator_changes']=changes
        receipt['preliminary_author_ledger']=LEDGER;receipt['preliminary_author_ledger_sha256']=sha((ROOT/LEDGER).read_bytes());receipt['status']='PASS'
    except BaseException:
        receipt['status']='FAIL';receipt['traceback']=traceback.format_exc();raise
    finally:
        receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(out/'execution.json',receipt)
        write(out/'reproduction-inputs.json',{'files':sorted(repro.inputs.values(),key=lambda x:x['path'])})
        print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
