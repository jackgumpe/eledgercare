"""Independent frozen public CPU review; no evaluated implementation or scoring code authored."""
import argparse
import copy
import datetime
import hashlib
import importlib.abc
import io
import json
from pathlib import Path
import subprocess
import sys
import traceback
import unittest

ROOT=Path(__file__).resolve().parents[5];OWN=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(OWN)]
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':raise RuntimeError('CPU review prohibits '+fullname)
sys.meta_path.insert(0,NoModel())
from qualification.mapping_v1.common import parse_native,baseline_prediction,mapping,score_document
from qualification.mapping_v1.mapper import extract_prediction
from qualification.mapping_v2.protocol.common import catalog,verify_pins
from qualification.mapping_v2.protocol.contract import validate,validate_family,validate_catalog,FAMILIES
from qualification.mapping_v2.protocol.scoring import score_policy,summarize_policy,original_comparison
from public_examples import example,unresolved_cell,unresolved_field

BASE='dc69bbabfb233cb021b3edd5ddb7264119ca081c'
SOURCE='6207daf1dc9cbdd141d083ca2d8d1e7507c63b09'
TREE='e424945507bb1d7ebf70e18e6d26bf808270bb66'
AUTHOR='9b90528f4dbd0ea1ff61c86d0d4040decf178a0a'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def require(ok,message):
    if not ok:raise AssertionError(message)
def write(path,value):
    path.resolve().relative_to(OWN);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def source_inventory():
    require(git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()==TREE,'Wrong candidate tree');verify_pins()
    rows=[]
    for prefix in ('qualification/mapping_v2','qualification/baseline','qualification/mapping_v1','qualification/coverage_v1','qualification/q0/harness/q0harness'):
        for path in git('ls-tree','-r','--name-only','HEAD','--',prefix).decode().splitlines():
            data=(ROOT/path).read_bytes();raw=git('show','HEAD:'+path);blob=git('rev-parse','HEAD:'+path).decode().strip()
            require(git('hash-object','--',path).decode().strip()==blob,'Dirty input '+path)
            require(data==raw or data.replace(b'\r\n',b'\n')==raw,'Unexplained representation '+path)
            rows.append({'path':path,'git_blob':blob,'bytes_git':len(raw),'sha256_git':sha(raw),'bytes_working':len(data),'sha256_working':sha(data)})
    return rows
def metadata(phase):return {'schema':'eld-wp13-independent-protocol-review/1','phase':phase,'status':'FAILED','source':SOURCE,'tree':TREE,'review_head':git('rev-parse','HEAD').decode().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}

