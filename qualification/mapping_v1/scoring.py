"""Reference-side loader and paired comparison; exact unchanged B0 comparator."""
import json
from .common import baseline_prediction,parse_native,score_document,summarize,mapping,sha,load_json,write
from .mapper import extract_prediction
from .release import read_release,protocol,schedule,fixture,read_artifact,require


def validate_expected_reference(expected,reference,fx):
    require(all(isinstance(expected.get(k),list) for k in ('expected_fields','expected_tables','expected_absences','page_sentinels','expected_adjacent_page_pairs','cross_page_links')),'Expected schema lists missing')
    require(all(isinstance(expected.get(k),str) for k in ('fixture_id','family_id','split','variant_kind')),'Expected metadata types missing')
    require(expected['fixture_id']==fx['fixture_id'] and expected['family_id']==fx['family_id'] and expected['page_count']==fx['page_count'],'Expected fixture identity mismatch')
    require(isinstance(reference.get('pages'),list) and len(reference['pages'])==fx['page_count'] and
            all(isinstance(p,str) for p in reference['pages']) and isinstance(reference.get('coverage'),dict),'Reference schema incompatible')
    for field in expected['expected_fields']:
        require(all(k in field for k in ('field_id','page_number','printed_text','normalized_value','value_type')),'Field schema incompatible')
    for table in expected['expected_tables']:
        require(isinstance(table.get('rows'),list) and isinstance(table.get('table_id'),str),'Table schema incompatible')
        for row in table['rows']:
            require(all(k in row for k in ('row_id','page_number','cells')) and isinstance(row['cells'],dict),'Row schema incompatible')
            for cell in row['cells'].values():require(all(k in cell for k in ('printed_text','normalized_value','value_type')),'Cell schema incompatible')
    return expected,reference


def paired(raw,expected,reference,completion,rules=None):
    rules=mapping() if rules is None else rules
    parsed=parse_native(raw)
    b0=baseline_prediction(parsed,rules);v1=extract_prediction(parsed,rules)
    scores={key:score_document(pred,expected,reference,completion) for key,pred in [('b0',b0),('mapping_v1',v1)]}
    return {'raw_sha256':sha(raw.encode('utf-8')),'completion':completion,'predictions':{'b0':b0,'mapping_v1':v1},'scores':scores}


def score_run(run,output,authority,release_path,owner):
    from pathlib import Path
    r=read_release(authority,release_path,owner,execution=False);p=protocol();run=Path(run).resolve()
    run.relative_to(Path(r['runtime_root']).resolve()/'runs'/owner)
    result=load_json(run/'run-result.json');require(result['release']==r,'Run/release mismatch')
    planned=schedule(p,owner)
    require([{k:c[k] for k in ('fixture_id','kind','excluded')} for c in result['calls']]==planned,'Run denominator/schedule mismatch')
    records=[]
    for call in result['calls']:
        if call['excluded']:continue
        fx=fixture(p,call['fixture_id']);art={a['role']:a for a in fx['artifacts']}
        expected,reference=validate_expected_reference(json.loads(read_artifact(r,p,art['expected'])),json.loads(read_artifact(r,p,art['reference'])),fx)
        raw=''
        if call['observation']:
            obs_path=(run/call['observation']).resolve();obs_path.relative_to(run)
            obs=load_json(obs_path)
            if 'raw_output' in obs:
                raw_path=(obs_path.parent/obs['raw_output']['name']).resolve();raw_path.relative_to(run)
                data=raw_path.read_bytes();require(sha(data)==obs['raw_output']['sha256_written'],'Retained raw hash mismatch');raw=data.decode('utf-8')
        records.append({'fixture_id':fx['fixture_id'],**paired(raw,expected,reference,call['status'])})
    packet={'schema':'eld-mapping-v1-paired/1','run_result_sha256':sha((run/'run-result.json').read_bytes()),'records':records,
            'summary':{key:summarize([x['scores'][key] for x in records]) for key in ('b0','mapping_v1')},
            'interpretation':'One raw observation per document; changed association only, not model recognition or latency improvement.'}
    write(output,packet)
