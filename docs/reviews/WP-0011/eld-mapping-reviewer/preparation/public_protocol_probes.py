"""Public synthetic counterexamples against immutable B0/v1; no fresh inputs."""
import argparse,hashlib,importlib.abc,json,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':raise RuntimeError('CPU public probes prohibit model/renderer imports')
sys.meta_path.insert(0,NoModel());sys.path.insert(0,str(ROOT))
from qualification.mapping_v1.common import mapping,parse_native,baseline_prediction,score_document
from qualification.mapping_v1.mapper import extract_prediction
from typed_values import compare
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def raw(body):return '<PAGE><BLOCK>text[0,0,1000,1000]<FORK>'+body
def table(rows):return '<PAGE><BLOCK>table[0,0,900,900]<FORK><table>'+''.join('<tr>'+''.join('<td>'+x+'</td>' for x in row)+'</tr>' for row in rows)+'</table>'
def predictions(text):
    parsed=parse_native(text);return [f(parsed,mapping()) for f in (baseline_prediction,extract_prediction)]
def truth(value='PUBLIC-ONLY'):
    return {'fixture_id':'SYNTHETIC-PROBE','family_id':'NOT-A-FRESH-FAMILY','split':'synthetic-only','variant_kind':'public-probe','page_count':1,
        'expected_fields':[{'field_id':'invoice_number','page_number':1,'printed_text':value,'normalized_value':value,'value_type':'identifier'}],
        'expected_tables':[],'expected_absences':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
def score(pred,completion='completed',value='PUBLIC-ONLY'):return score_document(pred,truth(value),{'pages':['Invoice No: '+value],'coverage':{'synthetic_only':True}},completion)
def require(ok,message):
    if not ok:raise AssertionError(message)

def same_row_known_label():
    a,b=predictions(table([['Invoice No:','PUBLIC-ONLY']]))
    require(not a['fields'] and b['fields'][0]['value']=='PUBLIC-ONLY','Expected public same-row B0/v1 support distinction')
    return {'b0_fields':a['fields'],'v1_fields':b['fields'],'conclusion':'Known label and v1 support alone do not establish B0 control support.'}
def inline_control():
    a,b=predictions(raw('Invoice No: PUBLIC-ONLY'));scores=[score(x) for x in (a,b)]
    require(all(s['fields']['correct']==s['fields']['total']==1 for s in scores),'Canonical public inline control support failed')
    return {'field_counts':[s['fields'] for s in scores],'conclusion':'A canonical ideal-native witness can demonstrate mapping support without claiming OCR success.'}
def coordinate_collision():
    text=raw('Unrelated visible payload');parsed=parse_native(text)
    payload='\n'.join(b['text'] for p in parsed['pages'] for b in p['blocks'])
    require('1000' in text and '1000' not in payload,'Coordinate-only collision absent')
    return {'raw_contains_target':True,'visible_payload_contains_target':False,'conclusion':'Searching all raw markup confuses coordinates with recognized text.'}
def wrong_slot_presence():
    text=raw('Invoice No: 00987')+'<BLOCK>text[0,100,900,150]<FORK>Work Order ID: 00123';a,b=predictions(text)
    require('00123' in text and all(score(x,value='00123')['fields']['correct']==0 for x in (a,b)),'Wrong-slot counterexample not reproduced')
    return {'fields':a['fields'],'expected_invoice':'00123','conclusion':'Same-page value presence does not prove semantic slot association; leading zeroes stay literal.'}
def repeated_value_ambiguity():
    text=raw('Invoice No: 00123')+'<BLOCK>text[0,100,900,150]<FORK>Work Order ID: 00123';a,b=predictions(text)
    require(text.count('00123')==2 and len(a['fields'])==2,'Repeated occurrence counterexample absent')
    return {'occurrences':2,'fields':a['fields'],'conclusion':'A target-value occurrence needs explicit multiplicity and slot/row identity; a global presence flag is insufficient.'}
def parse_failure_overlap():
    a,b=predictions(raw('Invoice No: PUBLIC-ONLY')+'<BLOCK>not-a-valid-header')
    scores=[score(x) for x in (a,b)]
    require(all(s['parse_errors'] and s['fields']['details'][0]['observed_exact'] and not s['fields']['details'][0]['credited_exact'] for s in scores),'Global parse eligibility counterexample absent')
    return {'parse_errors':scores[0]['parse_errors'],'field':scores[0]['fields']['details'][0],'conclusion':'A parse defect can withhold end-to-end credit while the local field evidence is exact; diagnostic attribution must not collapse these stages.'}
def unavailable_output():
    a,b=predictions('');scores=[score(x,'not_run_after_failure') for x in (a,b)]
    require(all(s['document_denominator']==1 and s['fields']['total']==1 and s['fields']['correct']==0 and not s['eligible_for_exact_credit'] for s in scores),'Unavailable denominator changed')
    return {'completion':scores[0]['completion'],'field_counts':scores[0]['fields'],'legacy_text':scores[0]['text'],'conclusion':'Retain legacy accounting but mark new stage observations unavailable; do not interpret empty accounting predictions as measured recognition errors or zero-error successes.'}
def unit_identity():
    target={'printed_text':'2 EA','normalized_value':'2.00','value_type':'decimal_2'}
    same=compare('2 EA',target,True,'qty_unit');different=compare('2 HR',target,True,'qty_unit')
    require(same['credited_exact'] and different['credited_exact'] and same['quantity_unit_observed']!=different['quantity_unit_observed'],'Frozen numeric-only unit behavior changed')
    return {'same_unit':same,'different_supported_unit':different,'conclusion':'Legacy typed quantity credit validates allowed units but compares numeric magnitude, so diagnostic unit identity must be separate.'}
def leading_zero_identifier():
    target={'printed_text':'00123','normalized_value':'00123','value_type':'identifier'}
    preserved=compare('00123',target,True,'invoice_number');dropped=compare('123',target,True,'invoice_number')
    require(preserved['credited_exact'] and not dropped['credited_exact'],'Identifier leading-zero semantics changed')
    return {'preserved':preserved,'dropped':dropped,'conclusion':'Identifier presence/canonicalization must not erase leading zeroes or use numeric equivalence.'}
def exact_table_header():
    rules=mapping();t=rules['tables'][0];headers=t['headers'];values=['PUBLIC-'+str(i) for i in range(len(headers))]
    clean=predictions(table([headers,values]));changed=list(headers);changed[0]=changed[0].swapcase();other=predictions(table([changed,values]))
    require(all(len(x['tables'])==1 for x in clean) and all(not x['tables'] for x in other),'Exact header support distinction absent')
    return {'control_table_id':t['table_id'],'control_headers':headers,'changed_header':changed[0],'rows_present_after_change':len(other[0]['pages'][0]['blocks'][0]['rows']),'conclusion':'Parsed rows/value presence can survive an unsupported exact-header vocabulary change; structure and vocabulary support are distinct.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.resolve().relative_to(Path(__file__).resolve().parent)
    out={'schema':'eld-wp0011-public-review-probes/1','synthetic_only':True,'head':git('rev-parse','HEAD').decode().strip(),'source_inventory':[],'checks':[]}
    for prefix,tree in [('qualification/baseline','deae8e826f4770e880374c68e6a56c8c65b6f8a3'),('qualification/mapping_v1','59f66d0d3d9be145a43efcc9258eb260d3ef2f00')]:
        require(git('rev-parse','HEAD:'+prefix).decode().strip()==tree,'Protected source tree changed')
        for path in git('ls-tree','-r','--name-only','HEAD','--',prefix).decode().splitlines():
            data=(ROOT/path).read_bytes();require(data==git('show','HEAD:'+path),'Working source changed')
            out['source_inventory'].append({'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':git('rev-parse','HEAD:'+path).decode().strip()})
    for probe in [same_row_known_label,inline_control,coordinate_collision,wrong_slot_presence,repeated_value_ambiguity,parse_failure_overlap,unavailable_output,unit_identity,leading_zero_identifier,exact_table_header]:
        try:out['checks'].append({'probe':probe.__name__,'status':'PASS','evidence':probe()})
        except Exception:out['checks'].append({'probe':probe.__name__,'status':'FAIL','traceback':traceback.format_exc()})
    out['failures']=sum(x['status']=='FAIL' for x in out['checks']);out['model_imports']=[k for k in sys.modules if k.split('.')[0] in ('torch','transformers','triton','pypdfium2')]
    with a.out.open('x',encoding='utf-8',newline='\n') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps({'checks':len(out['checks']),'failures':out['failures'],'model_imports':out['model_imports']}));return bool(out['failures'] or out['model_imports'])
if __name__=='__main__':raise SystemExit(main())
