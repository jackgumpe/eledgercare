"""Public synthetic readiness checks; never relabel these as actual runtime evidence."""
import copy,json,sys,unittest
from pathlib import Path
import compare_published as c
sys.path.insert(0,str(c.ROOT/'docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review'))
from public_examples import example,unresolved_field

def synthetic(owner='author',mode='completed',truth_status=None):
    p=c.protocol();plan=c.schedule(p,owner);head='2'*40
    release={'executing_head':head,'schedule':plan}
    supervisor={'pid':101,'creation_filetime_100ns':111,'created_utc':'CPU fixture'}
    launcher={'pid':102,'creation_filetime_100ns':222,'created_utc':'CPU fixture'}
    worker={'pid':103,'creation_filetime_100ns':333,'created_utc':'CPU fixture'}
    result={'schema':'eld-mapping-v2-run/1','release':release,'executing_head':head,'failure':None,'calls':[],
      'child_returncode':0,'observed_child_exit':True,'finalization_errors':[],'final_observation_status':{'post_observers':'available'},
      'supervisor_identity':supervisor,'child_launcher_pid':102,'child_launcher_identity':launcher}
    triples={f['fixture_id']:example(f['case'],f['family_id'])[:3] for f in p['fresh_fixtures']}
    if truth_status:
        for e,ref,policy in triples.values():
            if policy['case']=='conflict':
                unresolved_field(e,policy,truth_status)
                left,right=policy['ideal_native'].rsplit('PUBLIC-0042',1)
                policy['ideal_native']=left+'PUBLIC-9999'+right
    fixtures={f['fixture_id']:f for f in p['historical_warmups']+p['fresh_fixtures']};files={}
    def put(name,value):files[name]=json.dumps(value,ensure_ascii=False).encode()
    for i,call in enumerate(plan):
        fid=call['fixture_id'];fx=fixtures[fid];label=fid+'.'+call['kind'];prefix='evidence/'+label
        state='completed'
        if mode=='all_not_run':state='not_run_after_failure'
        elif mode=='partial' and i>=3:state='failed' if i==3 else 'not_run_after_failure'
        record={**call,'status':state,'observation':prefix+'.observation.json' if state=='completed' else None,
          'observation_status':'available' if state=='completed' else 'unavailable' if state=='failed' else 'absent'}
        result['calls'].append(record)
        if state!='completed':continue
        raw=(triples[fid][2]['ideal_native'] if fid in triples else '<PAGE>'*fx['page_count']+'<BLOCK>text[0,0,900,30]<FORK>Work Order ID: PUBLIC-42').encode()
        tokens=[1,2,3];tokenbytes=json.dumps(tokens).encode();files[prefix+'.raw.txt']=raw;files[prefix+'.tokens.json']=tokenbytes
        kwargs=dict(p['call']['fixed_kwargs'],max_new_tokens=8000*fx['page_count'],ngram_window=1024 if fx['page_count']>1 else 128)
        obs={'fixture_id':fid,'family_id':fx['family_id'],'kind':call['kind'],'page_count_in':fx['page_count'],'excluded_from_warm_statistics':call['excluded'],
          'flags':[],'call_kwargs':kwargs,
          'raw_output':{'name':label+'.raw.txt','bytes_written':len(raw),'sha256_written':c.sha(raw),'truncated_by_writer':False,'utf8_lossless':True},
          'token_ids_file':{'name':label+'.tokens.json','bytes_written':len(tokenbytes),'sha256_written':c.sha(tokenbytes)},
          'native':{'token_ids_sha256':c.sha(json.dumps(tokens).encode()),'text_sha256':c.sha(raw),'finish_reason':'stop','expected_pages':fx['page_count'],'num_pages_out':fx['page_count'],'output_tokens':3,'prompt_len':30},
          'kernel_path':{'label':'triton_import_failed_dense_fallback'},'timing':None,'host_memory':{'unknown':None},'cuda_memory':None}
        put(prefix+'.observation.json',obs)
        pdf=fx['sha256'] if fid in p['warmups'] else next(a['sha256'] for a in fx['artifacts'] if a['role']=='pdf')
        put(prefix+'.render.json',{'pdf_sha256':pdf,'raster':[{'page':n+1,'width':10,'height':20,'rgb_sha256':'a'*64} for n in range(fx['page_count'])],'render_s':None})
    if mode!='completed':result['failure']='SYNTHETIC_POST_FAILURE' if mode=='post_failure' else 'SYNTHETIC_FIRST_FAILURE'
    if mode=='post_failure':result['final_observation_status']['post_observers']='unavailable';result['finalization_errors']=[{'stage':'post_observer_validation'}]
    put('run-result.json',result);put('plan.json',{'release':release,'executing_head':head,'calls':plan,'supervisor_pid':101,'supervisor_identity':supervisor})
    put('evidence/worker-outcome.json',{'failure':None,'no_retry':True,'worker_pid':103,'worker_identity':worker})
    put('evidence/preflight.json',{'release':release,'worker_pid':103,'worker_identity':worker})
    def read(name):
        if name not in files:raise FileNotFoundError(name)
        return files[name]
    return p,release,files,read,lambda fid:triples[fid]

