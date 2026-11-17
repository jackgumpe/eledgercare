import copy
import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from qualification.coverage_v1 import release,scoring
from qualification.coverage_v1.common import protocol,sha,HERE,ROOT,git
from test_diagnostics import tiny

def valid_release(p,owner='author'):
    now=datetime.datetime.now(datetime.timezone.utc)
    proof={'commit':'4'*40,'path':'docs/coordination/WP-0011/observation.json','sha256':'5'*64}
    return {'schema':'eld-coverage-v1-release/1','owner':owner,'source_commit':'1'*40,'executing_head':'2'*40,
        'source_tree':'3'*40,'protocol_sha256':sha((HERE/'protocol.json').read_bytes()),'comparator_tree':p['comparator_tree'],
        'mapping_v1_tree':p['mapping_v1_tree'],'q0_core_tree':p['q0_core_tree'],'reservation_sha256':p['public_reservation_sha256'],
        'corpus_commit':'6'*40,'runtime_root':p['runtime_roots'][owner],
        'issued_utc':(now-datetime.timedelta(seconds=30)).isoformat(),'expires_utc':(now+datetime.timedelta(hours=1)).isoformat(),
        'schedule':release.schedule(p,owner),
        'source_review':{**proof,'path':p['source_review_path'],'decision':'accepted','reviewed_source_commit':'1'*40},
        'admission_review':{**proof,'path':p['admission_review_path'],'decision':'accepted','reviewed_reservation_sha256':p['public_reservation_sha256']},
        'unseal':{**proof,'path':'docs/coordination/WP-0011/unseal.json'},
        'lease':{'id':'CPU-ONLY-TEST','owner':owner,'gpu_uuid':p['gpu']['uuid'],'sole_lease':True,'scope':'sole_model_job','observations':[proof]},
        'torchvision_local_sha256_TOFU_accepted':True}