def probes(report):
    rows=[];report['checks']=rows
    def check(name,fn):
        row={'name':name,'status':'FAIL'};rows.append(row)
        try:row['evidence']=fn();row['status']='PASS'
        except Exception:row['error']=traceback.format_exc()
    def rejection(mutate,case='supported',reason=None):
        e,r,p,pred=example(case);validate(e,r,p);mutate(e,r,p,pred)
        try:accepted=validate(e,r,p)
        except ValueError as exc:
            if reason:require(reason in str(exc),'Rejected at unrelated guard: '+str(exc))
            return {'rejected':True,'reason':str(exc),'expected':e,'policy':p}
        raise AssertionError('Invalid reference accepted: '+json.dumps(accepted))
    def scored(mutate=lambda e,r,p,pred:None,case='supported',completion='completed'):
        e,r,p,pred=example(case);mutate(e,r,p,pred);snapshot=canonical([e,r,p,pred])
        result=score_policy(pred,e,r,p,completion);require(canonical([e,r,p,pred])==snapshot,'Scorer mutated inputs')
        return e,r,p,pred,result
    def exact():
        e,r,p,pred,s=scored();n=len(p['slots']);require(s['metrics']['strict_correct_known_slots']==n==s['metrics']['correct_assignments'],'Known exact counts');return s
    check('independent_supported_positive',exact)
    def colon_positive():
        e,r,p,pred=example();e['expected_fields'][0]['label_printed']+=':';p['slots'][0]['evidence'][0]['label_printed']+=':'
        return validate(e,r,p)
    check('one_field_colon_allowed',colon_positive)
    check('header_colon_rejected',lambda:rejection(lambda e,r,p,pred:p['slots'][1]['evidence'][0].update(label_printed=p['slots'][1]['evidence'][0]['label_printed']+':'),reason='Supported label outside catalog'))
    check('header_case_rejected',lambda:rejection(lambda e,r,p,pred:p['slots'][1]['evidence'][0].update(label_printed=p['slots'][1]['evidence'][0]['label_printed'].upper()),reason='Supported label outside catalog'))
    def double_colon(e,r,p,pred):
        p['slots'][0]['evidence'][0]['label_printed']+='::';e['expected_fields'][0]['label_printed']+='::'
    check('two_field_colons_rejected',lambda:rejection(double_colon,reason='Supported label outside catalog'))
    check('missing_policy_opportunity_rejected',lambda:rejection(lambda e,r,p,pred:p['slots'].pop(),reason='All known expected slots'))
    check('duplicate_policy_opportunity_rejected',lambda:rejection(lambda e,r,p,pred:p['slots'].append(copy.deepcopy(p['slots'][0])),reason='Duplicate policy opportunity'))
    check('row_ordinal_mismatch_rejected',lambda:rejection(lambda e,r,p,pred:p['slots'][1].update(row_ordinal=1),reason='Cell row identity'))
    check('expected_truth_disagreement_rejected',lambda:rejection(lambda e,r,p,pred:e['expected_fields'][0].update(normalized_value='OTHER'),reason='Known truth/expected mismatch'))
    def empty_rows(e,r,p,pred):
        e['expected_tables'][0]['rows'][0]['cells']={}
        for slot in p['slots'][1:]:slot.update(truth_status='unknown',truth=None,action='abstain',reason='missing_structure')
    check('P13_01_empty_truth_row_rejected',lambda:rejection(empty_rows,'conflict','known row-key truth'))
    check('P13_01_missing_known_rowkey_rejected',lambda:rejection(lambda e,r,p,pred:unresolved_cell(e,p,1,'unknown'),'conflict','known row-key truth'))
    def partial():
        e,r,p,pred,s=scored(lambda e,r,p,pred:unresolved_cell(e,p),case='conflict');old=score_document(pred,e,r)
        require(old['rows']['correct']==1 and old['cells']['extra_cells']==1,'Original known-subset behavior changed')
        require(s['row_truth'][0]['ambiguous']==1 and s['row_truth'][0]['known']==3 and s['metrics']['surplus_output_candidates']==0,'Unjudged slot lost')
        return {'original_rows':old['rows'],'original_cells':old['cells'],'policy_score':s}
    check('P13_01_partial_row_full_policy_accounting',partial)
    def field_variation(value,duplicate=False,abstain=False):
        def mutate(e,r,p,pred):
            if abstain:pred['fields']=[]
            elif duplicate:
                extra=copy.deepcopy(pred['fields'][0]);extra['value']=value;pred['fields'].append(extra)
            else:pred['fields'][0]['value']=value
        return scored(mutate,'conflict')
    def duplicate_equal():
        e,r,p,pred,s=field_variation('PUBLIC-0042',True)
        require(score_document(pred,e,r)['fields']['correct']==1,'Original first-candidate credit changed')
        require(s['slots'][0]['candidate_count']==2 and s['slots'][0]['strict_correct_known'] is False and s['metrics']['surplus_candidates_within_slots']==1 and s['metrics']['required_abstention_violations']==1,'Duplicate guard accounting');return s
    check('duplicate_equal_candidates_retained',duplicate_equal)
    def duplicate_conflict():
        e,r,p,pred,s=field_variation('WRONG',True);require(s['metrics']['incorrect_assignments']==1 and s['slots'][0]['candidate_count']==2 and s['metrics']['required_abstention_violations']==1,'Conflict not counted');return s
    check('conflicting_candidates_retained',duplicate_conflict)
    def blank():
        e,r,p,pred,s=field_variation('');require(s['slots'][0]['abstained'] is False and s['metrics']['required_abstention_violations']==1,'Blank treated as abstention');return s
    check('blank_is_assignment_and_violation',blank)
    def withheld():
        e,r,p,pred,s=field_variation('',abstain=True);require(s['metrics']['required_abstention_observed_truth_known']==1 and s['slots'][0]['strict_correct_known'] is False and score_document(pred,e,r)['fields']['correct']==0,'Abstention credited as value');return s
    check('required_abstention_not_semantic_exact',withheld)
    for status in ('ambiguous','unknown'):
        for assigned in (True,False):
            def unresolved(status=status,assigned=assigned):
                def mutate(e,r,p,pred):
                    unresolved_field(e,p,status)
                    if not assigned:pred['fields']=[]
                e,r,p,pred,s=scored(mutate,'conflict');require(s['slots'][0]['strict_correct_known'] is None,'Unresolved truth judged')
                require(s['metrics'][status+'_truth_assignments']==int(assigned) and s['metrics']['required_abstention_observed_truth_'+status]==int(not assigned),'Unresolved counts');return s
            check('unresolved_'+status+('_assigned' if assigned else '_withheld'),unresolved)
    for state in ('failed','not_run_after_failure','parse_error','no_page','empty_blocks','unsupported_visibility'):
        def unavailable(state=state):
            def mutate(e,r,p,pred):
                if state=='parse_error':pred['parse_errors']=['generic public parse failure']
                elif state=='no_page':pred['pages']=[]
                elif state=='empty_blocks':pred['pages'][0]['blocks']=[]
                elif state=='unsupported_visibility':pred['pages'][0]['blocks'][0]['text']='<unknown>public</unknown>'
            e,r,p,pred,s=scored(mutate,'conflict',state if state in ('failed','not_run_after_failure') else 'completed')
            n=len(p['slots']);m=s['metrics'];require(not s['eligible'] and m['unavailable_slots']==n and m['observed_candidates']==n and m['correct_assignments']==m['required_abstention_observed']==m['abstentions']==0,'Unavailable evidence credited')
            require(s['rates']['coverage_eligible']['rate'] is None,'Empty conditional rate must be null');return s
        check('unavailable_'+state,unavailable)
    for kind in ('table','column','extra_column','unknown_field','unknown_row'):
        def multiplicity(kind=kind):
            def mutate(e,r,p,pred):
                t=pred['tables'][0]
                if kind=='table':pred['tables'].append(copy.deepcopy(t))
                elif kind=='column':t['columns'][1]=t['columns'][0]
                elif kind=='extra_column':t['rows'][0]['values'].append('SURPLUS')
                elif kind=='unknown_field':pred['fields'].append({'field_id':'outside_scope','page':1,'value':'SURPLUS'})
                else:t['rows'].append(copy.deepcopy(t['rows'][0]))
            e,r,p,pred,s=scored(mutate)
            if kind in ('table','column'):require(s['slots'][1]['candidate_count']==2 and s['slots'][1]['strict_correct_known'] is False,'Duplicate table/column collapsed')
            else:require(s['metrics']['surplus_output_candidates']==(4 if kind=='unknown_row' else 1),'Surplus assignment dropped')
            return s
        check('candidate_'+kind,multiplicity)
    def identifier():
        e,r,p,pred,s=scored(lambda e,r,p,pred:pred['fields'][0].update(value='PUBLIC-42'))
        require(s['metrics']['incorrect_assignments']==1,'Identifier repaired');return s
    check('literal_identifier_preserved',identifier)
    def family():return validate_family([example(c)[:3] for c in ('supported','conflict','unsupported')])
    check('matched_family_positive',family)
    def family_units():
        records=[example(c)[:3] for c in ('supported','conflict','unsupported')]
        for e,r,p in records:e['expected_fields'][0]['quantity_unit']='EA';p['slots'][0]['truth']['quantity_unit']='EA'
        records[-1][0]['expected_fields'][0]['quantity_unit']='HR';records[-1][2]['slots'][0]['truth']['quantity_unit']='HR'
        try:validate_family(records)
        except ValueError as exc:return {'rejected':True,'reason':str(exc)}
        raise AssertionError('Family unit identity drift accepted')
    check('family_unit_identity_drift_rejected',family_units)
    def frame():
        scores=[]
        for fam in FAMILIES:
            for case in ('supported','conflict','unsupported'):
                e,r,p,pred=example(case,fam);scores.append(score_policy(pred,e,r,p,'not_run_after_failure' if fam=='WP13-F04' else 'completed'))
        s=summarize_policy(scores);require(s['all']['documents']==12 and s['all']['eligible_documents']==9 and s['equal_family_means']['coverage_eligible']['families_with_denominator']==3,'Full/macro denominators changed')
        for invalid in (scores[:-1],scores[:-1]+[scores[0]]):
            try:summarize_policy(invalid)
            except ValueError:continue
            raise AssertionError('Incomplete/duplicate twelve-document frame accepted')
        return s
    check('full_frame_mixed_available_and_unavailable',frame)
    report['status']='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL'

