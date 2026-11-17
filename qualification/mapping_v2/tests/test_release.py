import copy
import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from qualification.mapping_v2 import release, scoring
from qualification.mapping_v2.common import protocol, sha, HERE, ROOT, git
from qualification.mapping_v2.protocol.tests.test_protocol import fixture as tiny

SCRATCH = ROOT / '.scratch/wp0013-vocabulary'


def valid_release(p, owner='author'):
    now = datetime.datetime.now(datetime.timezone.utc)
    proof = {'commit': '4'*40, 'path': 'docs/coordination/WP-0013/observation.json', 'sha256': '5'*64}
    return {'schema': 'eld-mapping-v2-release/1', 'owner': owner, 'source_commit': '1'*40, 'executing_head': '2'*40,
            'source_tree': '3'*40, 'protocol_sha256': sha((HERE/'runtime_protocol.json').read_bytes()),
            'comparator_tree': p['comparator_tree'], 'mapping_v1_tree': p['mapping_v1_tree'], 'coverage_v1_tree': p['coverage_v1_tree'],
            'q0_core_tree': p['q0_core_tree'], 'reservation_sha256': p['public_reservation_sha256'],
            'accepted_protocol_sha256': p['accepted_protocol_sha256'], 'accepted_catalog_sha256': p['accepted_catalog_sha256'],
            'corpus_commit': '6'*40, 'runtime_root': p['runtime_roots'][owner],
            'issued_utc': (now-datetime.timedelta(seconds=30)).isoformat(), 'expires_utc': (now+datetime.timedelta(hours=1)).isoformat(),
            'schedule': release.schedule(p, owner),
            'source_review': {**proof, 'path': p['source_review_path'], 'decision': 'accepted', 'reviewed_source_commit': '1'*40},
            'admission_review': {**proof, 'path': p['admission_review_path'], 'decision': 'accepted', 'reviewed_reservation_sha256': p['public_reservation_sha256']},
            'unseal': {**proof, 'path': 'docs/coordination/WP-0013/unseal.json'},
            'lease': {'id': 'CPU-ONLY-TEST', 'owner': owner, 'gpu_uuid': p['gpu']['uuid'], 'sole_lease': True,
                      'scope': 'sole_model_job', 'observations': [proof]}, 'torchvision_local_sha256_TOFU_accepted': True}