class ReleaseTests(unittest.TestCase):
    def check(self,r,p=None,**kw):
        return release.validate_release(r,p or protocol(),r.get('owner','author'),head='2'*40,source_tree='3'*40,
            protocol_digest=sha((HERE/'protocol.json').read_bytes()),clean=kw.pop('clean',True),**kw)

    def test_exact_fourteen_and_three_call_schedules_and_policy(self):
        p=protocol()
        for owner,count in [('author',14),('reviewer',3)]:
            r=valid_release(p,owner);self.check(r,p);self.assertEqual(len(r['schedule']),count)
            self.assertEqual(sum(x['excluded'] for x in r['schedule']),2)
        self.assertEqual(release.schedule(p,'reviewer')[-1]['fixture_id'],'WP11-F03-degraded-v0')
        policy=p['sentinel_policy'];self.assertEqual(policy['fixture_id'],p['reviewer_sentinel'])
        self.assertEqual(policy['page_counts'],[p['fresh_fixtures'][-1]['page_count']])
        self.assertEqual(policy['measured_document_count'],1)
        self.assertEqual(policy['required_categories'],['one_page_degraded'])
        self.assertEqual(p['fresh_fixtures'][-1]['condition'],'degraded')
        self.assertEqual(p['diagnostic_matrix']['primary_documents'],12)

    def test_changed_schedule_order_subset_sentinel_and_binding_rejected(self):
        p=protocol();r=valid_release(p)
        for k,v in {'schema':'wrong','source_commit':'short','executing_head':'0'*40,'source_tree':'0'*40,
            'mapping_v1_tree':'0'*40,'protocol_sha256':'0'*64,'comparator_tree':'0'*40,'runtime_root':'C:/other',
            'reservation_sha256':'0'*64,'schedule':r['schedule'][:-1],'expires_utc':'2000-01-01T00:00:00Z'}.items():
            with self.subTest(key=k),self.assertRaises(PermissionError):self.check({**r,k:v})
        with self.assertRaises(PermissionError):self.check(r,clean=False)
        for changed in ({**p,'fresh_fixtures':list(reversed(p['fresh_fixtures']))},{**p,'reviewer_sentinel':'WP11-F01-control-v0'}):
            with self.assertRaises(PermissionError):release.schedule(changed,'author')
        for key,field,value in [('source_review','decision','pending'),('source_review','reviewed_source_commit','0'*40),
            ('admission_review','reviewed_reservation_sha256','0'*64),('lease','scope','hardware_exclusive')]:
            bad=copy.deepcopy(r);bad[key][field]=value
            with self.assertRaises(PermissionError):self.check(bad)

    def test_source_proof_failure_precedes_every_fresh_read(self):
        p=protocol();r=valid_release(p);authority='7'*40;path='docs/coordination/WP-0011/releases/author.json'
        public=git('show',p['public_reservation_commit']+':'+p['public_reservation_path'])
        def fakegit(*args):
            if args==('rev-parse','HEAD'):return b'2'*40
            if args==('status','--porcelain'):return b''
            if args==('show',authority+':'+path):return json.dumps(r).encode()
            if args==('show',p['public_reservation_commit']+':'+p['public_reservation_path']):return public
            return b'incorrect-proof-digest'
        def faketree(rev,path):return '3'*40 if path=='qualification/coverage_v1' else p['q0_core_tree']
        with patch.object(release,'git',side_effect=fakegit),patch.object(release,'tree',side_effect=faketree),patch.object(release,'verify_frozen_mappers'),patch.object(release,'read_artifact',side_effect=AssertionError('Fresh content read')) as read:
            with self.assertRaisesRegex(PermissionError,'digest'):release.read_release(authority,path,'author')
            read.assert_not_called()

    def test_absent_release_never_opens_artifacts(self):
        with patch.object(release,'read_artifact',side_effect=AssertionError('Fresh content read')) as read:
            for authority,path in [(None,None),('bad','bad'),('1'*40,'../escape'),('1'*40,'docs/coordination/WP-0009/releases/author.json')]:
                with self.assertRaises(PermissionError):release.read_release(authority,path,'author')
            read.assert_not_called()

    def test_failed_author_packet_keeps_twelve_and_reviewer_only_one(self):
        p=protocol();scratch=ROOT/'.scratch/wp0011-coverage';scratch.mkdir(parents=True,exist_ok=True)
        for owner,mode in (('author','partial'),('reviewer','partial'),('author','post_failure')):
            with self.subTest(owner=owner,mode=mode),tempfile.TemporaryDirectory(dir=scratch) as tmp:
                root=Path(tmp);r=valid_release(p,owner);r['runtime_root']=str(root);run=root/'runs'/owner/'CPU';run.mkdir(parents=True)
                plan=release.schedule(p,owner);calls=[]
                for i,call in enumerate(plan):
                    completed=i<=2 or mode=='post_failure';observation=None
                    if completed:
                        e,ref,a=tiny()
                        raw=a['ideal_native'].encode();(run/'raw.txt').write_bytes(raw)
                        (run/'observation.json').write_text(json.dumps({'flags':[],'raw_output':{'name':'raw.txt','sha256_written':sha(raw),'truncated_by_writer':False}}))
                        observation='observation.json'
                    calls.append({**call,'status':'completed' if completed else 'failed' if i==3 else 'not_run_after_failure','observation':observation,
                                  'observation_status':'available' if completed else 'unavailable' if i==3 else 'absent'})
                (run/'run-result.json').write_text(json.dumps({'schema':'eld-coverage-v1-run/1','release':r,'calls':calls,'failure':'CPU failure' if owner=='author' else None}))
                by_path={}
                for fx in p['fresh_fixtures']:
                    triple=tiny(fx['condition'],fx['family_id'])
                    for role,value in zip(('expected','reference','annotations'),triple):
                        artifact=next(x for x in fx['artifacts'] if x['role']==role);by_path[artifact['sealed_relative_path']]=json.dumps(value).encode()
                with patch.object(scoring,'read_release',return_value=r),patch.object(scoring,'read_artifact',side_effect=lambda r,p,a:by_path[a['sealed_relative_path']]):
                    scoring.score_run(run,root/'scores.json','CPU','CPU',owner)
                packet=json.loads((root/'scores.json').read_text());self.assertEqual(len(packet['records']),12 if owner=='author' else 1)
                self.assertEqual(sum(x['scores']['b0']['fields']['total'] for x in packet['records']),12 if owner=='author' else 1)
                if owner=='author':
                    self.assertEqual(packet['diagnostic_pairing']['unavailable_presence_pairs'],0 if mode=='post_failure' else 9)
                    self.assertEqual(sum(x['diagnostic']['presence_denominator']['unavailable_slots'] for x in packet['records']),0 if mode=='post_failure' else 11)
                    self.assertEqual(sum(x['scores']['b0']['fields']['correct'] for x in packet['records']),12 if mode=='post_failure' else 1)
                else:self.assertEqual(packet['diagnostic_pairing']['preselected_id'],'WP11-F03-degraded-v0')

    def test_call_state_machine_rejects_malformed_and_after_failure(self):
        p=protocol();scratch=ROOT/'.scratch/wp0011-coverage';scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            run=Path(tmp);raw=tiny()[2]['ideal_native'].encode();(run/'raw.txt').write_bytes(raw)
            observation={'flags':[],'raw_output':{'name':'raw.txt','sha256_written':sha(raw),'truncated_by_writer':False}}
            (run/'obs.json').write_text(json.dumps(observation))
            for owner in ('author','reviewer'):
                good={'schema':'eld-coverage-v1-run/1','failure':None,'calls':[{**c,'status':'completed','observation':'obs.json','observation_status':'available'} for c in release.schedule(p,owner)]}
                self.assertEqual(len(scoring.validated_calls(good,p,owner,run)[0]),14 if owner=='author' else 3)
                mutations=[('failed_warmup',lambda x:x['calls'][0].update(status='failed')),
                    ('gap_warmup',lambda x:x['calls'][0].update(status='not_run_after_failure',observation=None,observation_status='absent')),
                    ('missing_status',lambda x:x['calls'][0].pop('status')),
                    ('unknown_status',lambda x:x['calls'][0].update(status='success')),
                    ('missing_observation',lambda x:x['calls'][0].update(observation=None)),
                    ('unavailable_completed',lambda x:x['calls'][0].update(observation_status='unavailable')),
                    ('short_schedule',lambda x:x['calls'].pop()),
                    ('order_change',lambda x:x['calls'].reverse()),
                    ('missing_run_failure',lambda x:x.pop('failure'))]
                for name,mutate in mutations:
                    bad=copy.deepcopy(good);mutate(bad)
                    if name in ('failed_warmup','gap_warmup'):bad['failure']='INJECTED_FIRST_CALL_FAILURE'
                    with self.subTest(owner=owner,case=name),self.assertRaises(PermissionError):scoring.validated_calls(bad,p,owner,run)
                absent=copy.deepcopy(good)
                for c in absent['calls']:c.update(status='not_run_after_failure',observation=None,observation_status='absent')
                absent['failure']='PRE_EXECUTION_FAILURE';self.assertTrue(all(r is None for r in scoring.validated_calls(absent,p,owner,run)[1]))
                absent['failure']=None
                with self.assertRaises(PermissionError):scoring.validated_calls(absent,p,owner,run)
            for malformed in ({},{'flags':['failed'],'raw_output':observation['raw_output']},
                    {'flags':[],'raw_output':{**observation['raw_output'],'truncated_by_writer':True}},
                    {'flags':[],'error':'reported failure','raw_output':observation['raw_output']}):
                (run/'obs.json').write_text(json.dumps(malformed))
                with self.subTest(record=malformed),self.assertRaises(PermissionError):scoring.validated_calls(good,p,'reviewer',run)
            (run/'obs.json').unlink()
            with self.assertRaises(FileNotFoundError):scoring.validated_calls(good,p,'reviewer',run)

    def test_actual_score_run_rejects_otherwise_valid_completed_after_failed_warmup(self):
        p=protocol();scratch=ROOT/'.scratch/wp0011-coverage';scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            root=Path(tmp);r=valid_release(p);r['runtime_root']=str(root);run=root/'runs/author/CPU';run.mkdir(parents=True)
            raw=tiny()[2]['ideal_native'].encode();(run/'raw.txt').write_bytes(raw)
            (run/'obs.json').write_text(json.dumps({'flags':[],'raw_output':{'name':'raw.txt','sha256_written':sha(raw),'truncated_by_writer':False}}))
            result={'schema':'eld-coverage-v1-run/1','release':r,'failure':'FIRST_WARMUP_FAILED',
                'calls':[{**c,'status':'completed','observation':'obs.json','observation_status':'available'} for c in release.schedule(p,'author')]}
            # Positive: the complete revised record is accepted even with a run-level
            # post-finalization failure. Only the first call state changes below.
            self.assertEqual(len(scoring.validated_calls(result,p,'author',run)[0]),14)
            result['calls'][0]['status']='failed'
            (run/'run-result.json').write_text(json.dumps(result))
            with patch.object(scoring,'read_release',return_value=r),patch.object(scoring,'read_artifact',side_effect=AssertionError('Scored invalid history')) as read:
                with self.assertRaisesRegex(PermissionError,'after first failure'):
                    scoring.score_run(run,root/'scores.json','CPU','CPU','author')
                read.assert_not_called()
            self.assertFalse((root/'scores.json').exists())

if __name__=='__main__':unittest.main()
