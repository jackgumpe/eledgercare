"""Accounting-only collection of the original failed WP13 author execution.

Adapted from the preserved WP11 /005 collector. No scorer/model/renderer imports,
re-execution, source mutation or omitted-file success inference. Freeze before use.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = 'da6c91e0168f63843bd8d89ecf060834ccd07b9a'
SOURCE = 'c0a1af638e807803b6014b3a93ecb7f9946ce6e1'
TREE = '4477104eb2a3c73f496ef451cef9578f54d96518'
CORPUS = '373106d94b56e619e2210308ca3bf237b45affc0'
CORPUS_TREE = 'af22f632c2b69531f61866ca467c6f04f386df7e'
AUTHORITY = '6558c3d7cf12fd336fc277d3406b26ffe125960d'
RELEASE = 'docs/coordination/WP-0013/releases/author.json'
RUN = Path('C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/author/runs/author/20261117T182439Z-8726c2a5')
SCRATCH = ROOT / '.scratch/wp0013-vocabulary-execution/007-attempt-1'
DOS = 'docs/research/WP-0013/eld-mapping-author/007/'
PACKET = DOS + 'evidence/attempt-1/'
CACHES = {'cuda-cache', 'hf-home', 'hf-modules', 'home', 'inductor-cache', 'tmp', 'torch-home'}
NAMES = ('b0', 'mapping_v1', 'mapping_v2')
METRICS = ('fields', 'cells', 'normalized_fields', 'normalized_cells', 'rows', 'expected_absences', 'page_count')

def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_bytes().decode('utf-8-sig'))
def obj(rev, path): return git('show', rev + ':' + path)
def ident(rev, path): return git('rev-parse', rev + ':' + path).decode().strip()
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False); stream.write('\n')
def entries(rev):
    result = {}
    for row in git('ls-tree', '-r', '-z', rev).split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1); result[path.decode()] = tuple(meta.decode().split())
    return result

def collect(out, return_commit):
    assert not out.exists() and not git('status', '--porcelain').strip(), 'Freeze helper before collection'
    head = git('rev-parse', 'HEAD').decode().strip()
    git('merge-base', '--is-ancestor', BASE, head)
    assert ident('HEAD', 'qualification/mapping_v2') == TREE
    assert ident('HEAD', 'evaluation/mapping_v2') == CORPUS_TREE
    release = json.loads(obj(AUTHORITY, RELEASE)); result = load(RUN / 'run-result.json')
    scores = load(SCRATCH / 'scores.json')
    assert result['release'] == release and result['executing_head'] == BASE
    assert scores['run_result_sha256'] == sha((RUN / 'run-result.json').read_bytes())
    assert load(SCRATCH / 'execute-return.json')['exit_code'] == 1
    assert load(SCRATCH / 'execute-tool.json')['exit_code'] == 1
    assert load(SCRATCH / 'score-execution.json')['exit_code'] == 0
    assert load(SCRATCH / 'score-execution.json')['executing_head'] == BASE
    assert load(SCRATCH / 'score-tool.json')['exit_code'] == 0
    assert not any(x['observed_pid_present'] for x in load(SCRATCH / 'lease-return.json')['checks'])
    assert len(result['calls']) == 14 and all(c['status'] == 'not_run_after_failure' for c in result['calls'])
    assert result['failure'] == 'WORKER_OUTCOME_UNAVAILABLE' and result['child_returncode'] == 1
    assert result['observed_child_exit'] and not result['finalization_errors']
    assert not (RUN / 'evidence/worker-outcome.json').exists()
    assert len(scores['records']) == 12 and all(not r['raw_available'] for r in scores['records'])
    assert [c['fixture_id'] for c in result['calls'] if not c['excluded']] == [r['fixture_id'] for r in scores['records']]
    copied = []; retained = []; manifest = []
    def copy(data, relative, source):
        destination = out / relative; destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream: stream.write(data)
        assert destination.read_bytes() == data
        row = {'source': source, 'destination': destination.relative_to(ROOT).as_posix(), 'bytes': len(data), 'sha256': sha(data)}
        copied.append(row); return row
    for path in sorted(RUN.rglob('*')):
        assert not path.is_symlink() and not getattr(path.stat(), 'st_file_attributes', 0) & 0x400
        if not path.is_file(): continue
        rel = path.relative_to(RUN); data = path.read_bytes()
        row = {'run_relative_path': rel.as_posix(), 'bytes': len(data), 'sha256': sha(data)}
        if rel.parts[0] in CACHES:
            row.update(storage='retained_only_cache', published_path=None); retained.append({'source': str(path), **row})
        else:
            assert len(rel.parts) == 1 or rel.parts[0] == 'evidence', rel
            item = copy(data, 'run/' + rel.as_posix(), str(path)); row.update(storage='published_run_copy', published_path=item['destination'])
        manifest.append(row)
    for path in sorted(SCRATCH.iterdir()):
        assert path.is_file(), path
        copy(path.read_bytes(), 'scores.json' if path.name == 'scores.json' else 'launch/' + path.name, str(path))
    proofs = [{'commit': AUTHORITY, 'path': RELEASE, 'sha256': sha(obj(AUTHORITY, RELEASE))},
              release['source_review'], release['admission_review'], release['unseal'], *release['lease']['observations']]
    return_paths = git('ls-tree', '-r', '--name-only', return_commit, '--', 'docs/coordination/WP-0013/author-after').decode().splitlines()
    assert return_paths, 'Exact root return proof missing'
    proofs += [{'commit': return_commit, 'path': path, 'sha256': sha(obj(return_commit, path))} for path in return_paths]
    for index, proof in enumerate(proofs):
        data = obj(proof['commit'], proof['path']); assert sha(data) == proof['sha256']
        copy(data, f"bindings/{index:02d}-{Path(proof['path']).name}", proof['commit'] + ':' + proof['path'])
    reservation_path = 'docs/evaluation/WP-0013/reservation/reservation.json'
    reservation = json.loads(obj(BASE, reservation_path)); inputs = []
    assert sha(obj(BASE, reservation_path)) == release['reservation_sha256']
    for fx in reservation['fixtures']:
        for artifact in fx['artifacts']:
            data = (ROOT / artifact['path']).read_bytes()
            assert len(data) == artifact['bytes'] and sha(data) == artifact['sha256'] and obj(CORPUS, artifact['path']) == data
            inputs.append({'fixture_id': fx['fixture_id'], **artifact, 'git_blob': ident(CORPUS, artifact['path']), 'actual_inference': False})
    p = load(ROOT / 'qualification/mapping_v2/runtime_protocol.json')
    for fx in p['historical_warmups']:
        data = (ROOT / fx['file_path']).read_bytes()
        assert len(data) == fx['size_bytes'] and sha(data) == fx['sha256']
        inputs.append({'fixture_id': fx['fixture_id'], 'path': fx['file_path'], 'role': 'excluded_warmup_pdf', 'bytes': len(data), 'sha256': sha(data), 'git_blob': ident(BASE, fx['file_path']), 'actual_inference': False})
    totals = {name: {metric: {key: sum(r['scores'][name][metric][key] for r in scores['records']) for key in ('correct', 'total')} for metric in METRICS} for name in NAMES}
    documents = [{'fixture_id': r['fixture_id'], 'completion': r['completion'], 'raw_available': r['raw_available'], 'full_score_pointer': f'/records/{i}',
                  'counts': {name: {m: {k: r['scores'][name][m][k] for k in ('correct', 'total')} for m in METRICS} for name in NAMES},
                  'policy_metrics': {name: r['policy_scores'][name]['metrics'] for name in NAMES}} for i, r in enumerate(scores['records'])]
    pairs = [{'before': a, 'after': b, 'eligible_documents': 0, 'unavailable_documents': 12, 'gains': 0, 'losses': 0, 'neutral_eligible_documents': 0,
              'interpretation': 'No observed outputs; numerical zero differences are not mapping equivalence.'} for a, b in itertools.combinations(NAMES, 2)]
    write(out / 'analysis.json', {'source_commit': SOURCE, 'source_tree': TREE, 'corpus_commit': CORPUS, 'corpus_tree': CORPUS_TREE,
          'executing_head': BASE, 'collection_helper': head, 'runtime_authority': AUTHORITY, 'root_lease_return_commit': return_commit,
          'run': str(RUN), 'calls': result['calls'], 'failure': result['failure'], 'completed_model_calls': 0, 'cold_loads': 0,
          'families': 4, 'documents': documents, 'totals': totals, 'pairwise': pairs,
          'policy_summary': scores['policy_summary'], 'supervisor_elapsed_s': result['elapsed_s'],
          'failure_location': 'worker read_release -> verify_frozen_mappers -> protocol.common.verify_pins -> bare git subprocess: WinError 2',
          'limits': ['All 14 calls not run; no raw, token, render, model-load or worker-outcome evidence exists.',
                     'Legacy zero credits and text error=1 preserve failure accounting, not observed OCR/mapping quality.',
                     'All 255 policy slots and 89 required abstentions unavailable; absence of output is not abstention success.',
                     'Original 12-case/four-family frame remains; a separate recovery needs new root release.',
                     'Shared desktop GPU/WDDM observations are not hardware exclusivity or performance evidence.']})
    write(out / 'run-copy-manifest.json', {'schema': 'eld-mapping-v2-run-copy/1', 'external_run': str(RUN), 'run_prefix': (out / 'run').relative_to(ROOT).as_posix(),
          'entries': manifest, 'total_run_files': len(manifest), 'published_run_files': sum(x['storage'] == 'published_run_copy' for x in manifest),
          'retained_only_files': len(retained), 'note': 'Complete original file population; cache originals retained-only, including empty directory disclosure.'})
    base_entries = entries(BASE)
    source_paths = [path for path in base_entries if path.startswith(('qualification/mapping_v2/', 'qualification/mapping_v1/', 'qualification/coverage_v1/', 'qualification/baseline/', 'qualification/q0/'))]
    write(out / 'source-inventory.json', {'revision': BASE, 'entries': [{'path': path, 'mode': base_entries[path][0], 'type': base_entries[path][1], 'git_blob': base_entries[path][2]} for path in source_paths]})
    write(out / 'collection.json', {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'helper_commit': head, 'executing_head': BASE,
          'runtime_authority': AUTHORITY, 'root_lease_return_commit': return_commit, 'run': str(RUN), 'copied_file_count': len(copied), 'copied_files': copied,
          'retained_only_count': len(retained), 'retained_only_files': retained,
          'cache_directories': [{'name': n, 'exists': (RUN / n).exists(), 'files': sum(x.is_file() for x in (RUN / n).rglob('*'))} for n in sorted(CACHES)],
          'scheduled_input_files': inputs, 'checks': {'original_copy_bytes_equal': True, 'complete_run_manifest': True, 'all_fourteen_not_run_retained': True,
          'all_twelve_unavailable_scores_retained': True, 'actual_execute_failure_and_score_exit_preserved': True}})
    print(json.dumps({'helper': head, 'copied_files': len(copied), 'run_files': len(manifest), 'retained_cache_files': len(retained), 'scheduled_inputs': len(inputs), 'source_paths': len(source_paths), 'completed_calls': 0}, indent=2))

def verify(deliverable, out):
    assert not out.exists() and not git('status', '--porcelain').strip()
    assert git('rev-parse', 'HEAD').decode().strip() == deliverable
    before = entries(BASE); after = entries(deliverable)
    assert all(after.get(path) == value for path, value in before.items()), 'Prior path changed'
    changed = []
    for path in sorted(set(after) - set(before)):
        assert path.startswith(DOS), path
        data = obj(deliverable, path); local = (ROOT / path).read_bytes()
        if path.startswith(PACKET): assert data == local, 'Evidence byte normalization'
        changed.append({'path': path, 'git_blob': after[path][2], 'bytes_git': len(data), 'sha256_git': sha(data), 'bytes_worktree': len(local), 'sha256_worktree': sha(local)})
    collection = load(ROOT / PACKET / 'collection.json')
    for row in collection['copied_files']:
        data = (ROOT / row['destination']).read_bytes(); assert len(data) == row['bytes'] and sha(data) == row['sha256']
        source = row['source']; original = obj(source[:40], source[41:]) if len(source) > 41 and source[40] == ':' else Path(source).read_bytes()
        assert data == original
    for row in collection['retained_only_files']:
        data = Path(row['source']).read_bytes(); assert len(data) == row['bytes'] and sha(data) == row['sha256']
    for row in collection['scheduled_input_files']:
        data = (ROOT / row['path']).read_bytes(); assert len(data) == row['bytes'] and sha(data) == row['sha256']
    manifest = load(ROOT / PACKET / 'run-copy-manifest.json')
    assert {x['run_relative_path'] for x in manifest['entries']} == {x.relative_to(RUN).as_posix() for x in RUN.rglob('*') if x.is_file()}
    write(out, {'base': BASE, 'deliverable': deliverable, 'source': SOURCE, 'source_tree': TREE, 'corpus_commit': CORPUS, 'corpus_tree': CORPUS_TREE,
          'collection_helper': collection['helper_commit'], 'changed_file_count': len(changed), 'changed_files': changed, 'unchanged_base_paths': len(before),
          'all_base_mode_type_blob_identities_unchanged': True, 'all_copied_originals_and_git_bytes_reverified': True,
          'all_retained_cache_and_scheduled_inputs_reverified': True, 'complete_run_manifest_reverified': True})
    print(json.dumps({'deliverable': deliverable, 'added': len(changed), 'preserved': len(before), 'copied_reverified': len(collection['copied_files'])}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=('collect', 'verify')); parser.add_argument('--out', required=True)
    parser.add_argument('--return-authority'); parser.add_argument('--deliverable'); args = parser.parse_args()
    output = (ROOT / args.out).resolve(); output.relative_to(ROOT / DOS)
    if args.mode == 'collect': collect(output, args.return_authority)
    else: verify(args.deliverable, output)