def author_tests(report,out):
    stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'qualification/mapping_v2/protocol/tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    with (out/'author-tests.txt').open('x',encoding='utf-8',newline='\n') as f:f.write(stream.getvalue())
    report.update(tests=result.testsRun,failures=[[str(t),s] for t,s in result.failures],errors=[[str(t),s] for t,s in result.errors],skipped=[[str(t),s] for t,s in result.skipped],status='PASS' if result.wasSuccessful() else 'FAIL')

def history(report):
    inputs=[]
    def read(path):
        data=(ROOT/path).read_bytes();inputs.append({'path':path,'bytes':len(data),'sha256':sha(data),'git_blob':git('hash-object','--',path).decode().strip()});return data
    prior=json.loads(read('docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/scores.json'));results=[]
    for r in prior['records']:
        fid=r['fixture_id'];pre='evaluation/coverage_v1/corpus/r1/'
        e=json.loads(read(pre+'expected/'+fid+'.json'));ref=json.loads(read(pre+'reference/'+fid+'.json'))
        raw=read('docs/evidence/WP-0011/eld-mapping-author/005/attempt-1/run/evidence/'+fid+'.measured.raw.txt')
        require(sha(raw)==r['raw_sha256'],'Historical raw changed');parsed=parse_native(raw.decode());rules=mapping()
        direct={'b0':baseline_prediction(parsed,rules),'mapping_v1':extract_prediction(parsed,rules)}
        scores={k:score_document(v,e,ref,r['completion']) for k,v in direct.items()};wrapped=original_comparison(raw.decode(),e,ref,r['completion'])
        require(canonical(direct)==canonical(r['predictions'])==canonical(wrapped['predictions']),'Full predictions changed '+fid)
        require(canonical(scores)==canonical(r['scores'])==canonical(wrapped['scores']),'Full scores changed '+fid)
        require(wrapped['v2_status']=='not_implemented' and 'mapping_v2' not in wrapped['scores'],'Premature v2 implementation')
        results.append({'fixture_id':fid,'raw_sha256':sha(raw),'full_predictions_sha256':sha(canonical(direct)),'full_scores_sha256':sha(canonical(scores)),'full_objects_equal':True})
    report.update(status='PASS',documents=results,input_inventory=inputs,comparison='Direct frozen B0/v1 extraction+original scorer, independently compared against old immutable twelve-document packets and new protocol wrapper.')

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('probes','author-tests','history'));p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    out=a.out.resolve();out.relative_to(OWN);out.mkdir(parents=True,exist_ok=False);report=metadata(a.phase)
    try:
        report['source_inventory']=source_inventory()
        if a.phase=='probes':probes(report)
        elif a.phase=='author-tests':author_tests(report,out)
        else:history(report)
    except Exception:report['error']=traceback.format_exc()
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(out/'result.json',report)
    print(json.dumps({'phase':a.phase,'status':report['status'],'checks':len(report.get('checks',[])),'tests':report.get('tests'),'documents':len(report.get('documents',[])),'failures':[x['name'] for x in report.get('checks',[]) if x['status']!='PASS']}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
