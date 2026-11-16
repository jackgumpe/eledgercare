"""Independent selected-source review. CPU only; no sealed/fresh inputs or model imports."""
from pathlib import Path
import argparse,ast,copy,datetime,hashlib,html,importlib.abc,io,json,os,subprocess,sys,tempfile,threading,time,unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[5]
OWN=Path(__file__).resolve().parent
SOURCE='b95c12d2fd8d71598a1e9c523182cd1a2f3ee121'
SCRATCH=ROOT/'.scratch/wp0009-reviewer/source-006'
sys.path.insert(0,str(ROOT))
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':raise RuntimeError('Reviewer CPU import boundary: '+fullname)
sys.meta_path.insert(0,NoModel())
from qualification.mapping_v1.common import ROOT as MODULE_ROOT,protocol,sha,git,load_json,mapping,parse_native,baseline_prediction,score_document,summarize
from qualification.mapping_v1.mapper import extract_prediction
from qualification.mapping_v1 import release,scoring,runtime
from corpus import reference_for

RESULTS={}
def table(rows):return '<PAGE><BLOCK>table[0,0,900,900]<FORK><table>'+''.join('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table>'

class IndependentTests(unittest.TestCase):
    def test_one_treatment_ast_isolation(self):
        before=next(x for x in ast.parse((ROOT/'qualification/baseline/native.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='extract_prediction')
        after=next(x for x in ast.parse((ROOT/'qualification/mapping_v1/mapper.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='extract_prediction')
        fields_index=next(i for i,x in enumerate(after.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fields' for t in x.targets))
        # labels and by_label are two AST assignments despite sharing a physical line.
        after.body=after.body[:4]+after.body[fields_index:]
        class StripTreatment(ast.NodeTransformer):
            def visit_For(self,node):
                if ast.unparse(node.target)=='(ci, c)' and any(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='adjacent' for t in x.targets) for x in node.body):
                    node.body=[x for x in node.body if not(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='adjacent' for t in x.targets))]
                    idx=next(i for i,x in enumerate(node.body) if isinstance(x,ast.If) and 'adjacent' in ast.unparse(x.test))
                    node.body[idx]=node.body[idx].orelse[0]
                return self.generic_visit(node)
        after=StripTreatment().visit(after)
        self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))
        self.assertEqual(git('rev-parse','e84d584a1fecfe253d0c1fd1c7067d739f677be1:qualification/mapping_v1/mapper.py'),git('rev-parse',SOURCE+':qualification/mapping_v1/mapper.py'))

    def test_generic_guard_cases_and_provenance(self):
        cases=[('horizontal',table([['Invoice No:','CASE-003'],['Due Date:','2032-07-01']]),True),
          ('column_headers',table([['Invoice No:','Due Date:'],['CASE-003','2032-07-01']]),False),
          ('empty',table([['Invoice No:',' ']]),False),('unknown_colon',table([['Invoice No:','Unrecognized heading:']]),False),
          ('label_substring',table([['Invoice No:','unread Terms: clause']]),False),
          ('plain_below',table([['Invoice No:','CASE-003'],['OTHER','']]),False),
          ('second_right',table([['Invoice No:','CASE-003','OTHER']]),False),
          ('alias_duplicate',table([['Work Order ID:','CASE-003']])+table([['Ticket Number:','OTHER']]).replace('<PAGE>',''),False),
          ('inline_duplicate',table([['Invoice No:','CASE-003']])+'<BLOCK>text[0,0,900,900]<FORK>Invoice No: OTHER',False),
          ('unknown_label',table([['Unseen key:','CASE-003']]),False)]
        details=[]
        for name,raw,changed in cases:
            with self.subTest(name=name):
                parsed=parse_native(raw);saved=copy.deepcopy(parsed);rules=mapping();old=baseline_prediction(parsed,rules);new=extract_prediction(parsed,rules)
                self.assertEqual(parsed,saved);self.assertEqual(old['tables'],new['tables']);self.assertEqual(old['unmapped'],new['unmapped'])
                self.assertEqual(old!=new,changed)
                for f in new['fields']:
                    if f.get('association')=='immediate_right_neighbor':
                        bi,ri,ci=f['value_location'];self.assertEqual(f['value'],parsed['pages'][f['page']-1]['blocks'][bi]['rows'][ri][ci]['text'])
                details.append({'case':name,'changed':changed,'old_fields':old['fields'],'new_fields':new['fields']})
        RESULTS['independent_guard_cases']=details

    def test_frozen_sentinel_policy_matches_authorized_scope(self):
        p=protocol();policy=p['sentinel_policy']
        self.assertEqual(p['reviewer_sentinel'],'WP09-F04-v0')
        self.assertEqual(sum(not c['excluded'] for c in release.schedule(p,'reviewer')),1)
        self.assertNotIn('raster_or_hybrid',policy.get('required_categories',[]),'Stale B0 category outside clean digital scope')
        self.assertNotIn('single_page',policy.get('required_categories',[]),'One preselected multi-page sentinel cannot satisfy single-page requirement')

    def test_immutable_protocol_settings_and_caps(self):
        p=protocol();q=load_json(ROOT/p['q0_protocol_path'])
        for k in ('model','renderer','call','guards','gpu'):self.assertEqual(p[k],q[k],k)
        self.assertEqual(p['storage_cap_bytes'],4<<30);self.assertEqual(p['free_floor_bytes'],20<<30)
        self.assertEqual(p['gpu_process_policy']['lease_scope'],'sole_model_job')
        self.assertEqual(release.schedule(p,'author')[:2],release.schedule(p,'reviewer')[:2])
        self.assertEqual(len(release.schedule(p,'author')),6)

    def test_parser_limits_and_completion_denominators(self):
        from baseline import prediction
        e=load_json(ROOT/'evaluation/synthetic/expected/SYN-WO-01-v0-clean_expected.json');ref={'pages':['CPU reference'],'coverage':{}}
        raws={'no_pages':'unblocked','block_limit':'<PAGE>'+'<BLOCK>text[0,0,10,10]<FORK>x'*10001,'raw_limit':'x'*(16*1024*1024+1)}
        rows=[]
        for name,raw in raws.items():
            pair=scoring.paired(raw,e,ref,'completed');old=score_document(prediction(raw,mapping()),e,ref,'completed')
            self.assertEqual(pair['scores']['b0'],old);self.assertEqual(pair['scores']['mapping_v1'],old)
            self.assertFalse(old['eligible_for_exact_credit']);self.assertEqual(old['fields']['total'],15);self.assertEqual(old['cells']['total'],19)
            rows.append({'case':name,'parse_errors':old['parse_errors'],'field_total':15,'cell_total':19})
        for status in ('failed','not_run_after_failure'):
            pair=scoring.paired('',e,ref,status);self.assertEqual(pair['scores']['b0'],pair['scores']['mapping_v1']);self.assertEqual(pair['scores']['b0']['completion'],status)
        RESULTS['independent_parser_limits']=rows

    def test_atomic_heartbeat_scan_and_unsafe_paths(self):
        SCRATCH.mkdir(parents=True,exist_ok=True)
        from qualification.mapping_v1.common import safe_repo_path
        for path in ('../escape','C:/escape','/escape','docs/../escape','docs\\escape','./docs'):
            with self.subTest(path=path),self.assertRaises((PermissionError,ValueError)):safe_repo_path(path)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as d:
            root=Path(d);errors=[];stop=threading.Event()
            def writer():
                try:
                    for i in range(250):
                        (root/'heartbeat.tmp').write_text(str(i));os.replace(root/'heartbeat.tmp',root/'heartbeat.json')
                except Exception as exc:errors.append(repr(exc))
                finally:stop.set()
            t=threading.Thread(target=writer);t.start();scans=0
            while not stop.is_set() or scans<250:runtime.directory_size(root);scans+=1
            t.join();self.assertFalse(errors);self.assertGreaterEqual(scans,250)
            with self.assertRaises(FileNotFoundError):runtime.directory_size(root/'missing')
            RESULTS['atomic_scan']={'scans':scans,'writes':250,'writer_errors':errors}

    def test_full_release_gate_order_without_fresh_reads(self):
        p=protocol();now=datetime.datetime.now(datetime.timezone.utc);head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD:qualification/mapping_v1').decode().strip()
        r={'schema':'eld-mapping-v1-release/1','owner':'author','source_commit':SOURCE,'executing_head':head,'source_tree':tree,'protocol_sha256':sha((ROOT/'qualification/mapping_v1/protocol.json').read_bytes()),'comparator_tree':p['comparator_tree'],'q0_core_tree':p['q0_core_tree'],'reservation_sha256':p['public_reservation_sha256'],'corpus_commit':'6'*40,'runtime_root':p['runtime_roots']['author'],'issued_utc':(now-datetime.timedelta(seconds=10)).isoformat(),'expires_utc':(now+datetime.timedelta(minutes=30)).isoformat(),'schedule':release.schedule(p,'author'),'source_review':{'commit':'4'*40,'path':p['source_review_path'],'sha256':sha(b'CPU stub accepted review\n')},'admission_review':{'commit':p['admission_review_commit'],'path':p['admission_review_path'],'sha256':p['admission_review_sha256']},'unseal':{'commit':'5'*40,'path':'docs/coordination/WP-0009/cpu-unseal.json','sha256':''},'lease':{'id':'CPU-REVIEW-ONLY','owner':'author','gpu_uuid':p['gpu']['uuid'],'sole_lease':True,'scope':'sole_model_job','observations':[{'commit':'7'*40,'path':'docs/coordination/WP-0009/cpu-observation.json','sha256':sha(b'CPU observation\n')}]},'torchvision_local_sha256_TOFU_accepted':True}
        unseal=json.dumps({'schema':'eld-mapping-v1-unseal/1','allow_content':True,'source_commit':SOURCE,'source_review_commit':'4'*40,'reservation_sha256':p['public_reservation_sha256']}).encode();r['unseal']['sha256']=sha(unseal)
        path='docs/coordination/WP-0009/releases/cpu-review.json';authority='a'*40;real_git=release.git;read_calls=[]
        def mockgit(*args):
            if args==('show',authority+':'+path):return json.dumps(r).encode()
            if args==('show','4'*40+':'+p['source_review_path']):return b'CPU stub accepted review\n'
            if args==('show','5'*40+':'+r['unseal']['path']):return unseal
            if args==('show','7'*40+':'+r['lease']['observations'][0]['path']):return b'CPU observation\n'
            return real_git(*args)
        def artifact(*args):read_calls.append(args[2]['role']);return b'CPU artifact stub; no fresh file opened'
        with patch.object(release,'git',side_effect=mockgit),patch.object(release,'read_artifact',side_effect=artifact):
            self.assertEqual(release.read_release(authority,path,'author'),r);self.assertEqual(len(read_calls),20)
            count=len(read_calls);saved=r['source_review']['sha256'];r['source_review']['sha256']='0'*64
            with self.assertRaises(PermissionError):release.read_release(authority,path,'author')
            self.assertEqual(len(read_calls),count);r['source_review']['sha256']=saved
            saved=r['unseal']['sha256'];r['unseal']['sha256']='0'*64
            with self.assertRaises(PermissionError):release.read_release(authority,path,'author')
            self.assertEqual(len(read_calls),count);r['unseal']['sha256']=saved
            saved=r['lease']['observations'][0]['sha256'];r['lease']['observations'][0]['sha256']='0'*64
            with self.assertRaises(PermissionError):release.read_release(authority,path,'author')
            self.assertEqual(len(read_calls),count);r['lease']['observations'][0]['sha256']=saved
            r['executing_head']='0'*40
            with self.assertRaises(PermissionError):release.read_release(authority,path,'author')
            self.assertEqual(len(read_calls),count)
        RESULTS['release_binding']={'success_artifact_gate_calls':20,'mismatched_review_unseal_observation_head_rejected_before_fresh_gate':True,'stubbed_git_objects':True,'real_fresh_reads':0}

    def test_score_run_author_four_reviewer_one_denominator(self):
        p=protocol();old=load_json(ROOT/'evaluation/synthetic/expected/SYN-WO-01-v0-clean_expected.json');outcomes=[]
        for owner,count in [('author',4),('reviewer',1)]:
            with tempfile.TemporaryDirectory(dir=SCRATCH) as d:
                root=Path(d);run=root/'runs'/owner/'cpu';run.mkdir(parents=True);r={'runtime_root':str(root)}
                calls=[dict(c,status='failed' if not c['excluded'] else 'completed',observation=None) for c in release.schedule(p,owner)]
                (run/'run-result.json').write_text(json.dumps({'release':r,'calls':calls}))
                def artifact(r,p,a):
                    f=next(f for f in p['fresh_fixtures'] if a in f['artifacts'])
                    if a['role']=='expected':
                        e=copy.deepcopy(old);e.update(fixture_id=f['fixture_id'],family_id=f['family_id'],split='CPU_REVIEW',page_count=f['page_count']);return json.dumps(e).encode()
                    return json.dumps({'pages':['CPU historical reference']*f['page_count'],'coverage':{}}).encode()
                with patch.object(scoring,'read_release',return_value=r),patch.object(scoring,'read_artifact',side_effect=artifact):
                    scoring.score_run(run,root/'paired.json','CPU','CPU',owner)
                result=load_json(root/'paired.json');self.assertEqual(len(result['records']),count)
                self.assertEqual(result['summary']['b0']['CPU_REVIEW']['document_denominator'],count)
                self.assertEqual(result['summary']['mapping_v1']['CPU_REVIEW']['document_denominator'],count)
                self.assertEqual([x['fixture_id'] for x in result['records']],[c['fixture_id'] for c in calls if not c['excluded']])
                outcomes.append({'owner':owner,'primary_denominator':count,'scored_ids':[x['fixture_id'] for x in result['records']],'unselected_rows_created':False})
        RESULTS['score_run_denominators']=outcomes

def regression():
    runs={'dev':ROOT/'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6','eval_holdout':ROOT/'docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d','supplement':ROOT/'docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca'}
    fixtures={f['fixture_id']:f for f in load_json(ROOT/'evaluation/manifests/corpus-manifest.json')['fixtures']}
    candidate=load_json(ROOT/'docs/evidence/WP-0009/eld-mapping-author/005/attempt-2/comparison.json');seen=[];old_scores=[];new_scores=[];supplements=[];gains=losses=tg=tl=0
    for lane,run in runs.items():
        for old in load_json(run/'scores.json')['scores']:
            fid=old['fixture_id'];fx=fixtures[fid];raw_path=run/'evidence'/(fid+'.measured.raw.txt');data=raw_path.read_bytes() if raw_path.exists() else b''
            e=load_json(ROOT/fx['expected_ground_truth_path']);ref=reference_for(fx,allow_test=True)
            parsed=parse_native(data.decode())
            before=baseline_prediction(parsed,mapping());after=extract_prediction(parsed,mapping())
            b=score_document(before,e,ref,old['completion']);n=score_document(after,e,ref,old['completion'])
            b['raw_sha256']=n['raw_sha256']=sha(data);assert b==old
            author=next(d for d in candidate['supplement_separate' if lane=='supplement' else 'documents'] if d['fixture_id']==fid)
            assert n==author['mapping_v1_score'] and after['fields']==author['mapping_v1_fields']
            for key in set(before)-{'fields'}:assert before[key]==after[key],(fid,key)
            for key in ('cells','normalized_cells','rows','expected_absences','text','page_count','page_sentinels','adjacency','cross_page_links','parse_errors'):assert b[key]==n[key],(fid,key)
            if lane!='supplement':
                old_scores.append(b);new_scores.append(n)
                for a,z in zip(b['fields']['details'],n['fields']['details']):gains+=int(z['credited_exact'] and not a['credited_exact']);losses+=int(a['credited_exact'] and not z['credited_exact'])
                for a,z in zip(b['normalized_fields']['details'],n['normalized_fields']['details']):tg+=int(z['credited_exact'] and not a['credited_exact']);tl+=int(a['credited_exact'] and not z['credited_exact'])
            else:supplements.append({'fixture_id':fid,'b0':b,'mapping_v1':n})
            seen.append({'fixture_id':fid,'lane':lane,'raw_sha256':sha(data),'raw_available':raw_path.exists(),'b0_full_score_equal':True,'candidate_full_score_equal':True,'before_fields':b['fields']['correct'],'after_fields':n['fields']['correct'],'field_total':b['fields']['total'],'cell_total':b['cells']['total'],'candidate_provenance':after['fields']})
    assert summarize(old_scores)==candidate['baseline_summary'] and summarize(new_scores)==candidate['mapping_v1_summary']
    assert (len(old_scores),len(supplements),gains,losses,tg,tl)==(26,1,27,0,27,0)
    first=load_json(ROOT/'docs/evidence/WP-0009/eld-mapping-author/005/attempt-1/comparison.json')
    assert first['documents']==candidate['documents'] and first['supplement_separate']==candidate['supplement_separate']
    RESULTS['regression']={'primary':26,'completed':25,'separate_supplement':1,'printed_gains':gains,'printed_losses':losses,'typed_gains':tg,'typed_losses':tl,'fields':sum(s['fields']['total'] for s in old_scores),'cells':sum(s['cells']['total'] for s in old_scores),'documents':seen,'supplement_scores':supplements,'summaries':{'b0':summarize(old_scores),'mapping_v1':summarize(new_scores)},'initial_and_corrected_candidate_document_scores_identical':True}

def main():
    global SOURCE
    parser=argparse.ArgumentParser();parser.add_argument('--source',default=SOURCE);parser.add_argument('--out',required=True);args=parser.parse_args()
    SOURCE=args.source;output=(OWN/args.out).resolve();output.relative_to(OWN);assert not output.exists(),'Preserve all previous attempt results'
    assert MODULE_ROOT==ROOT and not git('status','--porcelain').strip()
    source_tree=git('rev-parse','HEAD:qualification/mapping_v1').decode().strip()
    assert source_tree==git('rev-parse',SOURCE+':qualification/mapping_v1').decode().strip()
    SCRATCH.mkdir(parents=True,exist_ok=True)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'qualification/mapping_v1/tests'))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    regression()
    RESULTS.update({'executing_head':git('rev-parse','HEAD').decode().strip(),'candidate_source':SOURCE,'source_tree':source_tree,'protocol_sha256':sha((ROOT/'qualification/mapping_v1/protocol.json').read_bytes()),'tests':{'run':result.testsRun,'failures':[(str(t),m) for t,m in result.failures],'errors':[(str(t),m) for t,m in result.errors],'skipped':result.skipped},'fresh_reads':0,'model_gpu_queries':0,'status':'PASS' if result.wasSuccessful() else 'FINDINGS'})
    output.write_text(json.dumps(RESULTS,indent=2)+'\n')
    print(json.dumps({k:RESULTS[k] for k in ('executing_head','candidate_source','source_tree','protocol_sha256','tests','status')},indent=2))
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