class ReleaseTests(unittest.TestCase):
    def setUp(self): SCRATCH.mkdir(parents=True, exist_ok=True)

    def check(self, r, p=None, **kwargs):
        return release.validate_release(r, p or protocol(), r.get('owner', 'author'), head='2'*40, source_tree='3'*40,
                                        protocol_digest=sha((HERE/'runtime_protocol.json').read_bytes()), clean=kwargs.pop('clean', True), **kwargs)

    def test_exact_author_fourteen_reviewer_three_and_conflict_sentinel(self):
        p = protocol()
        for owner, count in [('author', 14), ('reviewer', 3)]:
            r = valid_release(p, owner); self.check(r, p)
            self.assertEqual(count, len(r['schedule'])); self.assertEqual(2, sum(x['excluded'] for x in r['schedule']))
        self.assertEqual('WP13-F04-conflict-v0', release.schedule(p, 'reviewer')[-1]['fixture_id'])
        self.assertEqual(['one_page_conflict'], p['sentinel_policy']['required_categories'])

    def test_mutated_envelope_schedule_source_lease_rejected(self):
        p = protocol(); r = valid_release(p)
        changes = {'schema': 'wrong', 'source_commit': 'short', 'executing_head': '0'*40, 'source_tree': '0'*40,
                   'mapping_v1_tree': '0'*40, 'coverage_v1_tree': '0'*40, 'protocol_sha256': '0'*64,
                   'accepted_catalog_sha256': '0'*64, 'accepted_protocol_sha256': '0'*64,
                   'runtime_root': 'C:/other', 'reservation_sha256': '0'*64, 'schedule': r['schedule'][:-1],
                   'expires_utc': '2000-01-01T00:00:00Z'}
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(PermissionError): self.check({**r, key: value})
        with self.assertRaises(PermissionError): self.check(r, clean=False)
        for key, field, value in [('source_review', 'decision', 'pending'), ('source_review', 'reviewed_source_commit', '0'*40),
                                  ('admission_review', 'reviewed_reservation_sha256', '0'*64), ('lease', 'scope', 'hardware_exclusive')]:
            bad = copy.deepcopy(r); bad[key][field] = value
            with self.subTest(key=key, field=field), self.assertRaises(PermissionError): self.check(bad)
        for changed in ({**p, 'fresh_fixtures': list(reversed(p['fresh_fixtures']))}, {**p, 'reviewer_sentinel': 'WP13-F04-unsupported-v0'}):
            with self.assertRaises(PermissionError): release.schedule(changed, 'author')

    def test_source_proof_failure_precedes_fresh_reads(self):
        p = protocol(); r = valid_release(p); authority = '7'*40; path = 'docs/coordination/WP-0013/releases/author.json'
        public = git('show', p['public_reservation_commit'] + ':' + p['public_reservation_path'])
        def fakegit(*args):
            if args == ('rev-parse', 'HEAD'): return b'2'*40
            if args == ('status', '--porcelain'): return b''
            if args == ('show', authority + ':' + path): return json.dumps(r).encode()
            if args == ('show', p['public_reservation_commit'] + ':' + p['public_reservation_path']): return public
            return b'incorrect-proof-digest'
        def faketree(rev, path): return '3'*40 if path == 'qualification/mapping_v2' else p['q0_core_tree']
        with patch.object(release, 'git', side_effect=fakegit), patch.object(release, 'tree', side_effect=faketree), \
             patch.object(release, 'verify_frozen_mappers'), patch.object(release, 'read_artifact', side_effect=AssertionError('Fresh content read')) as read:
            with self.assertRaisesRegex(PermissionError, 'digest'): release.read_release(authority, path, 'author')
            read.assert_not_called()

    def test_absent_release_has_no_fresh_access(self):
        with patch.object(release, 'read_artifact', side_effect=AssertionError('Fresh content read')) as read:
            for authority, path in [(None, None), ('bad', 'bad'), ('1'*40, '../escape'), ('1'*40, 'docs/coordination/WP-0011/releases/author.json')]:
                with self.assertRaises(PermissionError): release.read_release(authority, path, 'author')
            read.assert_not_called()

    def packet(self, run, owner='author'):
        raw = tiny()[2]['ideal_native'].encode(); (run/'raw.txt').write_bytes(raw)
        obs = {'flags': [], 'raw_output': {'name': 'raw.txt', 'sha256_written': sha(raw), 'truncated_by_writer': False}}
        (run/'obs.json').write_text(json.dumps(obs))
        return {'schema': 'eld-mapping-v2-run/1', 'failure': None,
                'calls': [{**c, 'status': 'completed', 'observation': 'obs.json', 'observation_status': 'available'} for c in release.schedule(protocol(), owner)]}

    def test_complete_record_state_machine_and_observation_failures(self):
        p = protocol()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            run = Path(tmp)
            for owner in ('author', 'reviewer'):
                good = self.packet(run, owner)
                self.assertEqual(14 if owner == 'author' else 3, len(scoring.validated_calls(good, p, owner, run)[0]))
                for status in ('failed', 'not_run_after_failure'):
                    bad = copy.deepcopy(good); bad['failure'] = 'FIRST_CALL_FAILURE'; bad['calls'][0]['status'] = status
                    if status == 'not_run_after_failure': bad['calls'][0].update(observation=None, observation_status='absent')
                    with self.assertRaisesRegex(PermissionError, 'after first failure'): scoring.validated_calls(bad, p, owner, run)
                all_absent = copy.deepcopy(good); all_absent['failure'] = 'PREFLIGHT_FAILURE'
                for call in all_absent['calls']: call.update(status='not_run_after_failure', observation=None, observation_status='absent')
                self.assertTrue(all(raw is None for raw in scoring.validated_calls(all_absent, p, owner, run)[1]))
                all_absent['failure'] = None
                with self.assertRaises(PermissionError): scoring.validated_calls(all_absent, p, owner, run)
                good['failure'] = 'POST_FINALIZATION_FAILURE'
                self.assertEqual(len(good['calls']), len(scoring.validated_calls(good, p, owner, run)[0]))
            for mutation in ({}, {'flags': ['failure']}, {'flags': [], 'error': 'failure'},
                             {'flags': [], 'raw_output': {'name': 'raw.txt', 'sha256_written': sha(b'wrong'), 'truncated_by_writer': False}}):
                (run/'obs.json').write_text(json.dumps(mutation))
                with self.assertRaises(PermissionError): scoring.validated_calls(good, p, 'reviewer', run)

    def test_score_run_preserves_full_failed_and_completed_populations(self):
        p = protocol()
        for owner, mode in [('author', 'all_absent'), ('author', 'partial'), ('author', 'post_failure'), ('reviewer', 'post_failure')]:
            with self.subTest(owner=owner, mode=mode), tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
                root = Path(tmp); r = valid_release(p, owner); r['runtime_root'] = str(root)
                run = root/'runs'/owner/'CPU'; run.mkdir(parents=True)
                result = self.packet(run, owner); result.update(release=r, executing_head=r['executing_head'], failure='CPU retained failure')
                if mode != 'post_failure':
                    for index, call in enumerate(result['calls']):
                        if mode == 'all_absent' or index >= 3:
                            call.update(status='failed' if mode == 'partial' and index == 3 else 'not_run_after_failure', observation=None,
                                        observation_status='unavailable' if mode == 'partial' and index == 3 else 'absent')
                (run/'run-result.json').write_text(json.dumps(result))
                by_path = {}
                for fx in p['fresh_fixtures']:
                    triple = tiny(fx['case'], fx['family_id'])[:3]
                    for role, value in zip(('expected', 'reference', 'policy'), triple):
                        artifact = next(a for a in fx['artifacts'] if a['role'] == role); by_path[artifact['path']] = json.dumps(value).encode()
                with patch.object(scoring, 'read_release', return_value=r), patch.object(scoring, 'read_artifact', side_effect=lambda r, p, a: by_path[a['path']]):
                    scoring.score_run(run, root/'scores.json', 'CPU', 'CPU', owner)
                packet = json.loads((root/'scores.json').read_text()); self.assertEqual(12 if owner == 'author' else 1, len(packet['records']))
                self.assertEqual(12 if owner == 'author' else 1, sum(row['scores']['mapping_v2']['fields']['total'] for row in packet['records']))
                if owner == 'author':
                    for key in ('b0', 'mapping_v1', 'mapping_v2'):
                        summary = packet['policy_summary'][key]['all']; self.assertEqual(12, summary['documents'])
                        self.assertEqual(12 if mode == 'post_failure' else 1 if mode == 'partial' else 0, summary['completed_documents'])

    def test_actual_score_run_rejects_completed_after_failed_warmup_before_artifacts(self):
        p = protocol()
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root = Path(tmp); r = valid_release(p); r['runtime_root'] = str(root); run = root/'runs/author/CPU'; run.mkdir(parents=True)
            good = self.packet(run); good.update(release=r, executing_head=r['executing_head'], failure='CPU failure')
            self.assertEqual(14, len(scoring.validated_calls(good, p, 'author', run)[0]))
            good['calls'][0]['status'] = 'failed'; (run/'run-result.json').write_text(json.dumps(good))
            with patch.object(scoring, 'read_release', return_value=r), patch.object(scoring, 'read_artifact', side_effect=AssertionError('Scored invalid history')) as read:
                with self.assertRaisesRegex(PermissionError, 'after first failure'): scoring.score_run(run, root/'scores.json', 'CPU', 'CPU', 'author')
                read.assert_not_called()


if __name__ == '__main__': unittest.main()
