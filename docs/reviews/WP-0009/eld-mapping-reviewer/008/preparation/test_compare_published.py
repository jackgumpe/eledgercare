"""Synthetic in-memory schema tests only. These are not fresh inference outcomes."""
import copy,json,unittest
import compare_published as c

def encoded(obj):return (json.dumps(obj,indent=2)+'\n').encode()
def raw_text(pages,value='SYNTHETIC-ONLY'):
    return ('<PAGE><BLOCK>table[0,0,900,900]<FORK><table><tr><td>Invoice No:</td><td>'+value+'</td></tr></table>')*pages

class Packet:
    def __init__(self,owner='author'):
        self.p=c.protocol();self.owner=owner;self.data={};self.fixtures={}
        self.release={'executing_head':'0'*40,'schedule':c.schedule(self.p,owner),'synthetic_only':True}
        self.plan={'release':self.release,'executing_head':'0'*40,'calls':self.release['schedule']}
        self.result={'release':self.release,'executing_head':'0'*40,'calls':[],'failure':None,'child_returncode':0,'observed_child_exit':True,'observers':[{'path':'C:\\synthetic-only\\observer.log','bytes':15,'returncode':0,'tag':'synthetic','index':0}]}
        self.data['observer.log']=b'SYNTHETIC ONLY\n'
        for call in self.release['schedule']:
            fx=next(f for f in self.p['historical_warmups']+self.p['fresh_fixtures'] if f['fixture_id']==call['fixture_id'])
            fid=fx['fixture_id'];label=fid+'.'+call['kind'];pages=fx['page_count'];raw=raw_text(pages).encode();tokens=[101,202,303]
            def descriptor(name,data):return {'name':name,'bytes_written':len(data),'full_bytes':len(data),'sha256_written':c.sha(data),'full_sha256':c.sha(data),'truncated_by_writer':False,'utf8_lossless':True}
            obs={**{'fixture_id':fid,'family_id':fx['family_id'],'page_count_in':pages,'kind':call['kind'],'excluded_from_warm_statistics':call['excluded']},'flags':[],
                'raw_output':descriptor(label+'.txt',raw),'token_ids_file':descriptor(label+'.tokens.json',encoded(tokens)),
                'native':{'text_sha256':c.sha(raw),'token_ids_sha256':c.sha(json.dumps(tokens).encode()),'finish_reason':'stop','expected_pages':pages,'num_pages_out':pages,'output_tokens':len(tokens),'prompt_len':100},
                'call_kwargs':dict(self.p['call']['fixed_kwargs'],max_new_tokens=8000*pages,ngram_window=1024 if pages>1 else 128),'kernel_path':{'label':'triton_import_failed_dense_fallback'},
                'timing':{'synthetic_only':True},'host_memory':{'synthetic_only':True},'cuda_memory':{'synthetic_only':True}}
            self.set('evidence/'+label+'.observation.json',obs);self.data['evidence/'+label+'.txt']=raw;self.data['evidence/'+label+'.tokens.json']=encoded(tokens)
            pdf=fx['sha256'] if fid in self.p['warmups'] else next(a['sha256'] for a in fx['artifacts'] if a['role']=='pdf')
            self.set('evidence/'+label+'.render.json',{'pdf_sha256':pdf,'raster':[{'page':page,'width':1,'height':1,'rgb_sha256':'0'*64} for page in range(1,pages+1)],'synthetic_only':True})
            self.result['calls'].append({**call,'status':'completed','observation':'evidence/'+label+'.observation.json'})
            fields=[{'field_id':'invoice_number','page_number':page,'printed_text':'SYNTHETIC-ONLY','normalized_value':'SYNTHETIC-ONLY','value_type':'identifier'} for page in range(1,pages+1)]
            expected={'fixture_id':fid,'family_id':fx['family_id'],'page_count':pages,'split':'synthetic-test-only','variant_kind':'synthetic-test-only','expected_fields':fields,'expected_tables':[],'expected_absences':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
            self.fixtures[fid]=(expected,{'pages':['Invoice No: SYNTHETIC-ONLY']*pages,'coverage':{'synthetic_only':True}})
        self.set('evidence/worker-outcome.json',{'failure':None,'no_retry':True,'synthetic_only':True})
        self.set('evidence/preflight.json',{'release':self.release,'renderer':{'distribution_version':self.p['renderer']['version']},'model':{'files':[{'ok':True,'synthetic_only':True} for _ in range(18)]},'notice':{'notices':[{'ok':True,'synthetic_only':True}]}})
        self.set('evidence/load.json',{'module_cache':{'modules':[{'identical':True,'synthetic_only':True}]}})
    def set(self,path,obj):self.data[path]=encoded(obj)
    def get(self,path):return c.load(self.data[path])
    def read(self,path):
        if path not in self.data:raise FileNotFoundError(path)
        return self.data[path]
    def audit(self,scores=None):
        self.set('run-result.json',self.result);self.set('plan.json',self.plan)
        return c.inspect_run(self.read,self.p,self.release,self.owner,self.fixtures.__getitem__,scores)
    def fail_from(self,index):
        for i,call in enumerate(self.result['calls']):
            if i>=index:call.update(status='failed' if i==index else 'not_run_after_failure',observation=None)
        self.result['failure']='SYNTHETIC_FIRST_FAILURE';self.result['child_returncode']=1
    def alter_observation(self,index,key,value):
        path=self.result['calls'][index]['observation'];obs=self.get(path);obs[key]=value;self.set(path,obs)

class PreparationTests(unittest.TestCase):
    def test_full_author_denominator_excludes_warmups_and_family_weight(self):
        a=Packet().audit()['public'];self.assertEqual(a['primary_document_denominator'],4);self.assertEqual(a['completed_primary'],4)
        self.assertEqual(len(a['calls']),6);self.assertEqual(len(a['records']),4);self.assertEqual(a['excluded_warmups'],2)
        summary=a['summary']['mapping_v1']['synthetic-test-only'];self.assertEqual(summary['family_macro']['fields'],{'mean':1.0,'families_with_denominator':4})
        self.assertEqual(sum(r['scores']['mapping_v1']['fields']['total'] for r in a['records']),6)
        self.assertEqual(sum(len(x['fields']['gains']) for x in a['per_item_changes'].values()),6)
        self.assertTrue(all(not x['non_field_changed_objects'] for x in a['per_item_changes'].values()))
    def test_reviewer_only_selected_sentinel_not_four_families(self):
        b=Packet('reviewer').audit()['public'];self.assertEqual(b['primary_document_denominator'],1);self.assertEqual(len(b['records']),1)
        self.assertEqual(b['records'][0]['fixture_id'],'WP09-F04-v0');self.assertEqual(len(b['summary']['b0']['synthetic-test-only']['families']),1)
    def test_actual_sentinel_equality_and_divergence_are_explicit(self):
        a=Packet().audit();b=Packet('reviewer').audit();same=c.compare_sentinel(a,b)
        self.assertTrue(same['raw_bytes_equal'] and same['token_ids_equal'] and same['full_scores_equal'])
        changed=copy.deepcopy(b);changed['material']['WP09-F04-v0']['raw']+=b' ';changed['material']['WP09-F04-v0']['tokens'].append(99)
        diff=c.compare_sentinel(a,changed);self.assertFalse(diff['raw_bytes_equal']);self.assertFalse(diff['token_ids_equal']);self.assertTrue(diff['full_scores_equal'])
        changed['material']['WP09-F04-v0']['scores']['b0']['fields']['correct']=9
        self.assertFalse(c.compare_sentinel(a,changed)['full_scores_equal'])
    def test_failed_primary_and_not_run_retain_denominators(self):
        p=Packet();p.fail_from(3);a=p.audit()['public'];self.assertEqual(a['completed_primary'],1);self.assertEqual(a['primary_document_denominator'],4)
        self.assertEqual([r['completion'] for r in a['records']],['completed','failed','not_run_after_failure','not_run_after_failure'])
        self.assertEqual(a['summary']['mapping_v1']['synthetic-test-only']['family_macro']['fields']['mean'],.25)
        self.assertEqual(sum(r['scores']['mapping_v1']['fields']['total'] for r in a['records']),6)
        self.assertTrue(a['metadata_issues'])
    def test_failed_warmup_prevents_all_primary_credit(self):
        p=Packet();p.fail_from(0);a=p.audit()['public'];self.assertEqual(a['completed_primary'],0);self.assertEqual(a['primary_document_denominator'],4)
        self.assertTrue(all(r['scores']['mapping_v1']['fields']['correct']==0 for r in a['records']))
    def test_missing_sentinel_has_no_manufactured_raw_equality(self):
        p=Packet('reviewer');p.fail_from(2);r=c.compare_sentinel(Packet().audit(),p.audit())
        self.assertIsNone(r['raw_bytes_equal']);self.assertIsNone(r['token_ids_equal']);self.assertFalse(r['both_completed']);self.assertFalse(r['full_scores_equal'])
    def test_completed_after_first_failure_rejected(self):
        p=Packet();p.result['calls'][2]['status']='failed'
        with self.assertRaisesRegex(ValueError,'Later call'):p.audit()
    def test_omitted_primary_rejected(self):
        p=Packet();p.result['calls'].pop()
        with self.assertRaisesRegex(ValueError,'schedule'):p.audit()
    def test_raw_tampering_rejected(self):
        p=Packet();p.data['evidence/WP09-F01-v0.measured.txt']+=b'x'
        with self.assertRaisesRegex(ValueError,'Retained raw'):p.audit()
    def test_token_file_tampering_rejected(self):
        p=Packet();p.data['evidence/WP09-F01-v0.measured.tokens.json']+=b' '
        with self.assertRaisesRegex(ValueError,'token file'):p.audit()
    def test_native_token_hash_tampering_rejected(self):
        p=Packet();path=p.result['calls'][2]['observation'];obs=p.get(path);obs['native']['token_ids_sha256']='0'*64;p.set(path,obs)
        with self.assertRaisesRegex(ValueError,'Native token'):p.audit()
    def test_render_binding_and_parameters_rejected(self):
        for kind in ['render','kwargs','warmup']:
            p=Packet()
            if kind=='render':
                path='evidence/WP09-F01-v0.measured.render.json';value=p.get(path);value['pdf_sha256']='0'*64;p.set(path,value)
            elif kind=='kwargs':p.alter_observation(2,'call_kwargs',{})
            else:p.alter_observation(0,'excluded_from_warm_statistics',False)
            with self.subTest(kind=kind),self.assertRaises(ValueError):p.audit()
    def test_exact_full_scores_and_summary_required(self):
        p=Packet();a=p.audit()['public'];scores={'run_result_sha256':c.sha(p.read('run-result.json')),'records':a['records'],'summary':a['summary']}
        p.audit(scores);scores['records'][0]['scores']['b0']['fields']['correct']=99
        with self.assertRaisesRegex(ValueError,'full score'):p.audit(scores)
    def test_supervisor_and_worker_status_do_not_erase_completed_observations(self):
        p=Packet();p.result['failure']='SYNTHETIC_FINALIZATION';p.result['child_returncode']=7;a=p.audit()['public']
        self.assertEqual(a['completed_primary'],4);self.assertEqual(a['worker_outcome']['failure'],None);self.assertTrue(any('Supervisor' in s for s in a['metadata_issues']))
        self.assertEqual(len(a['checks_requiring_separate_exact_coordinator_proof']),3)
    def test_observer_failure_and_missing_metadata_preserved(self):
        p=Packet();p.result['observers'][0]['returncode']=3;del p.data['evidence/load.json'];a=p.audit()['public']
        self.assertEqual(a['observer_checks'][0]['returncode'],3);self.assertTrue(any('Observer' in s for s in a['metadata_issues']));self.assertTrue(any('Missing published' in s for s in a['metadata_issues']))
    def test_empty_model_notice_and_cache_not_passed_vacuously(self):
        p=Packet();path='evidence/preflight.json';v=p.get(path);v['notice']={};p.set(path,v);p.set('evidence/load.json',{'module_cache':{}})
        issues=p.audit()['public']['metadata_issues'];self.assertTrue(any('notice' in s for s in issues));self.assertTrue(any('cache' in s for s in issues))
    def test_nonfield_changes_and_losses_are_not_hidden(self):
        pair=Packet().audit()['public']['records'][0];pair=copy.deepcopy(pair);pair['scores']['b0']['fields']['details'][0]['credited_exact']=True;pair['scores']['mapping_v1']['fields']['details'][0]['credited_exact']=False;pair['scores']['mapping_v1']['page_count']['correct']=9
        delta=c.field_changes(pair);self.assertEqual(len(delta['fields']['losses']),1);self.assertIn('page_count',delta['non_field_changed_objects'])
    def test_unsafe_paths_rejected_without_opening_external_files(self):
        for path in ['../secret','C:/active/run','/active/run','a/../b','a//b']:
            with self.subTest(path=path),self.assertRaises(ValueError):c.safe(path)
    def test_model_import_blocked(self):
        with self.assertRaisesRegex(RuntimeError,'prohibits'):c.NoModel().find_spec('torch',None)

if __name__=='__main__':unittest.main(verbosity=2)