def inspect(b,owner='author',scores=None):return c.inspect_run(b[3],b[0],b[1],owner,b[4],scores)
def mutate(b,path,fn):
    value=c.load(b[2][path]);fn(value);b[2][path]=json.dumps(value).encode()

class ComparisonTests(unittest.TestCase):
    def test_full_three_mapper_packets_twelve_vs_one(self):
        for owner,n in [('author',12),('reviewer',1)]:
            b=synthetic(owner);a=inspect(b,owner);public=a['public']
            self.assertEqual(public['primary_document_denominator'],n);self.assertEqual(len(public['calls']),n+2)
            self.assertEqual(set(public['records'][0]['scores']),{'b0','mapping_v1','mapping_v2'})
            expected=sum(len(b[4](row['fixture_id'])[2]['slots']) for row in public['records'])
            for name in ('b0','mapping_v1','mapping_v2'):
                self.assertEqual(public['policy_denominators'][name]['slots'],expected)
                self.assertEqual(public['policy_denominators'][name]['unavailable_slots'],0)
            self.assertTrue(all(x['timing'] is None and x['cuda_memory'] is None for x in public['calls']))
            if owner=='author':self.assertEqual(len(public['policy_summary']['mapping_v2']['families']),4)
            else:self.assertEqual(public['policy_summary']['sentinel_documents'],1)
            inspect(b,owner,public['complete_reproduced_packet'])

    def test_full_prediction_score_policy_and_summary_mutations_rejected(self):
        b=synthetic();original=inspect(b)['public']['complete_reproduced_packet']
        mutations=[
          lambda x:x['records'][0]['predictions']['mapping_v2'].update(parse_errors=['changed']),
          lambda x:x['records'][0]['scores']['mapping_v2']['fields'].update(correct=999),
          lambda x:x['records'][0]['policy_scores']['mapping_v2']['metrics'].update(observed_candidates=999),
          lambda x:x['policy_summary']['mapping_v2']['all'].update(documents=999),
          lambda x:x['historical_summary']['mapping_v1'].update(extra='changed')]
        for fn in mutations:
            bad=copy.deepcopy(original);fn(bad)
            with self.assertRaisesRegex(ValueError,'Published full'):inspect(b,scores=bad)

    def test_otherwise_complete_after_failure_and_gap_reject(self):
        for state in ('failed','not_run_after_failure'):
            b=synthetic()
            def change(x):
                x['failure']='FIRST_FAILURE';x['calls'][0]['status']=state
                if state=='not_run_after_failure':x['calls'][0].update(observation=None,observation_status='absent')
            mutate(b,'run-result.json',change)
            with self.assertRaisesRegex(ValueError,'after first failure'):inspect(b)

    def test_failed_unavailable_and_post_finalization_frames(self):
        for owner,n in [('author',12),('reviewer',1)]:
            for mode in ('all_not_run','partial','post_failure'):
                a=inspect(synthetic(owner,mode),owner)['public']
                self.assertEqual(len(a['records']),n)
                completed=sum(x['completion']=='completed' for x in a['records'])
                self.assertEqual(completed,0 if mode=='all_not_run' else n if mode=='post_failure' else 1)
                for key in ('b0','mapping_v1','mapping_v2'):
                    if mode=='all_not_run':self.assertEqual(a['policy_denominators'][key]['unavailable_slots'],a['policy_denominators'][key]['slots'])
                self.assertIn('Supervisor reports failure/nonzero or unknown child exit',a['metadata_issues'])

    def test_raw_tokens_render_observation_and_exclusion_mismatches(self):
        for kind in ('raw','tokens','render','identity','warmup','truncation','call','count'):
            b=synthetic();label=c.schedule(b[0],'author')[0]['fixture_id']+'.warmup';prefix='evidence/'+label
            if kind=='raw':b[2][prefix+'.raw.txt']+=b'X'
            elif kind=='tokens':b[2][prefix+'.tokens.json']=b'[9,8,7]'
            elif kind=='render':mutate(b,prefix+'.render.json',lambda x:x.update(pdf_sha256='0'*64))
            elif kind=='identity':mutate(b,prefix+'.observation.json',lambda x:x.update(fixture_id='WRONG'))
            elif kind=='warmup':mutate(b,prefix+'.observation.json',lambda x:x.update(excluded_from_warm_statistics=False))
            elif kind=='truncation':mutate(b,prefix+'.observation.json',lambda x:x['raw_output'].update(truncated_by_writer=True))
            elif kind=='call':mutate(b,prefix+'.observation.json',lambda x:x['call_kwargs'].update(temperature=1.0))
            else:mutate(b,prefix+'.observation.json',lambda x:x['native'].update(output_tokens=99))
            with self.subTest(kind=kind),self.assertRaises(ValueError):inspect(b)

    def test_copy_inventory_complete_original_and_public_bytes(self):
        data={'a':b'first','sub/b':b'second'}
        rows=[{'relative_path':k,'bytes':len(v),'sha256':c.sha(v),'original_bytes':len(v),'original_sha256':c.sha(v)} for k,v in data.items()]
        good={'schema':'eld-review-run-copy-manifest/1','files':rows}
        self.assertEqual(c.verify_manifest(data.__getitem__,list(data),good)['count'],2)
        for bad in [dict(good,files=rows[:-1]),dict(good,files=rows+[rows[0]]),dict(good,files=[{**rows[0],'original_sha256':'0'*64},rows[1]])]:
            with self.assertRaises(ValueError):c.verify_manifest(data.__getitem__,list(data),bad)

    def test_fixed_sentinel_equal_different_and_unavailable(self):
        a=inspect(synthetic());b=inspect(synthetic('reviewer'),'reviewer');fid='WP13-F04-conflict-v0'
        equal=c.compare_sentinel(a,b);self.assertTrue(equal['both_completed'] and equal['raw_bytes_equal'] and equal['full_policy_scores_equal'])
        changed=copy.deepcopy(b);changed['material'][fid]['raw']+=b'changed';changed['material'][fid]['tokens']=[9]
        changed['material'][fid]['render']['raster'][0]['rgb_sha256']='b'*64
        diff=c.compare_sentinel(a,changed);self.assertFalse(diff['raw_bytes_equal']);self.assertFalse(diff['token_ids_equal']);self.assertFalse(diff['render_rasters_equal'])
        unavailable=c.compare_sentinel(a,inspect(synthetic('reviewer','all_not_run'),'reviewer'))
        self.assertFalse(unavailable['both_completed']);self.assertIsNone(unavailable['raw_bytes_equal']);self.assertIsNone(unavailable['token_ids_equal'])

    def test_process_creation_identity_mismatch_rejected(self):
        for path,key in [('plan.json','supervisor_identity'),('run-result.json','supervisor_identity'),('run-result.json','child_launcher_identity'),('evidence/worker-outcome.json','worker_identity')]:
            b=synthetic()
            def change(value):
                if key=='child_launcher_identity':value[key]['pid']+=1
                else:value[key]['creation_filetime_100ns']+=1
            mutate(b,path,change)
            with self.subTest(path=path),self.assertRaises(ValueError):inspect(b)

    def test_paths_and_missing_tokens_fail_closed(self):
        for path in ('../x','/absolute','C:/secret','a/../b','a//b',''):
            with self.assertRaises(ValueError):c.safe(path)
        b=synthetic();b[2].pop(next(k for k in b[2] if k.endswith('.tokens.json')))
        with self.assertRaises(FileNotFoundError):inspect(b)

    def test_ambiguous_unknown_truth_remains_unjudged_in_full_frame(self):
        for status in ('ambiguous','unknown'):
            a=inspect(synthetic(truth_status=status))['public']
            for key in ('b0','mapping_v1','mapping_v2'):
                self.assertEqual(a['policy_denominators'][key]['truth_'+status],4)
                slots=[s for row in a['records'] for s in row['policy_scores'][key]['slots'] if s['truth_status']==status]
                self.assertEqual(len(slots),4)
                self.assertTrue(all(s['strict_correct_known'] is None for s in slots))

if __name__=='__main__':unittest.main()
