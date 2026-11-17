"""Independent public-only source review; modes retain every failure and full object identities."""
import argparse,contextlib,copy,datetime,hashlib,html,importlib.abc,importlib.util,io,json,os,subprocess,sys,traceback,unittest
from pathlib import Path
OWN=Path(__file__).resolve().parent;ROOT=OWN.parents[4]
SOURCE='c0a1af638e807803b6014b3a93ecb7f9946ce6e1'
CHECKPOINT='93d6edb6656be30ff8c99fb908fe5cb64a2fcb43'
TREE='4477104eb2a3c73f496ef451cef9578f54d96518'
AUTHOR='docs/research/WP-0013/eld-mapping-author/005/evidence/attempt-1/'
sys.path.insert(0,str(ROOT))
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':
            raise RuntimeError('Forbidden review import: '+fullname)
sys.meta_path.insert(0,NoModel())
from qualification.mapping_v2 import mapper,scoring,release
from qualification.mapping_v2.common import protocol,verify_frozen_mappers,parse_native,sha
from qualification.mapping_v2.protocol.common import catalog
from qualification.mapping_v1.mapper import extract_prediction as v1
from qualification.mapping_v1.common import mapping,score_document
sys.path.insert(0,str(ROOT/'docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review'))
from public_examples import example
INPUTS={}
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def require(ok,why):
    if not ok:raise AssertionError(why)
