"""Frozen CPU implementation checks and complete exposed historical regression."""
import argparse
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'transformers', 'triton', 'pypdfium2') or fullname == 'q0harness.backend_torch':
            raise RuntimeError('CPU implementation checks prohibit model/renderer imports: ' + fullname)


sys.meta_path.insert(0, NoModelImports())
from qualification.mapping_v2.common import HERE, git, sha, write, protocol, verify_frozen_mappers
from qualification.mapping_v2.scoring import paired
from qualification.mapping_v2.protocol.tests import test_protocol
from corpus import reference_for

BASE = 'ad7309f2079ed11bc4a63e52567e6a1e5fba1868'
OLD = {'dev': 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6',
       'eval_holdout': 'docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d',
       'supplement': 'docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca'}


def change_counts(scores, left):
    result = {}
    for metric, credit in [('fields', 'credited_exact'), ('cells', 'credited_exact'), ('normalized_fields', 'credited_exact'),
                           ('normalized_cells', 'credited_exact'), ('rows', 'exact'), ('expected_absences', 'verified_absent')]:
        before = scores[left][metric]['details']; after = scores['mapping_v2'][metric]['details']
        if len(before) != len(after): raise AssertionError('Original comparison denominator changed')
        result[metric] = {'total': len(before), 'before_correct': scores[left][metric]['correct'],
                          'v2_correct': scores['mapping_v2'][metric]['correct'],
                          'gains': sum(not a[credit] and b[credit] for a, b in zip(before, after)),
                          'losses': sum(a[credit] and not b[credit] for a, b in zip(before, after))}
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True); args = parser.parse_args()
    out = (ROOT/args.out).resolve(); out.relative_to(ROOT/'docs/research/WP-0013/eld-mapping-author/005')
    if out.exists(): raise FileExistsError('New retained attempt required')
    if git('status', '--porcelain').strip(): raise RuntimeError('Freeze exact source/helpers before decisive checks')
    verify_frozen_mappers(); head = git('rev-parse', 'HEAD').decode().strip(); started = time.time(); out.mkdir(parents=True)
    suite = unittest.defaultTestLoader.discover(str(HERE/'tests'))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_protocol))
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    test_record = {'source_commit': head, 'tests': tests.testsRun, 'failures': [[str(t), d] for t, d in tests.failures],
                   'errors': [[str(t), d] for t, d in tests.errors], 'skipped': [[str(t), d] for t, d in tests.skipped]}
    write(out/'tests.json', test_record)
    if not tests.wasSuccessful(): return 1
    inputs = {}
    def read(path):
        path = Path(path).as_posix(); data = (ROOT/path).read_bytes()
        inputs[path] = {'path': path, 'bytes': len(data), 'sha256': sha(data), 'git_blob': git('hash-object', '--', path).decode().strip()}
        return data
    def load(path): return json.loads(read(path))
    # Execute the unchanged independent public probe function as an attributed
    # author reproduction. Its original source/pins/results remain untouched.
    review_dir = ROOT/'docs/reviews/WP-0013/eld-mapping-reviewer/protocol-review'
    sys.path.insert(0, str(review_dir))
    spec = importlib.util.spec_from_file_location('wp13_public_review_probes', review_dir/'review_checks.py')
    reviewer = importlib.util.module_from_spec(spec); spec.loader.exec_module(reviewer)
    public_probes = {'executed_by': 'eld-mapping-author', 'helper_origin': 'independent protocol /002', 'status': 'PENDING'}
    reviewer.probes(public_probes); write(out/'reused-public-probes.json', public_probes)
    if public_probes['status'] != 'PASS': raise AssertionError('Unchanged public reference probes failed')
    # Also apply actual v2 to the independent tiny native examples, not just the
    # hand-constructed predictions used to test the original policy interface.
    from public_examples import example
    from qualification.mapping_v2.protocol.scoring import score_policy
    actual_probes = []
    for family in ('WP13-F01', 'WP13-F02', 'WP13-F03', 'WP13-F04'):
        for case in ('supported', 'conflict', 'unsupported'):
            expected, reference, policy, _ = example(case, family)
            comparison = paired(policy['ideal_native'], expected, reference, 'completed')
            ps = score_policy(comparison['predictions']['mapping_v2'], expected, reference, policy)
            if ps['metrics']['required_abstention_violations'] != 0: raise AssertionError('Public negative policy violation')
            if case == 'supported' and ps['metrics']['strict_correct_known_slots'] != ps['metrics']['slots']:
                raise AssertionError('Public supported native example failed')
            actual_probes.append({'fixture_id': policy['fixture_id'], 'raw': policy['ideal_native'], 'comparison': comparison, 'policy_score': ps})
    write(out/'actual-public-native-probes.json', {'executed_by': 'eld-mapping-author', 'examples': actual_probes,
          'limit': 'Independent tiny public examples only; not fresh WP13 corpus or independent implementation acceptance.'})
    p = protocol(); public = git('show', p['public_reservation_commit'] + ':' + p['public_reservation_path'])
    if sha(public) != p['public_reservation_sha256'] or json.loads(public)['fixtures'] != p['fresh_fixtures']:
        raise AssertionError('Public reservation changed')
    manifest = load('evaluation/manifests/corpus-manifest.json'); fixtures = {f['fixture_id']: f for f in manifest['fixtures']}
    previous = load('docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json')
    prior_v1 = {d['fixture_id']: d for d in previous['documents']}; recovery_v1 = previous['supplement_separate'][0]
    documents = []; supplements = []; missing = []
    def keep(group, fid, raw, completion, expected, reference, raw_path, original_scores, old_predictions=None):
        current = paired(raw.decode(), expected, reference, completion)
        for name in ('b0', 'mapping_v1'):
            if current['scores'][name] != original_scores[name]: raise AssertionError('Historical full score changed: ' + fid + '/' + name)
            if old_predictions and current['predictions'][name] != old_predictions[name]: raise AssertionError('Historical prediction changed: ' + fid + '/' + name)
        item = {'fixture_id': fid, 'group': group, 'completion': completion, 'raw_path': raw_path,
                'raw_sha256': sha(raw), 'historical_scores_equal': True, 'scores': current['scores'],
                'v2_prediction': current['predictions']['mapping_v2'],
                'changes_from_b0': change_counts(current['scores'], 'b0'), 'changes_from_v1': change_counts(current['scores'], 'mapping_v1')}
        (supplements if group == 'supplement' else documents).append(item)
    for lane, prefix in OLD.items():
        packet = load(prefix + '/scores.json')
        for old in packet['scores']:
            fid = old['fixture_id']; fx = fixtures[fid]; expected = load(fx['expected_ground_truth_path'])
            parent = next(f for f in fixtures.values() if f['family_id'] == fx['family_id'] and f['variant_kind'] == 'v0_clean')
            read(parent['file_path'])
            if fx['variant_kind'] == 'v3_hybrid': read(fx['source_record_path'])
            reference = reference_for(fx, allow_test=True)
            raw_path = prefix + '/evidence/' + fid + '.measured.raw.txt'
            raw = read(raw_path) if (ROOT/raw_path).exists() else b''
            if not raw: missing.append({'fixture_id': fid, 'path': raw_path, 'completion': old['completion']})
            if raw:
                obs = load(prefix + '/evidence/' + fid + '.measured.observation.json')
                if sha(raw) != obs['raw_output']['sha256_written']: raise AssertionError('Historical raw changed')
            v1 = recovery_v1 if lane == 'supplement' else prior_v1[fid]
            score0 = {k: v for k, v in old.items() if k != 'raw_sha256'}
            score1 = {k: v for k, v in v1['mapping_v1_score'].items() if k != 'raw_sha256'}
            keep('supplement' if lane == 'supplement' else 'wp7_primary', fid, raw, old['completion'], expected, reference, raw_path,
                 {'b0': score0, 'mapping_v1': score1})
    for group, prefix, corpus in [('wp9_exposed', 'docs/evidence/WP-0009/eld-mapping-author/007/attempt-1', 'evaluation/mapping_v1/corpus/r1/'),
                                   ('wp11_exposed', 'docs/evidence/WP-0011/eld-mapping-author/005/attempt-1', 'evaluation/coverage_v1/corpus/r1/')]:
        packet = load(prefix + '/scores.json')
        for old in packet['records']:
            fid = old['fixture_id']; expected = load(corpus + 'expected/' + fid + '.json'); reference = load(corpus + 'reference/' + fid + '.json')
            raw_path = prefix + '/run/evidence/' + fid + '.measured.raw.txt'; raw = read(raw_path)
            if sha(raw) != old['raw_sha256']: raise AssertionError('Exposed raw identity changed')
            keep(group, fid, raw, old['completion'], expected, reference, raw_path, old['scores'], old['predictions'])
    if len(documents) != 42 or len(supplements) != 1: raise AssertionError('Historical denominator changed')
    def summary(rows):
        return {'documents': len(rows), 'completed_documents': sum(r['completion'] == 'completed' for r in rows),
                'changes_from_v1': {metric: {key: sum(r['changes_from_v1'][metric][key] for r in rows)
                    for key in ('total', 'before_correct', 'v2_correct', 'gains', 'losses')}
                    for metric in ('fields', 'cells', 'normalized_fields', 'normalized_cells', 'rows', 'expected_absences')}}
    groups = {group: summary([r for r in documents if r['group'] == group]) for group in ('wp7_primary', 'wp9_exposed', 'wp11_exposed')}
    write(out/'historical-regression.json', {'documents': documents, 'supplement_separate': supplements,
          'groups': groups, 'original_missing_raw': missing,
          'limit': 'Exposed historical regression only; original failed primary retained, recovery separate. No future-content tuning or generalization claim.'})
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.is_file() and path.suffix == '.py': read(path.relative_to(ROOT))
    for path in git('ls-files', 'qualification/mapping_v2', 'docs/research/WP-0013/eld-mapping-author/005').decode().splitlines():
        read(path)
    read('docs/coordination/WP-0007/gpu-reviewer-heldout-release/host-before.json')
    write(out/'inputs.json', {'files': sorted(inputs.values(), key=lambda x: x['path']),
          'public_git_objects': [{'commit': p['public_reservation_commit'], 'path': p['public_reservation_path'], 'bytes': len(public), 'sha256': sha(public)}]})
    record = {'source_commit': head, 'source_tree': git('rev-parse', 'HEAD:qualification/mapping_v2').decode().strip(), 'base': BASE,
              'runtime_protocol_sha256': sha((HERE/'runtime_protocol.json').read_bytes()), 'tests': tests.testsRun,
              'reproduced_independent_public_probes': len(public_probes['checks']), 'actual_public_native_cases': len(actual_probes),
              'historical_groups': groups, 'separate_recovery': summary(supplements), 'original_missing_raw': missing,
              'input_files': len(inputs), 'elapsed_seconds': time.time()-started, 'private_content_access': False,
              'model_import_or_execution': False, 'result': 'PASS'}
    write(out/'summary.json', record)
    print(json.dumps(record, indent=2)); return 0


if __name__ == '__main__': raise SystemExit(main())
