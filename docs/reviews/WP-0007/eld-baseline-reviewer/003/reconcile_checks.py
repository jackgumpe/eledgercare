"""Independent /003 reconciliation against the single published author correction."""
from __future__ import annotations
import copy, datetime, hashlib, inspect, json, random, shutil, subprocess, sys, traceback
from pathlib import Path

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[4]
sys.path.insert(0,str(OWN))
import review_checks as original
import baseline, corpus, native, release, score, typed_values

CANDIDATE='f807e0ac737df4e9e0aeeb96f716afec57f58ff6'
PUBLICATION='e22c6730d19a6d616f0e7afb00b9416635799c16'
TREE='df44162c62641596032df04bc834754da38a5f7b'
DESIGN='d106db76de6dc8d9b52770d405ca95300b6dacd6'

def case(name,fn):
    try:
        detail=fn()
        return {'name':name,'passed':True,'detail':detail}
    except Exception as e:
        return {'name':name,'passed':False,'exception':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()}

def integer_fixed(n,places):
    sign='-' if n<0 else '';n=abs(n);scale=10**places
    return sign+str(n//scale)+'.'+str(n%scale).zfill(places)

def numeric_cases():
    rng=random.Random(7003);values=[0,1,-1,10,-10,99,-99,100,-100,101,-101,123456789,-123456789]
    values += [rng.randrange(-10**14,10**14) for _ in range(96)]
    checked=0
    for cents in values:
        canonical=integer_fixed(cents,2);sign='-' if cents<0 else '';whole,frac=canonical.lstrip('-').split('.')
        grouped=format(int(whole),',')
        for raw in [canonical,canonical+'0000',sign+'$'+grouped+'.'+frac,sign+grouped+'.'+frac]:
            parsed=typed_values.convert(raw,'currency_usd')
            assert parsed['status']=='parsed' and parsed['canonical']==canonical,(raw,parsed,canonical)
            checked+=1
        for raw in [canonical,canonical+'0000']:
            parsed=typed_values.convert(raw,'decimal_2','hours')
            assert parsed['canonical']==canonical,(raw,parsed)
            checked+=1
        rate=integer_fixed(cents,2)+'%';want=integer_fixed(cents,4)
        parsed=typed_values.convert(rate,'rate_percent')
        assert parsed['canonical']==want,(rate,parsed,want)
        checked+=1
    return {'seed':7003,'integer_values':len(values),'candidate_conversions':checked,'expected_arithmetic':'integer scaled units; no Decimal conversion used to derive expected strings'}

def invalid_numeric_cases():
    cases={
        'currency_usd':['+1.00','$-1.00','--1.00','1,23.00','0,001.00','1,0000.00','01.00','-0.00','1.001','NaN','Infinity','1e3','$ 1.00','(1.00)','1.00 USD','\u22121.00','\uff11.00','1_000.00','9'*25,'1.'+'0'*7],
        'decimal_2':['01.00','1,000.00','+1.00','1e2','1.000001','-0','1.00 HR','1 000.00','1.0.0','\u0661.00'],
        'rate_percent':['0.075','7.501%','-0%','7.5 %','7,50%','+7.50%','7.50%%','NaN%','1e2%']}
    checked=0
    for kind,raws in cases.items():
        for raw in raws:
            result=typed_values.convert(raw,kind)
            assert result['status']!='parsed',(kind,raw,result)
            assert result['canonical'] is None,(kind,raw,result)
            checked+=1
    large='999,999,999,999,999,999,999,999.990000'
    assert typed_values.convert(large,'currency_usd')['canonical']=='999999999999999999999999.99'
    return {'rejected_cases':checked,'maximum_supported_grouped_integer_passes':True}

def type_boundaries():
    for value,want in [('[X]','true'),('[ ]','false')]:assert typed_values.convert(value,'boolean_mark')['canonical']==want
    for value in ['[x]','true','false','X','[ V ]','1','0','']:
        assert typed_values.convert(value,'boolean_mark')['status']!='parsed',value
    for value in ['2024-02-29','0001-01-01','9999-12-31']:
        assert typed_values.convert(value,'date_iso')['canonical']==value
    for value in ['2023-02-29','0000-01-01','2026-13-01','2026-11-31','2026-1-01','26-01-01','2026-01-01T00:00:00']:
        assert typed_values.convert(value,'date_iso')['status']!='parsed',value
    for value in ['0019-GFCI','000007','A  B','First line\nSecond line','1 Main St, Unit 2']:
        for kind in ('text','identifier'):assert typed_values.convert(value,kind)['canonical']==value
    assert typed_values.convert(' e\u0301\r\n','text')['canonical']=='\u00e9'
    for kind in typed_values.SUPPORTED:
        assert typed_values.convert(None,kind)['status']=='missing'
        for raw in (0,False,{},[]):assert typed_values.convert(raw,kind)['status']=='unsupported_candidate_structure'
    assert typed_values.convert('x','unknown-type')['status']=='unsupported_type'
    assert typed_values.convert('1'*129,'currency_usd')['status']=='lexical_limit'
    return {'boolean_and_calendar_boundaries':True,'text_and_identifier_internal_content_preserved':True,'no_address_join':True,'missing_and_unsupported_structures_explicit':True}

def quantity_scope():
    for unit in ('BX','EA','HR','KT','PR'):
        p=typed_values.convert('2.0000 '+unit,'decimal_2','qty_unit')
        assert p['canonical']=='2.00' and p['quantity_unit_observed']==unit
    for raw in ['2.00 ZZ','2.00 ea','2.00  EA','2.00','2.00\tEA','2.00 EA EA']:
        assert typed_values.convert(raw,'decimal_2','qty_unit')['status']!='parsed',raw
    truth=original.expected();truth['expected_fields']=[];truth['expected_absences']=[]
    truth['expected_tables']=[{'table_id':'quantity','rows':[{'row_id':'r1','page_number':1,'cells':{'qty_unit':{'printed_text':'2.00 HR','normalized_value':'2.00','value_type':'decimal_2'}}}]}]
    pred={'fields':[],'tables':[{'page':1,'table_id':'quantity','columns':['qty_unit'],'rows':[{'values':['2.00 EA']}]}],'anchors':[],'pages':[],'parse_errors':[],'unmapped':[]}
    result=score.score_document(pred,truth,{'pages':['2.00 HR'],'coverage':{}})
    assert result['cells']['correct']==0 and result['normalized_cells']['correct']==1
    assert result['normalized_cells']['details'][0]['quantity_unit_observed']=='EA'
    return {'supported_units':5,'unsupported_or_ambiguous_forms_rejected':6,'documented_limitation':'Wrong but supported unit receives numeric normalized credit; raw unit retained and printed metric fails.'}

def answer_independence():
    assert list(inspect.signature(typed_values.convert).parameters)==['raw','value_type','slot']
    canonical_fields=('raw','value_type','slot','status','canonical')
    checked=0
    examples=[('$1,234.50','currency_usd','1234.50'),('-20.00','currency_usd','-20.00'),('[X]','boolean_mark','true'),('7.50%','rate_percent','0.0750'),('0007','identifier','0007')]
    for raw,kind,target in examples:
        first=typed_values.compare(raw,{'value_type':kind,'normalized_value':target},True)
        for other in ('999.00','wrong','',None,{},False):
            changed=typed_values.compare(raw,{'value_type':kind,'normalized_value':other,'printed_text':'do not inspect','bbox_pt':[0,0,999,999]},True)
            assert {k:first[k] for k in canonical_fields}=={k:changed[k] for k in canonical_fields}
            assert not changed['credited_exact']
            checked+=1
    return {'changed_answer_targets':checked,'candidate_conversion_identical':True,'expected_value_not_a_converter_parameter':True}

def denominator_cases():
    truth=original.expected()
    truth['expected_fields'][0]['value_type']='identifier'
    truth['expected_tables'][0]['rows'][0]['cells']['code'].update(normalized_value='A',value_type='identifier')
    truth['expected_tables'][0]['rows'][0]['cells']['price'].update(printed_text='$1.00',normalized_value='1.00',value_type='currency_usd')
    header=original.HEADER
    valid='<PAGE>'+original.block('ID: 007')+original.block('<table>'+header+'<tr><td>A</td><td>1.0</td></tr></table>','table')
    pred=baseline.prediction(valid,original.RULES)
    cases=0
    for completion in ('completed','timeout','oom','not_run_after_failure','missing_run_record'):
        s=score.score_document(pred,truth,{'pages':['ID: 007 Code Price A $1.00'],'coverage':{}},completion)
        assert (s['fields']['total'],s['normalized_fields']['total'],s['cells']['total'],s['normalized_cells']['total'])==(1,1,2,2)
        assert s['normalized_fields']['correct']==int(completion=='completed')
        assert s['normalized_cells']['correct']==2*int(completion=='completed')
        assert s['cells']['correct']==int(completion=='completed')
        cases+=1
    malformed=baseline.prediction(valid.replace('<td>A','<td rowspan>A'),original.RULES)
    bad=score.score_document(malformed,truth,{'pages':['ID: 007'],'coverage':{}})
    assert bad['parse_errors'] and bad['fields']['correct']==bad['normalized_fields']['correct']==bad['cells']['correct']==bad['normalized_cells']['correct']==0
    assert bad['normalized_cells']['total']==2
    missing=score.score_document(baseline.prediction('<PAGE>',original.RULES),truth,{'pages':[],'coverage':{}})
    assert missing['normalized_fields']['uncredited_reasons']=={'missing':1}
    assert missing['normalized_cells']['uncredited_reasons']=={'missing':2}
    unsupported=copy.deepcopy(truth);unsupported['expected_fields'][0]['value_type']='unsupported';unsupported['expected_tables'][0]['rows'][0]['cells']['price']['normalized_value']={}
    s=score.score_document(pred,unsupported,{'pages':[],'coverage':{}})
    assert s['normalized_fields']['uncredited_reasons']=={'unsupported_type':1}
    assert s['normalized_cells']['uncredited_reasons']=={'unsupported_normalized_target':1}
    return {'completion_states':cases,'printed_and_typed_denominators_equal':True,'parse_invalid_zero_credit':True,'unsupported_type_and_target_remain_counted':True}

def empty_absence_duplicates():
    pred=baseline.prediction('<PAGE>',original.RULES)
    pred['fields']=[{'page':1,'field_id':'optional','value':''} for _ in range(3)]
    s=score.score_document(pred,original.expected(),{'pages':[],'coverage':{}})
    assert s['fields']['unmatched_candidates']==2 and s['expected_absences']['surplus_candidates']==2
    assert s['expected_absences']['violations']==0 and s['expected_absences']['correct']==1
    return {'three_empty_occurrences':3,'surplus_count':2,'absence_violation_count':0}

def malformed_sequence(scratch):
    from unittest.mock import patch
    path=scratch/'sequence';path.mkdir()
    raw0='<PAGE>'+original.block('<table>'+original.HEADER+original.ROW,'table')
    raw1='<PAGE>'+original.block('ID: 007')+original.block('<table>'+original.HEADER+original.ROW+'</table>','table')
    fixtures=[{'fixture_id':'bad','split':'dev'},{'fixture_id':'good','split':'dev'},{'fixture_id':'absent','split':'dev'}];calls=[]
    truth=original.expected();truth['expected_fields'][0]['value_type']='identifier'
    for f,raw in zip(fixtures,(raw0,raw1)):
        name=f['fixture_id'];data=raw.encode();(path/(name+'.raw.txt')).write_bytes(data)
        original.dump(path/(name+'.observation.json'),{'raw_output':{'name':name+'.raw.txt','sha256_written':corpus.sha(data)}})
        calls.append({'fixture_id':name,'excluded':False,'status':'completed','observation':name+'.observation.json'})
    original.dump(path/'run-result.json',{'release':{},'calls':calls})
    loader=baseline.load_json
    with patch('baseline.read_release',return_value={}),patch('baseline.protocol',return_value={'fixtures':fixtures}),patch('baseline.expected_for',return_value=truth),patch('baseline.reference_for',return_value={'pages':['ID: 007 A $1'],'coverage':{}}),patch('baseline.load_json',side_effect=lambda p:original.RULES if p==release.HERE/'mapping.json' else loader(p)):
        baseline.score_run(path,path/'scores.json','CPU-TEST','CPU-TEST','dev','author')
    data=loader(path/'scores.json');results=data['scores']
    assert len(results)==3 and data['summary']['dev']['document_denominator']==3
    assert [s['fields']['correct'] for s in results]==[0,1,0]
    assert [s['normalized_fields']['correct'] for s in results]==[0,1,0]
    assert [s['normalized_fields']['total'] for s in results]==[1,1,1]
    assert results[-1]['completion']=='missing_run_record'
    return {'malformed_then_valid_then_absent_documents':3,'all_denominators_preserved':True,'later_valid_document_scored':True}

def main():
    head=original.git('rev-parse','HEAD')
    assert original.git('rev-parse','HEAD:qualification/baseline')==TREE
    assert original.git('rev-parse',CANDIDATE+':qualification/baseline')==TREE
    assert not original.git('status','--porcelain'),'Freeze reviewer helpers before decisive execution'
    tag=head[:8]+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')
    scratch=ROOT/'.scratch/wp0007-review-003'/tag;scratch.mkdir(parents=True)
    out=OWN/'reconciliation'/tag;out.mkdir(parents=True)
    command=[sys.executable,'-I','-B',str(release.HERE/'tests/test_baseline.py'),'-v']
    cp=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=120)
    (out/'author-tests.stdout.txt').write_bytes(cp.stdout);(out/'author-tests.stderr.txt').write_bytes(cp.stderr)
    seen,denied=original.content_audit()
    original.CANDIDATE=CANDIDATE;original.PUBLICATION=PUBLICATION
    old=original.probes(scratch)
    new=[case('independent_integer_arithmetic_numeric_oracle',numeric_cases),case('numeric_grammar_precision_and_sign_boundaries',invalid_numeric_cases),case('boolean_calendar_text_identifier_structures',type_boundaries),case('quantity_unit_scope_is_explicit',quantity_scope),case('candidate_conversion_independent_of_changed_answers',answer_independence),case('typed_printed_failure_and_unsupported_denominators',denominator_cases),case('empty_absence_duplicates_counted',empty_absence_duplicates),case('malformed_missing_document_score_run_continuation',lambda:malformed_sequence(scratch))]
    baseline.dev_check(scratch/'dev')
    reproduction=[];invariants=[]
    for path in sorted((scratch/'dev').glob('*.json')):
        data=path.read_bytes();published=(ROOT/'docs/evidence/WP-0007/eld-rd-astra/f807e0ac/dev'/path.name).read_bytes()
        reproduction.append({'file':path.name,'byte_identical':data==published,'sha256':corpus.sha(data),'bytes':len(data)})
        if path.name.endswith('.score.json'):
            current=json.loads(data);previous=corpus.load_json(ROOT/'docs/evidence/WP-0007/eld-rd-astra/a998b765/dev'/path.name)
            invariants.append({'file':path.name,'printed_fields_unchanged':current['fields']==previous['fields'],'printed_cells_unchanged':current['cells']==previous['cells'],'raw_text_errors_unchanged':current['text']==previous['text'],'raw_source_identity_unchanged':current['source']==previous['source'],'denominators_equal':current['fields']['total']==current['normalized_fields']['total'] and current['cells']['total']==current['normalized_cells']['total']})
    for child in ('dev','supervisor-stub','supervisor-root','sequence'):
        if (scratch/child).exists():shutil.copytree(scratch/child,out/'retained-scratch'/child)
    if (scratch/'supervisor-scores.json').exists():shutil.copyfile(scratch/'supervisor-scores.json',out/'retained-scratch/supervisor-scores.json')
    status={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'review_execution_head':head,'source_candidate':CANDIDATE,'source_tree':TREE,'author_publication':PUBLICATION,'coordinator_clarification':DESIGN,'python':sys.version,
            'author_suite':{'argv':command,'exit_code':cp.returncode},'original_independent_probes':old,'new_independent_probes':new,'dev_reproduction':reproduction,'retrospective_invariants':invariants,'synthetic_paths_opened':sorted(set(seen)),'denied_synthetic_access':denied,'model_modules':[m for m in sys.modules if m in ('torch','transformers')], 'runtime_roots_exist':{k:Path(p).exists() for k,p in release.protocol()['runtime_roots'].items()}}
    status['passed']=cp.returncode==0 and all(c['passed'] for c in old+new) and all(c['byte_identical'] for c in reproduction) and all(all(v for k,v in c.items() if k!='file') for c in invariants) and not denied and not status['model_modules']
    original.dump(out/'results.json',status)
    inventory=[]
    for path in sorted(out.rglob('*')):
        if path.is_file():
            data=path.read_bytes();inventory.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    original.dump(out/'inventory.json',{'entries':inventory})
    print(json.dumps({'evidence':str(out),'passed':status['passed'],'original_probes':len(old),'new_probes':len(new),'failed_probes':[x['name'] for x in old+new if not x['passed']],'dev_artifacts':len(reproduction),'synthetic_paths':len(set(seen)),'runtime_roots_exist':status['runtime_roots_exist']}))
    return int(not status['passed'])

if __name__=='__main__':raise SystemExit(main())
