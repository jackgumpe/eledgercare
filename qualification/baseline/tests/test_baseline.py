import copy,datetime,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native import parse_native,extract_prediction,ParseError,norm
from score import score_document,token_errors,summarize
from corpus import fixtures,expected_for,reference_for,DEV
from release import protocol,schedule,validate_release,read_release,HERE
from runtime import guard_reason
from corpus import sha

RULES={'labels':[{'label':'Ticket','field_id':'id'},{'label':'Total','field_id':'total'},{'label':'Optional','field_id':'optional'}],
       'tables':[{'table_id':'lines','headers':['Code','Price'],'columns':['code','price']} ]}
def block(text,kind='text',box='10,10,300,25'):return f'<BLOCK>{kind}[{box}]<FORK>{text}\n'
def pred(raw):return extract_prediction(parse_native(raw),RULES)
def truth():
    return {'fixture_id':'made-up','family_id':'DEV','split':'dev','variant_kind':'v0_clean','page_count':1,
      'expected_fields':[{'field_id':'id','label_printed':'Ticket','page_number':1,'printed_text':'0007','normalized_value':'0007'},
                         {'field_id':'total','label_printed':'Total','page_number':1,'printed_text':'-$20.00','normalized_value':'-20.00'}],
      'expected_absences':[{'field_id':'optional','page_number':1}],
      'expected_tables':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
def score(raw,status='completed',e=None):return score_document(pred(raw),e or truth(),{'pages':['Ticket: 0007\nTotal: -$20.00'],'coverage':{'status':'test'}},status)
class ParserScorerTests(unittest.TestCase):
    def test_exact_and_strict_digits_money(self):
        raw='<PAGE>'+block('Ticket: 0007')+block('Total: -$20.00')
        self.assertEqual(score(raw)['fields']['correct'],2)
        self.assertEqual(score(raw.replace('0007','7'))['fields']['correct'],1)
        self.assertEqual(score(raw.replace('-$20.00','$20.00'))['fields']['correct'],1)
    def test_duplicate_and_missing_preserved(self):
        a=score('<PAGE>'+block('Ticket: 0007')*2)
        self.assertEqual(a['fields']['total'],2);self.assertEqual(a['fields']['missing'],1);self.assertEqual(a['fields']['unmatched_candidates'],1)
    def test_failed_completion_cannot_get_exact_credit(self):
        a=score('<PAGE>'+block('Ticket: 0007')+block('Total: -$20.00'),'timeout')
        self.assertEqual(a['fields']['total'],2);self.assertEqual(a['fields']['correct'],0);self.assertEqual(a['completed_documents'],0)
        self.assertEqual(a['expected_absences']['correct'],0)
    def test_absence_invention(self):
        a=score('<PAGE>'+block('Optional: made up'))
        self.assertEqual(a['expected_absences']['violations'],1)
    def test_no_expected_values_enter_extraction(self):
        raw='<PAGE>'+block('Ticket: 0007');before=pred(raw)
        e=truth();e['expected_fields'][0]['printed_text']='CHANGED';score(raw,e=e)
        self.assertEqual(before,pred(raw))
    def test_unknown_label_retained(self):
        p=pred('<PAGE>'+block('Surprise: invented value'))
        self.assertTrue(any(x['kind']=='unknown_label' for x in p['unmapped']))
    def test_safe_html_and_entities(self):
        p=pred('<PAGE>'+block('<table><tr><td>Code</td><td>Price</td></tr><tr><td>A&amp;B</td><td>-$2.00</td></tr></table>','table'))
        self.assertEqual(p['tables'][0]['rows'][0]['values'],['A&B','-$2.00'])
        q=pred('<PAGE>'+block('<table><tr><td><script>danger()</script></td></tr></table>','table'))
        self.assertTrue(q['parse_errors'])
    def test_reject_rowspan_and_unclosed(self):
        self.assertTrue(pred('<PAGE>'+block('<table><tr><td rowspan="2">A</td></tr></table>','table'))['parse_errors'])
        self.assertTrue(pred('<PAGE>'+block('<table><tr><td>A','table'))['parse_errors'])
    def test_no_eval_grammar(self):
        raw='<PAGE><BLOCK>text[__import__("os"),0,1,2]<FORK>payload'
        self.assertTrue(pred(raw)['parse_errors'])
    def test_coordinates_and_extra_pages(self):
        self.assertTrue(pred('<PAGE>'+block('x',box='20,10,5,12'))['parse_errors'])
        self.assertEqual(score('<PAGE><PAGE>')['page_count']['correct'],0)
    def test_empty_failure_all_denominators(self):
        a=score('','not_run_after_failure');self.assertEqual(a['fields']['total'],2);self.assertEqual(a['fields']['missing'],2)
        self.assertEqual(a['text']['deletions'],4)
    def test_token_reorder_insert_delete_counts(self):
        self.assertGreater(token_errors('a b c','c a b')['error_rate'],0)
        self.assertEqual(token_errors('a b','a b c')['insertions'],1)
        self.assertEqual(token_errors('a b','a')['deletions'],1)
    def test_nfc_outer_only(self):
        self.assertEqual(norm(' e\u0301\r\n'),'é');self.assertNotEqual(norm('A  B'),'A B')
    def test_table_duplicate_missing_extra_cells(self):
        e=truth();e['expected_fields']=[];e['expected_tables']=[{'table_id':'lines','rows':[{'row_id':'r1','page_number':1,'cells':{'code':{'printed_text':'A'},'price':{'printed_text':'$1.00'}}}]}]
        row='<tr><td>A</td><td>$1.00</td></tr>'
        a=score('<PAGE>'+block('<table><tr><td>Code</td><td>Price</td></tr>'+row+row+'</table>','table'),e=e)
        self.assertEqual(a['cells']['correct'],2);self.assertEqual(a['cells']['extra_rows'],1);self.assertEqual(a['cells']['extra_cells'],2)
        b=score('<PAGE>',e=e);self.assertEqual(b['cells']['total'],2);self.assertEqual(b['cells']['missing_rows'],1)
    def test_bad_header_not_repaired(self):
        a=pred('<PAGE>'+block('<table><tr><td>C0de</td><td>Price</td></tr><tr><td>A</td><td>$1</td></tr></table>','table'))
        self.assertFalse(a['tables']);self.assertTrue(a['unmapped'])
    def test_repeated_headers_not_rows(self):
        h='<tr><td>Code</td><td>Price</td></tr>';r='<tr><td>A</td><td>$1</td></tr>'
        a=pred('<PAGE>'+block('<table>'+h+r+h+r+'</table>','table'))
        self.assertEqual(sum(len(t['rows']) for t in a['tables']),2)
    def test_resource_bound(self):
        with patch('native.MAX_BYTES',10):
            with self.assertRaises(ParseError):parse_native('x'*11)
    def test_family_macro_and_split_separation(self):
        a=score('<PAGE>'+block('Ticket: 0007'));b=copy.deepcopy(a);b['family_id']='OTHER';b['fields']['rate']=1.0;b['split']='eval_holdout'
        s=summarize([a,b]);self.assertEqual(set(s),{'dev','eval_holdout'});self.assertEqual(s['dev']['document_denominator'],1)

class CorpusReleaseTests(unittest.TestCase):
    def test_holdout_gate_before_read(self):
        f=next(f for f in fixtures() if f['split']=='eval_holdout')
        with patch('corpus.verified') as reader:
            with self.assertRaises(PermissionError):expected_for(f)
            with self.assertRaises(PermissionError):reference_for(f)
            reader.assert_not_called()
    def test_dev_reference_coverage(self):
        docs=[f for f in fixtures() if f['family_id'] in DEV];self.assertEqual(len(docs),13)
        for f in docs:
            ref=reference_for(f);self.assertEqual(len(ref['pages']),f['page_count']);self.assertTrue(all(ref['pages']))
            self.assertEqual(ref['coverage']['status'],'complete_for_admitted_writer')
            self.assertEqual(ref['coverage']['hybrid_added'],f['variant_kind']=='v3_hybrid')
    def test_schedule_exact(self):
        p=protocol();self.assertEqual(len(p['fixtures']),26);self.assertEqual(sum(f['page_count'] for f in p['fixtures']),40)
        for split in ['dev','eval_holdout']:
            s=schedule(p,split);self.assertEqual(len(s),15);self.assertEqual(sum(x['excluded'] for x in s),2)
            self.assertEqual(len({x['fixture_id'] for x in s if not x['excluded']}),13)
    def release(self):
        p=protocol();return {'schema':'eld-baseline-release/1','owner':'author','source_commit':'1'*40,'executing_head':'4'*40,'source_tree':'2'*40,
         'protocol_sha256':sha((HERE/'protocol.json').read_bytes()),'mapping_sha256':sha((HERE/'mapping.json').read_bytes()),'lock_sha256':p['dependency_lock_sha256'],
         'accepted_review_commit':'3'*40,'accepted_review_path':'docs/agent-reports/eld-next-reviewer/WP-0007/003_test.md','split':'dev','runtime_root':p['runtime_roots']['author'],
         'lease_id':'test-only','gpu_uuid':p['gpu']['uuid'],'expires_utc':'2099-01-01T00:00:00Z','allow_test_content':False,
         'sentinels':['SYN-WO-01-v0-clean','SYN-MP-01-v0-clean','SYN-WO-02-v3-hybrid-note'],'observed_gpu_state':{'test':True},'torchvision_local_sha256_TOFU_accepted':True}
    def test_release_missing_changed_expired_and_test_refused(self):
        p=protocol();r=self.release();validate_release(r,p,'dev','author',tree='2'*40)
        for key,value in [('source_tree','f'*40),('mapping_sha256','0'*64),('expires_utc','2000-01-01T00:00:00Z'),('sentinels',[]),('runtime_root','C:\\wrong')]:
            bad={**r,key:value}
            with self.assertRaises(PermissionError):validate_release(bad,p,'dev','author',tree='2'*40)
        r['split']='eval_holdout'
        with self.assertRaises(PermissionError):validate_release(r,p,'eval_holdout','author',tree='2'*40)
        with self.assertRaises(PermissionError):read_release(None,None,'dev','author')
    def test_runtime_no_release_before_side_effects(self):
        from runtime import execute
        with patch('runtime.q0_imports') as q:
            with self.assertRaises(PermissionError):execute(None,None,'dev','author')
            q.assert_not_called()
    def test_timeout_stall_storage_log_guard(self):
        p=protocol();args=dict(elapsed=1,phase_elapsed=1,progress_elapsed=1,stall_monitored=True,phase_limit=1800,log_bytes=0,root_bytes=0,free_bytes=30<<30,p=p)
        self.assertIsNone(guard_reason(**args))
        for key,value in [('elapsed',21601),('phase_elapsed',1801),('progress_elapsed',301),('log_bytes',65<<20),('root_bytes',5<<30),('free_bytes',19<<30)]:
            self.assertIsNotNone(guard_reason(**{**args,key:value}))
    @unittest.skipUnless(os.name=='nt','Windows job test')
    def test_worker_job_ownership_kills_only_owned_child(self):
        import winjob,uuid
        name='Local\\baseline-cpu-test-'+uuid.uuid4().hex;handle=winjob.create(name);proc=None
        try:
            code=f"import sys,time;sys.path.insert(0,{str(HERE)!r});import winjob;winjob.join({name!r});print('JOINED',flush=True);time.sleep(30)"
            proc=subprocess.Popen([sys.executable,'-I','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(proc.stdout.readline().strip(),'JOINED')
            winjob.close(handle);handle=None
            proc.wait(timeout=5);self.assertIsNotNone(proc.returncode)
        finally:
            if handle:winjob.close(handle)
            if proc and proc.poll() is None:proc.kill();proc.wait(timeout=5)
            if proc:
                proc.stdout.close();proc.stderr.close()
if __name__=='__main__':unittest.main()
