"""Public reviewer probes of unchanged legacy metric/guard boundaries, not a v2 mapper/scorer."""
import argparse
import copy
import datetime
import hashlib
import html
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[5];OWN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':
            raise RuntimeError('CPU reviewer preparation prohibits model/renderer imports: '+fullname)
sys.meta_path.insert(0,NoModel())
from qualification.mapping_v1.common import parse_native,baseline_prediction,mapping,score_document
from qualification.mapping_v1.mapper import extract_prediction

BASE='47fbc7612e4a08cf1960ad7ac01bd2843ae645e5'
TREES={'qualification/baseline':'deae8e826f4770e880374c68e6a56c8c65b6f8a3',
       'qualification/mapping_v1':'59f66d0d3d9be145a43efcc9258eb260d3ef2f00',
       'qualification/coverage_v1':'6bdab544c9fe26cbf093cc765212db2a2e7a97a5',
       'qualification/q0/harness/q0harness':'fee7218eb233438cce7c583be1527b5c549930f0'}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def require(value,message):
    if not value:raise AssertionError(message)
def write(path,value):
    path.resolve().relative_to(OWN);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def identities():
    out=[]
    for prefix,tree in TREES.items():
        require(git('rev-parse','HEAD:'+prefix).decode().strip()==tree,'Legacy tree changed: '+prefix)
        for name in git('ls-tree','-r','--name-only','HEAD','--',prefix).decode().splitlines():
            blob=git('rev-parse','HEAD:'+name).decode().strip();raw=git('show','HEAD:'+name);working=(ROOT/name).read_bytes()
            require(git('hash-object','--',name).decode().strip()==blob,'Uncommitted legacy source: '+name)
            require(raw==working or raw==working.replace(b'\r\n',b'\n'),'Unexplained representation: '+name)
            out.append({'path':name,'git_blob':blob,'bytes_git':len(raw),'sha256_git':sha(raw),'bytes_working':len(working),'sha256_working':sha(working)})
    return out
