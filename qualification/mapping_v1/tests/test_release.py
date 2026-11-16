import copy
import datetime
import unittest
from unittest.mock import patch
from qualification.mapping_v1 import release
from qualification.mapping_v1.common import protocol,sha,HERE,ROOT,load_json
from qualification.mapping_v1.scoring import validate_expected_reference


def valid_release(p,owner='author'):
    now=datetime.datetime.now(datetime.timezone.utc)
    proof={'commit':'4'*40,'path':'docs/coordination/WP-0009/observation.json','sha256':'5'*64}
    return {'schema':'eld-mapping-v1-release/1','owner':owner,'source_commit':'1'*40,'executing_head':'2'*40,
            'source_tree':'3'*40,'protocol_sha256':sha((HERE/'protocol.json').read_bytes()),
            'comparator_tree':p['comparator_tree'],'q0_core_tree':p['q0_core_tree'],
            'reservation_sha256':p['public_reservation_sha256'],'corpus_commit':'6'*40,'runtime_root':p['runtime_roots'][owner],
            'issued_utc':(now-datetime.timedelta(seconds=30)).isoformat(),'expires_utc':(now+datetime.timedelta(hours=1)).isoformat(),
            'schedule':release.schedule(p,owner),'source_review':{**proof,'path':p['source_review_path']},
            'admission_review':{'commit':p['admission_review_commit'],'path':p['admission_review_path'],'sha256':p['admission_review_sha256']},
            'unseal':{**proof,'path':'docs/coordination/WP-0009/unseal.json'},
            'lease':{'id':'CPU-ONLY-TEST','owner':owner,'gpu_uuid':p['gpu']['uuid'],'sole_lease':True,'scope':'sole_model_job','observations':[proof]},
            'torchvision_local_sha256_TOFU_accepted':True}


class ReleaseTests(unittest.TestCase):
    def validate(self,r,p=None,**kwargs):
        p=p or protocol()
        return release.validate_release(r,p,r.get('owner','author'),head='2'*40,source_tree='3'*40,
                                        protocol_digest=sha((HERE/'protocol.json').read_bytes()),clean=kwargs.pop('clean',True),**kwargs)

    def test_exact_author_and_preselected_reviewer_schedule(self):
        p=protocol()
        for owner,count in [('author',6),('reviewer',3)]:
            r=valid_release(p,owner);self.validate(r,p);self.assertEqual(len(r['schedule']),count)
            self.assertEqual(sum(not x['excluded'] for x in r['schedule']),count-2)
        self.assertEqual(release.schedule(p,'reviewer')[-1]['fixture_id'],'WP09-F04-v0')

    def test_declared_sentinel_policy_matches_finite_schedule_and_scope(self):
        p=protocol();policy=p['sentinel_policy'];plan=release.schedule(p,'reviewer')
        warmups=[row for row in plan if row['excluded']]
        measured=[row for row in plan if not row['excluded']]
        self.assertEqual([row['fixture_id'] for row in warmups],p['warmups'])
        self.assertEqual(len(warmups),2)
        self.assertTrue(all(row['kind']=='warmup' for row in warmups))
        self.assertEqual([row['fixture_id'] for row in measured],[p['reviewer_sentinel']])
        self.assertEqual(len(measured),1)
        self.assertEqual(policy['measured_document_count'],len(measured))
        self.assertTrue(all(row['kind']=='measured' for row in measured))
        fixtures={fx['fixture_id']:fx for fx in p['fresh_fixtures']}
        page_counts=[fixtures[row['fixture_id']]['page_count'] for row in measured]
        self.assertEqual(page_counts,[3])
        self.assertEqual(policy['page_counts'],page_counts)
        actual_categories=sorted({'single_page' if count==1 else 'multi_page' for count in page_counts})
        self.assertEqual(policy['required_categories'],actual_categories)
        self.assertEqual(policy['content_scope'],'clean_digital_only')
        self.assertEqual(policy['not_covered_categories'],['single_page','raster_or_hybrid'])
        self.assertTrue(set(policy['required_categories']).isdisjoint(policy['not_covered_categories']))
        self.assertEqual(policy['chosen_by'],'independent reviewer before result access')
        self.assertIs(policy['ids_bound_in_release'],True)

    def test_missing_wrong_and_expired_envelopes(self):
        p=protocol();r=valid_release(p)
        with self.assertRaises(PermissionError):self.validate({})
        mutations={'schema':'bad','executing_head':'0'*40,'source_tree':'0'*40,'source_commit':'short',
                   'protocol_sha256':'0'*64,'comparator_tree':'0'*40,'q0_core_tree':'0'*40,
                   'reservation_sha256':'0'*64,'runtime_root':'C:/other','schedule':r['schedule'][:-1],
                   'torchvision_local_sha256_TOFU_accepted':False,'corpus_commit':'bad',
                   'expires_utc':'2000-01-01T00:00:00Z','issued_utc':'2999-01-01T00:00:00Z'}
        for k,v in mutations.items():
            with self.subTest(key=k),self.assertRaises(PermissionError):self.validate({**r,k:v})
        with self.assertRaises(PermissionError):self.validate(r,clean=False)
        for k in ('source_review','admission_review','unseal'):
            bad=copy.deepcopy(r);bad[k]['path']='wrong'
            with self.subTest(key=k),self.assertRaises(PermissionError):self.validate(bad)
        for k,v in [('sole_lease',False),('scope','hardware_exclusive'),('owner','reviewer'),('gpu_uuid','other'),('observations',[])]:
            bad=copy.deepcopy(r);bad['lease'][k]=v
            with self.subTest(key=k),self.assertRaises(PermissionError):self.validate(bad)

    def test_no_retry_duplicate_schedule_or_changed_sentinel(self):
        p=protocol();r=valid_release(p)
        for plan in [r['schedule']+[r['schedule'][-1]],list(reversed(r['schedule'])),r['schedule'][2:]]:
            with self.assertRaises(PermissionError):self.validate({**r,'schedule':plan})
        with self.assertRaises(PermissionError):release.schedule({**p,'reviewer_sentinel':'WP09-F01-v0'},'reviewer')

    def test_entry_rejects_before_any_fresh_read_or_runtime_import(self):
        with patch.object(release,'read_artifact',side_effect=AssertionError('Fresh content read')):
            for authority,path in [(None,None),('short','bad'),('1'*40,'../escape'),('1'*40,'docs/coordination/WP-0007/release.json')]:
                with self.subTest(authority=authority,path=path),self.assertRaises(PermissionError):release.read_release(authority,path,'author')

    def test_old_public_schema_and_malformed_reference(self):
        p=protocol();fx=p['historical_warmups'][0];e=load_json(ROOT/fx['expected_ground_truth_path'])
        ref={'pages':['CPU synthetic reference'],'coverage':{}}
        validate_expected_reference(e,ref,fx)
        for bad in [{},{'pages':[1],'coverage':{}},{'pages':[],'coverage':{}},{'pages':['x'],'coverage':[]}]:
            with self.assertRaises(PermissionError):validate_expected_reference(e,bad,fx)
        with self.assertRaises(PermissionError):validate_expected_reference({**e,'fixture_id':'wrong'},ref,fx)


if __name__=='__main__':unittest.main()