def canonical(obj):return sha(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
def read(path):
    p=Path(path);p=p.relative_to(ROOT) if p.is_absolute() else p
    name=p.as_posix()
    require(not name.startswith('evaluation/mapping_v2/'),'Fresh input forbidden')
    raw=(ROOT/p).read_bytes()
    INPUTS[name]={'path':name,'bytes':len(raw),'sha256':sha(raw),'git_blob':git('hash-object','--',name).decode().strip()}
    return raw
def load(path):return json.loads(read(path))
def write(path,value):
    path.resolve().relative_to(OWN);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
def pin(out):
    require(not git('status','--porcelain').strip(),'Freeze clean helper before checks')
    require(git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()==TREE,'Wrong candidate tree')
    verify_frozen_mappers()
    paths=git('ls-tree','-r','--name-only',SOURCE,'qualification/mapping_v2','qualification/mapping_v1','qualification/coverage_v1','qualification/baseline','qualification/q0/harness/q0harness').decode().splitlines()
    records=[]
    for p in paths:
        raw=read(p);blob=git('rev-parse',SOURCE+':'+p).decode().strip()
        require(git('hash-object','--',p).decode().strip()==blob,'Source working/Git mismatch '+p)
        records.append(INPUTS[p])
    out.update(helper_freeze=git('rev-parse','HEAD').decode().strip(),reviewed_source=SOURCE,source_tree=TREE,source_inputs=records)
def block(text,box=(10,10,400,30),kind='text'):
    return '<BLOCK>'+kind+'['+','.join(map(str,box))+']<FORK>'+text
def table(rows,box=(10,300,900,900)):
    def cell(x):
        if isinstance(x,tuple):return '<td colspan="'+str(x[1])+'">'+html.escape(x[0])+'</td>'
        return '<td>'+html.escape(x)+'</td>'
    return block('<table>'+''.join('<tr>'+''.join(cell(x) for x in row)+'</tr>' for row in rows)+'</table>',box,'table')
def context(profile,headers=None,rows=None):
    t=profile['tables'][0]
    return table([headers or t['alias_headers'],*(rows if rows is not None else [['PUBLIC-ROW-42']+['literal-'+str(i) for i in range(1,len(t['columns']))]])])
def pred(*blocks):return mapper.extract_prediction(parse_native('<PAGE>'+''.join(blocks)))
def values(p,fid):return [x['value'] for x in p['fields'] if x['field_id']==fid]
def probes(out):
    checks=[]
    def check(name,fn):
        row={'name':name}
        try:row['evidence']=fn();row['status']='PASS'
        except BaseException:row.update(status='FAIL',failure=traceback.format_exc())
        checks.append(row)
    profiles=catalog()['profiles']
    for profile in profiles:
        for field in profile['fields']:
            for label in field['aliases']+field['canonical_labels']:
                def one(pr=profile,f=field,l=label):
                    p=pred(block(l+': PUBLIC-VALUE-42'),context(pr))
                    require(values(p,f['field_id'])==['PUBLIC-VALUE-42'],'Unique exact label not mapped')
                    return {'label':l,'target':f['field_id'],'prediction_sha256':canonical(p)}
                check('exact_catalog/'+profile['profile']+'/'+label,one)
        def column_permutation(pr=profile):
            t=pr['tables'][0];order=list(reversed(range(len(t['columns']))))
            headers=[(t['alias_headers'] if i%2 else t['canonical_headers'])[i] for i in order]
            row=['literal-'+str(i) for i in order];p=pred(context(pr,headers,[row]))
            require(len(p['tables'])==1 and p['tables'][0]['columns']==[t['columns'][i] for i in order],'Column identity/order changed')
            require(p['tables'][0]['rows'][0]['values']==row,'Row values reordered')
            return p['tables']
        check('mixed_permuted_header/'+profile['profile'],column_permutation)
    pr=profiles[0];fr=pr['fields'][0];fid=fr['field_id'];label=fr['aliases'][0];can=fr['canonical_labels'][0];ctx=context(pr)
    def no_field(*blocks):
        p=pred(*blocks);require(values(p,fid)==[],'Guard emitted affected field')
        return {'prediction_sha256':canonical(p),'decisions':[x for x in p['mapping_v2_decisions'] if x.get('field_id')==fid]}
    check('alias_without_profile',lambda:no_field(block(label+': PUBLIC-A')))
    check('canonical_alias_duplicate_suppresses_old',lambda:no_field(block(can+': PUBLIC-A'),block(label+': PUBLIC-A'),ctx))
    check('duplicate_distinct',lambda:no_field(block(label+': PUBLIC-A'),block(label+': PUBLIC-B'),ctx))
    check('duplicate_in_footer_counts',lambda:no_field(block(label+': PUBLIC-A'),block('Public prose '+can+' elsewhere',kind='footer'),ctx))
    check('duplicate_in_data_cell_counts',lambda:no_field(block(label+': PUBLIC-A'),context(pr,rows=[['PUBLIC-ROW',can,'literal','1 EA']])))
    check('two_profiles_no_alias_fallback',lambda:no_field(block(label+': PUBLIC-A'),ctx,context(profiles[1])))
    check('duplicate_schema_no_alias_fallback',lambda:no_field(block(label+': PUBLIC-A'),ctx,ctx))
    check('rejected_right_has_no_below_escape',lambda:no_field(table([[can,'PUBLIC-A'],['PUBLIC-B','OTHER']]),ctx))
    check('unknown_colon_value',lambda:no_field(table([[label,'Public caption: OTHER']]),ctx))
    check('additional_plain_cell',lambda:no_field(table([[label,'PUBLIC-A','EXTRA']]),ctx))
    check('internal_nbsp_not_normalized',lambda:no_field(block(label.replace(' ','\u00a0')+': PUBLIC-A'),ctx))
    check('case_not_folded',lambda:no_field(block(label.upper()+': PUBLIC-A'),ctx))
    check('double_colon_not_repaired',lambda:no_field(block(label+':: PUBLIC-A'),ctx))
    check('alias_inside_markup_abstains',lambda:no_field(block('<x title="'+label+': PUBLIC-A">body</x>'),ctx))
    check('right_and_below_equal_still_ambiguous',lambda:no_field(block(label,(10,10,100,20)),block('PUBLIC-A',(110,10,180,20)),block('PUBLIC-A',(10,25,100,35)),ctx))
    def malformed_header():
        t=pr['tables'][0];headers=[t['canonical_headers'][0],t['alias_headers'][0],*t['alias_headers'][2:]]
        p=pred(block(label+': PUBLIC-A'),context(pr,headers))
        require(not p['tables'] and not values(p,fid),'Collision selected a column')
        return p['mapping_v2_decisions']
    check('canonical_alias_header_collision',malformed_header)
    for name,rows in [('empty_key',[['','a','b','1']]),('equal_duplicate',[['K','a','b','1'],['K','a','b','1']]),('trimmed_duplicate',[['K','a','b','1'],[' K ','a','b','1']]),('different_duplicate',[['K','a','b','1'],['K','other','b','2']]),('short',[['K','a','b']]),('long',[['K','a','b','1','x']]),('span',[[('K',2),'a','b','1']]),('repeated_header',[['K','a','b','1'],pr['tables'][0]['alias_headers']])]:
        def guard(rr=rows):
            p=pred(context(pr,pr['tables'][0]['canonical_headers'],rr))
            require(not p['tables'],'Canonical affected table bypassed guard')
            return p['mapping_v2_decisions']
        check('canonical_table/'+name,guard)
    def profile_survives_badrow():
        p=pred(block(label+': PUBLIC-A'),context(pr,rows=[['short']]))
        require(values(p,fid)==['PUBLIC-A'] and not p['tables'],'Invalid row erased valid header evidence')
        return p['mapping_v2_decisions']
    check('profile_independent_of_data_validity',profile_survives_badrow)
    def untouched():
        raw='<PAGE>'+block('Contract ID: PUBLIC-C')+ctx
        native=parse_native(raw);before=v1(native,mapping());old=copy.deepcopy(native);after=mapper.extract_prediction(native)
        require(native==old,'Input native mutated')
        require([x for x in before['fields'] if x['field_id']=='contract_id']==[x for x in after['fields'] if x['field_id']=='contract_id'],'Untouched output changed')
        require(before['pages']==after['pages'] and before['unmapped']==after['unmapped'] and before['anchors']==after['anchors'],'Native/unmapped data changed')
        return {'before':canonical(before),'after':canonical(after)}
    check('untouched_and_input_immutability',untouched)
    def page_local():
        raw='<PAGE>'+block(label+': PUBLIC-A')+ctx+'<PAGE>'+block(label+': PUBLIC-A')+ctx
        p=mapper.extract_prediction(parse_native(raw));require(values(p,fid)==['PUBLIC-A','PUBLIC-A'],'Cross-page duplicate suppression')
        return p['fields']
    check('duplicate_scope_page_local',page_local)
    def empty_explicit():
        f=next(f for f in pr['fields'] if f['field_id']=='resident_contact')
        p=pred(table([[f['aliases'][0],'']]),ctx)
        require(values(p,f['field_id'])==[''],'Explicit blank lost')
        require(not values(pred(block(f['aliases'][0]),ctx),f['field_id']),'Omitted value inferred blank')
        return p['fields']
    check('explicit_blank_vs_omission',empty_explicit)
    def direct_originals():
        e,r,p,_=example();raw=p['ideal_native'];cmp=scoring.paired(raw,e,r,'completed')
        require(cmp['scores']['mapping_v2']==score_document(cmp['predictions']['mapping_v2'],e,r,'completed'),'Original v2 scorer bypass')
        from qualification.mapping_v2.protocol.scoring import score_policy
        ps=score_policy(cmp['predictions']['mapping_v2'],e,r,p)
        require(ps['metrics']['strict_correct_known_slots']==len(p['slots']),'Public ideal support lost')
        return {'comparison':canonical(cmp),'policy':ps}
    check('original_score_and_actual_policy',direct_originals)
    out['checks']=checks;out['status']='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
def tests(out,directory):
    sys.path.insert(0,str(ROOT/'qualification/mapping_v2/tests'))
    import test_runtime,test_release,test_mapper
    # Only owned CPU scratch is redirected; no source mutation or live observers.
    scratch=ROOT/'.scratch/wp0013-independent-source';scratch.mkdir(parents=True,exist_ok=True)
    test_runtime.SCRATCH=scratch;test_release.SCRATCH=scratch
    from qualification.mapping_v2.protocol.tests import test_protocol
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_mapper,test_release,test_runtime,test_protocol))
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    with (directory/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:f.write(stream.getvalue())
    out.update(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=[(str(t),d) for t,d in result.failures],errors=[(str(t),d) for t,d in result.errors],skipped=[(str(t),d) for t,d in result.skipped])
def history(out):
    from corpus import reference_for
    manifest=load('evaluation/manifests/corpus-manifest.json');fixtures={f['fixture_id']:f for f in manifest['fixtures']}
    authored=load(AUTHOR+'historical-regression.json')
    prior1=load('docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json')
    old1={d['fixture_id']:d['mapping_v1_score'] for d in prior1['documents']}
    old0={}
    for prefix in ['docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6','docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d','docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca']:
        packet=load(prefix+'/scores.json')
        for row in packet['scores']:old0[(row['fixture_id'],'recovery' if 'recovery' in prefix else 'primary')]=row
    exposed={}
    for group,prefix,corpus in [('wp9_exposed','docs/evidence/WP-0009/eld-mapping-author/007/attempt-1','evaluation/mapping_v1/corpus/r1/'),('wp11_exposed','docs/evidence/WP-0011/eld-mapping-author/005/attempt-1','evaluation/coverage_v1/corpus/r1/')]:
        for row in load(prefix+'/scores.json')['records']:exposed[row['fixture_id']]=(row,corpus)
    records=[];changes=[]
    metrics={'fields':'credited_exact','cells':'credited_exact','normalized_fields':'credited_exact','normalized_cells':'credited_exact','rows':'exact','expected_absences':'verified_absent'}
    for a in authored['documents']+authored['supplement_separate']:
        fid=a['fixture_id'];raw=read(a['raw_path']) if (ROOT/a['raw_path']).exists() else b''
        require(sha(raw)==a['raw_sha256'],'Raw identity mismatch')
        if a['group'] in ('wp7_primary','supplement'):
            fx=fixtures[fid];e=load(fx['expected_ground_truth_path'])
            parent=next(f for f in fixtures.values() if f['family_id']==fx['family_id'] and f['variant_kind']=='v0_clean')
            read(parent['file_path'])
            if fx['variant_kind']=='v3_hybrid':read(fx['source_record_path'])
            ref=reference_for(fx,allow_test=True)
            before0=old0[(fid,'recovery' if a['group']=='supplement' else 'primary')]
            before1=prior1['supplement_separate'][0]['mapping_v1_score'] if a['group']=='supplement' else old1[fid]
            originals={k:{key:value for key,value in v.items() if key!='raw_sha256'} for k,v in [('b0',before0),('mapping_v1',before1)]}
        else:
            old,corpus=exposed[fid];e=load(corpus+'expected/'+fid+'.json');ref=load(corpus+'reference/'+fid+'.json');originals=old['scores']
        current=scoring.paired(raw.decode(),e,ref,a['completion'])
        for name in ('b0','mapping_v1'):
            require(current['scores'][name]==originals[name],'Frozen historical full score changed')
            if fid in exposed:require(current['predictions'][name]==exposed[fid][0]['predictions'][name],'Historical full prediction changed')
        require(current['scores']==a['scores'] and current['predictions']['mapping_v2']==a['v2_prediction'],'Author full-object reproduction mismatch')
        delta={}
        for metric,credit in metrics.items():
            left=current['scores']['mapping_v1'][metric];right=current['scores']['mapping_v2'][metric]
            require(len(left['details'])==len(right['details']),'Denominator changed')
            gain=loss=0
            for ordinal,(x,y) in enumerate(zip(left['details'],right['details'])):
                if x[credit]!=y[credit]:
                    gain+=int(y[credit]);loss+=int(x[credit])
                    changes.append({'fixture_id':fid,'group':a['group'],'metric':metric,'ordinal':ordinal,'direction':'gain' if y[credit] else 'loss','before':x,'after':y,'v2_decisions':current['predictions']['mapping_v2']['mapping_v2_decisions']})
            delta[metric]={'total':left['total'],'before_correct':left['correct'],'v2_correct':right['correct'],'gains':gain,'losses':loss}
        require(delta==a['changes_from_v1'],'Author detailed gain/loss totals mismatch')
        records.append({'fixture_id':fid,'group':a['group'],'completion':a['completion'],'raw_path':a['raw_path'],'raw_sha256':sha(raw),'full_scores_sha256':canonical(current['scores']),'full_predictions_sha256':canonical(current['predictions']),'author_v2_prediction_equal':True,'historical_full_scores_equal':True,'changes_from_v1':delta})
    require(len(records)==43 and sum(r['group']=='supplement' for r in records)==1,'Primary/recovery frame changed')
    out.update(status='PASS',documents=records,changed_slots=changes,primary_documents=42,separate_recovery_documents=1,original_missing_raw=authored['original_missing_raw'])
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['probes','tests','history']);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.resolve().relative_to(OWN);require(not a.out.exists(),'Retain prior attempt; output already exists')
    out={'schema':'eld-wp13-independent-source-checks/1','mode':a.mode,'status':'FAIL','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        pin(out);a.out.mkdir(parents=True,exist_ok=False)
        if a.mode=='tests':tests(out,a.out)
        else:globals()[a.mode](out)
    except BaseException:out['failure']=traceback.format_exc()
    out['input_files']=sorted(INPUTS.values(),key=lambda x:x['path'])
    out['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(a.out/'result.json',out)
    print(json.dumps({'status':out['status'],'mode':a.mode,'checks':len(out.get('checks',[])),'tests':out.get('tests'),'primary_documents':out.get('primary_documents'),'failure':out.get('failure'),'failed_checks':[c['name'] for c in out.get('checks',[]) if c['status']!='PASS']}))
    return int(out['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