def expected(field_id='work_order_id',printed='PUB-0042',value_type='identifier',normalized=None,absence=False):
    result={'fixture_id':'PUBLIC-PROBE','family_id':'PUBLIC-PROBE','split':'reviewer_public','variant_kind':'probe','page_count':1,
            'expected_fields':[],'expected_tables':[],'expected_absences':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
    if absence:result['expected_absences']=[{'field_id':field_id,'page_number':1,'expected_state':'absent_blank'}]
    else:result['expected_fields']=[{'field_id':field_id,'page_number':1,'printed_text':printed,'normalized_value':printed if normalized is None else normalized,'value_type':value_type}]
    return result
def text(*values):return '<PAGE>'+''.join('<BLOCK>text[0,0,900,20]<FORK>'+x for x in values)
def table(rows):return '<PAGE><BLOCK>table[0,0,900,900]<FORK><table>'+''.join('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table>'
def pair(raw,e,completion='completed'):
    parsed=parse_native(raw);old=copy.deepcopy(parsed);rules=mapping();saved=copy.deepcopy(rules)
    predictions={'b0':baseline_prediction(parsed,rules),'mapping_v1':extract_prediction(parsed,rules)}
    require(parsed==old and rules==saved,'Legacy mapper modified inputs')
    scores={k:score_document(v,e,{'pages':['Independent generic public probe'],'coverage':{}},completion) for k,v in predictions.items()}
    return {'raw':raw,'expected':e,'completion':completion,'predictions':predictions,'scores':scores}
def compact(result):
    return {**{k:v for k,v in result.items() if k!='scores'},'scores':{m:{k:s[k] for k in ('eligible_for_exact_credit','fields','normalized_fields','cells','expected_absences','parse_errors')} for m,s in result['scores'].items()}}

def run():
    report={'schema':'eld-wp13-public-legacy-boundaries/1','status':'FAILED','base_commit':BASE,
            'helper_commit':git('rev-parse','HEAD').decode().strip(),'helper_sha256':sha(Path(__file__).read_bytes()),
            'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':[],
            'scope':'Only unchanged B0/v1 public counterexamples. No v2 implementation, policy scorer, fresh fixture or protocol acceptance.'}
    def check(name,produce,assertion,meaning):
        row={'name':name,'meaning':meaning};report['checks'].append(row)
        try:
            result=produce();row['evidence']=compact(result);assertion(result);row['status']='PASS'
        except Exception:row['status']='FAIL';row['error']=traceback.format_exc()
    def exact_with_surplus(r,n):
        for s in r['scores'].values():require(s['fields']['correct']==n and s['fields']['total']==1 and s['fields']['unmatched_candidates']==1,'First-candidate/surplus boundary changed')
    try:
        report['legacy_inputs']=identities()
        check('duplicate_equal_first_credit',lambda:pair(text('Work Order ID: PUB-0042','Work Order ID: PUB-0042'),expected()),lambda r:exact_with_surplus(r,1),'Duplicate-equal candidates can receive original exact credit; required abstention needs independent cardinality accounting.')
        check('conflict_first_credit',lambda:pair(text('Work Order ID: PUB-0042','Work Order ID: PUB-9999'),expected()),lambda r:exact_with_surplus(r,1),'A conflicting surplus can coexist with full original field credit.')
        check('conflict_order_changes_credit',lambda:pair(text('Work Order ID: PUB-9999','Work Order ID: PUB-0042'),expected()),lambda r:exact_with_surplus(r,0),'Original scorer candidate order is not a conflict adjudication policy.')
        check('canonical_alias_duplicate_identity',lambda:pair(text('Work Order ID: PUB-0042','Ticket Number: PUB-9999'),expected()),lambda r:exact_with_surplus(r,1),'Two canonical legacy labels can name one field identity; guards must not count only identical spellings.')
        def fallback(r):
            fields=r['predictions']['mapping_v1']['fields'];require(fields and all(f.get('association')!='immediate_right_neighbor' for f in fields),'Expected rejected-right-neighbor fallback evidence')
        check('duplicate_guard_falls_back',lambda:pair(table([['Invoice No:','PUB-0042'],['Invoice No:','PUB-9999']]),expected('invoice_no')),fallback,'v1 rejecting its right-neighbor treatment is not a global abstention.')
        def below(r):require(r['predictions']['mapping_v1']['fields'][0]['value']=='OTHER','Below-row fallback not observed')
        check('ambiguous_orientation_falls_back',lambda:pair(table([['Invoice No:','PUB-0042'],['OTHER','MORE']]),expected('invoice_no')),below,'Rejecting ambiguous right/below orientation can retain another legacy value.')
        def one(r):
            for s in r['scores'].values():require(s['fields']['correct']==1,'Expected legacy substring recognition')
        check('unknown_prefix_contains_known_label',lambda:pair(text('Unknown Work Order ID: PUB-0042'),expected()),one,'Exact whole-label and contextual alias rules must be explicit; legacy inline matching accepts a known substring.')
        def absent(r,n):
            for s in r['scores'].values():require(s['expected_absences']['correct']==n and s['expected_absences']['total']==1,'Blank/absence boundary changed')
        check('explicit_blank_is_verified_absence',lambda:pair(text('Resident Contact'),expected('resident_contact',absence=True)),lambda r:absent(r,1),'A recognized blank slot is different from no candidate.')
        check('no_candidate_is_not_verified_absence',lambda:pair(text('Unknown record'),expected('resident_contact',absence=True)),lambda r:absent(r,0),'No assignment is not original factual absence credit or necessarily policy success.')
        def unavailable(r):
            for s in r['scores'].values():require(not s['eligible_for_exact_credit'] and s['fields']['correct']==0 and s['fields']['total']==1,'Unavailable denominator was lost')
        check('failed_completion_retains_denominator',lambda:pair(text('Work Order ID: PUB-0042'),expected(),'failed'),unavailable,'Observed-looking content from a failed call remains ineligible; unavailable must not become a compliant abstention.')
        check('parse_error_retains_denominator',lambda:pair(text('Work Order ID: PUB-0042')+'<BLOCK>invalid',expected()),unavailable,'Invalid native evidence retains full denominators and cannot establish successful guard behavior.')
        def quantity():
            e=expected('qty_unit','2.00 EA','decimal_2','2.00');e['expected_fields'][0]['quantity_unit']='EA';r=pair(text('Unknown quantity'),e)
            for name,p in r['predictions'].items():
                p['fields']=[{'field_id':'qty_unit','page':1,'value':'2.00 HR','label':'public synthetic candidate','location':[0]}]
                r['scores'][name]=score_document(p,e,{'pages':['2.00 EA'],'coverage':{}},'completed')
            return r
        def unit_limit(r):
            for s in r['scores'].values():require(s['fields']['correct']==0 and s['normalized_fields']['correct']==1 and s['normalized_fields']['details'][0]['quantity_unit_observed']=='HR','Frozen numeric/unit separation changed')
        check('valid_wrong_unit_can_get_numeric_credit',quantity,unit_limit,'Valid unit, exact numeric value and literal expected unit identity are different; original typed scores remain immutable.')
        def leading_zero(r):
            for s in r['scores'].values():require(s['fields']['correct']==s['normalized_fields']['correct']==0,'Identifier zero repair was introduced')
        check('identifier_zeroes_not_repaired',lambda:pair(text('Work Order ID: 42'),expected(printed='0042')),leading_zero,'Do not change identifier spelling to improve coverage.')
        report['status']='PASS' if all(x['status']=='PASS' for x in report['checks']) else 'FAIL'
    except Exception:report['error']=traceback.format_exc()
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();return report

def inventory(output):
    require(not git('status','--porcelain').strip(),'Commit deliverable before inventory')
    def listing(rev):return {x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0].decode() for x in git('ls-tree','-r','-z',rev).split(b'\0') if x}
    head=git('rev-parse','HEAD').decode().strip();before=listing(BASE);after=listing(head)
    require(all(after.get(k)==v for k,v in before.items()),'Previously committed artifact changed')
    added=sorted(set(after)-set(before));require(all(p.startswith(OWN.relative_to(ROOT).as_posix()+'/') for p in added),'Unowned change')
    rows=[]
    for path in added:
        data=git('show',head+':'+path);require(data==(ROOT/path).read_bytes(),'Working/Git bytes differ')
        rows.append({'path':path,'git_mode_type_blob':after[path],'bytes':len(data),'sha256':sha(data)})
    write(output,{'schema':'eld-reviewer-preliminary-inventory/1','base_commit':BASE,'deliverable_commit':head,'preserved_paths':len(before),'files':rows})
    return {'files':len(rows),'preserved_paths':len(before),'inventory_sha256':sha(output.read_bytes())}
def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('probe','inventory'));p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.command=='inventory':print(json.dumps(inventory(a.out)));return 0
    result=run();write(a.out,result);print(json.dumps({'status':result['status'],'checks':len(result['checks']),'failures':[x['name'] for x in result['checks'] if x['status']!='PASS']}));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
