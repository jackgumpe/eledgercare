"""Public synthetic helper tests; never represent these as actual runtime evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

import compare_published as c

path=Path(__file__).resolve().parent.parent/'source/probes_v2.py'
spec=importlib.util.spec_from_file_location('public_review_fixture',path);tiny=importlib.util.module_from_spec(spec);spec.loader.exec_module(tiny)

def synthetic(owner='author',mode='completed'):
    p=c.protocol();plan=c.schedule(p,owner);head='2'*40
    release={'executing_head':head,'schedule':plan}
    result={'schema':'eld-coverage-v1-run/1','release':release,'executing_head':head,'failure':None,'calls':[],
            'child_returncode':0,'observed_child_exit':True,'finalization_errors':[],'final_observation_status':{'post_observers':'available'}}
    files={};triples={f['fixture_id']:tiny.fixture(f['condition'],f['family_id']) for f in p['fresh_fixtures']}
    fixtures={f['fixture_id']:f for f in p['historical_warmups']+p['fresh_fixtures']}
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
        raw=('<PAGE>'*fx['page_count']+'<BLOCK>text[0,0,900,30]<FORK>Work Order ID: R42').encode();tokens=[1,2,3]
        tokenbytes=json.dumps(tokens).encode();files[prefix+'.raw.txt']=raw;files[prefix+'.tokens.json']=tokenbytes
        kwargs=dict(p['call']['fixed_kwargs'],max_new_tokens=8000*fx['page_count'],ngram_window=1024 if fx['page_count']>1 else 128)
        obs={'fixture_id':fid,'family_id':fx['family_id'],'kind':call['kind'],'page_count_in':fx['page_count'],
             'excluded_from_warm_statistics':call['excluded'],'flags':[],'call_kwargs':kwargs,
             'raw_output':{'name':label+'.raw.txt','bytes_written':len(raw),'sha256_written':c.sha(raw),'truncated_by_writer':False,'utf8_lossless':True},
             'token_ids_file':{'name':label+'.tokens.json','bytes_written':len(tokenbytes),'sha256_written':c.sha(tokenbytes)},
             'native':{'token_ids_sha256':c.sha(json.dumps(tokens).encode()),'text_sha256':c.sha(raw),'finish_reason':'stop',
                       'expected_pages':fx['page_count'],'num_pages_out':fx['page_count'],'output_tokens':3,'prompt_len':30},
             'kernel_path':{'label':'triton_import_failed_dense_fallback'},'timing':None,'host_memory':{'unknown':None},'cuda_memory':None}
        put(prefix+'.observation.json',obs)
        pdf=fx['sha256'] if fid in p['warmups'] else next(a['sha256'] for a in fx['artifacts'] if a['role']=='pdf')
        put(prefix+'.render.json',{'pdf_sha256':pdf,'raster':[{'page':n+1,'width':10,'height':20,'rgb_sha256':'a'*64} for n in range(fx['page_count'])],'render_s':None})
    if mode!='completed':result['failure']='SYNTHETIC_POST_FAILURE' if mode=='post_failure' else 'SYNTHETIC_FIRST_FAILURE'
    if mode=='post_failure':result['final_observation_status']['post_observers']='unavailable';result['finalization_errors']=[{'stage':'post_observer_validation'}]
    put('run-result.json',result);put('plan.json',{'release':release,'executing_head':head,'calls':plan})
    def read(name):
        if name not in files:raise FileNotFoundError(name)
        return files[name]
    return p,release,files,read,lambda fid:triples[fid]

def inspect(bundle,owner='author',scores=None):
    p,r,_,read,fixtures=bundle
    return c.inspect_run(read,p,r,owner,fixtures,scores)
def mutate(bundle,path,fn):
    files=bundle[2];value=c.load(files[path]);fn(value);files[path]=json.dumps(value).encode()

class ComparisonTests(unittest.TestCase):
    def test_complete_twelve_one_and_full_packet_reproduction(self):
        for owner,n in [('author',12),('reviewer',1)]:
            b=synthetic(owner);a=inspect(b,owner)
            self.assertEqual(a['public']['primary_document_denominator'],n)
            self.assertEqual(len(a['public']['calls']),n+2)
            self.assertEqual(a['public']['presence_denominator'],{'all_expected_slots':n,'eligible_slots':n,'unavailable_slots':0})
            self.assertTrue(all(x['timing'] is None and x['cuda_memory'] is None for x in a['public']['calls']))
            if owner=='author':self.assertEqual(a['public']['diagnostic_pairing']['paired_comparisons'],9)
            inspect(b,owner,a['public']['complete_reproduced_packet'])

    def test_full_prediction_score_diagnostic_and_pair_mutations_rejected(self):
        b=synthetic();original=inspect(b)['public']['complete_reproduced_packet']
        mutations=[lambda x:x['records'][0]['predictions']['b0'].update(parse_errors=['changed']),
                   lambda x:x['records'][0]['scores']['b0']['fields'].update(correct=0),
                   lambda x:x['records'][0]['diagnostic']['slots'][0]['value_presence'].update(count=0),
                   lambda x:x['diagnostic_pairing'].update(eligible_presence_pairs=0),
                   lambda x:x['historical_summary']['b0'].update(extra='changed')]
        for fn in mutations:
            bad=copy.deepcopy(original);fn(bad)
            with self.assertRaisesRegex(ValueError,'Published full'):inspect(b,scores=bad)

    def test_after_failure_and_gap_rejected_with_exact_reason(self):
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
                correct=sum(x['scores']['b0']['fields']['correct'] for x in a['records'])
                self.assertEqual(correct,0 if mode=='all_not_run' else n if mode=='post_failure' else 1)
                if mode=='all_not_run':self.assertEqual(a['presence_denominator']['unavailable_slots'],n)
                if owner=='author' and mode!='post_failure':self.assertEqual(a['diagnostic_pairing']['unavailable_presence_pairs'],9)

    def test_raw_token_render_and_observation_mismatch_rejected(self):
        for kind in ('raw','tokens','render','identity','warmup','truncation'):
            b=synthetic();label=c.schedule(b[0],'author')[0]['fixture_id']+'.warmup';prefix='evidence/'+label
            if kind=='raw':b[2][prefix+'.raw.txt']+=b'X'
            elif kind=='tokens':b[2][prefix+'.tokens.json']=b'[9, 8, 7]'
            elif kind=='render':mutate(b,prefix+'.render.json',lambda x:x.update(pdf_sha256='0'*64))
            elif kind=='identity':mutate(b,prefix+'.observation.json',lambda x:x.update(fixture_id='WRONG'))
            elif kind=='warmup':mutate(b,prefix+'.observation.json',lambda x:x.update(excluded_from_warm_statistics=False))
            else:mutate(b,prefix+'.observation.json',lambda x:x['raw_output'].update(truncated_by_writer=True))
            with self.subTest(kind=kind),self.assertRaises(ValueError):inspect(b)

    def test_copy_inventory_completeness_and_original_identity(self):
        data={'a':b'first','sub/b':b'second'}
        rows=[{'relative_path':k,'bytes':len(v),'sha256':c.sha(v),'original_bytes':len(v),'original_sha256':c.sha(v)} for k,v in data.items()]
        good={'schema':'eld-review-run-copy-manifest/1','files':rows}
        self.assertEqual(c.verify_manifest(data.__getitem__,list(data),good)['count'],2)
        for bad in [dict(good,files=rows[:-1]),dict(good,files=rows+[rows[0]]),dict(good,files=[{**rows[0],'original_sha256':'0'*64},rows[1]])]:
            with self.assertRaises(ValueError):c.verify_manifest(data.__getitem__,list(data),bad)

    def test_fixed_sentinel_differences_and_unavailable_are_honest(self):
        a=inspect(synthetic());b=inspect(synthetic('reviewer'),'reviewer');fid='WP11-F03-degraded-v0'
        equal=c.compare_sentinel(a,b);self.assertTrue(equal['both_completed'] and equal['raw_bytes_equal'] and equal['full_diagnostics_equal'])
        changed=copy.deepcopy(b);changed['material'][fid]['raw']+=b'changed';changed['material'][fid]['tokens']=[9]
        changed['material'][fid]['render']['raster'][0]['rgb_sha256']='b'*64
        difference=c.compare_sentinel(a,changed)
        self.assertFalse(difference['raw_bytes_equal']);self.assertFalse(difference['token_ids_equal']);self.assertFalse(difference['render_rasters_equal'])
        unavailable=c.compare_sentinel(a,inspect(synthetic('reviewer','all_not_run'),'reviewer'))
        self.assertFalse(unavailable['both_completed']);self.assertIsNone(unavailable['raw_bytes_equal']);self.assertIsNone(unavailable['token_ids_equal'])

    def test_path_escape_and_missing_records_fail_closed(self):
        for path in ('../x','/absolute','C:/secret','a/../b','a//b',''):
            with self.assertRaises(ValueError):c.safe(path)
        b=synthetic();b[2].pop(next(k for k in b[2] if k.endswith('.tokens.json')))
        with self.assertRaises(FileNotFoundError):inspect(b)

if __name__=='__main__':unittest.main()
