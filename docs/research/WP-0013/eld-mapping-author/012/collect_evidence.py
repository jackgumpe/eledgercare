"""Accounting-only collection of the separately released WP13 recovery012.

Adapted from the preserved WP11 /005 collector. No scorer/model/renderer imports,
re-execution, source mutation or omitted-file success inference. Freeze before use.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import itertools
import json
import statistics
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = 'fbc2ab64e9ae1b4ff6655e427d78e69930d40b72'
SOURCE = 'ae790497f3fdd10573e8179757416bc2d1736250'
TREE = '8fd68c96bb18ca0177f227ad9a82505090d997b0'
CORPUS = '373106d94b56e619e2210308ca3bf237b45affc0'
CORPUS_TREE = 'af22f632c2b69531f61866ca467c6f04f386df7e'
AUTHORITY = '73fbbd7856b61d227b4462c9120ca6d117316a04'
RELEASE = 'docs/coordination/WP-0013/releases/author.json'
RUN = Path('C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/author/runs/author/20261117T192905Z-c72cf92b')
SCRATCH = ROOT / '.scratch/wp0013-vocabulary-execution/012-attempt-1'
DOS = 'docs/research/WP-0013/eld-mapping-author/012/'
PACKET = DOS + 'evidence/attempt-1/'
CACHES = {'cuda-cache', 'hf-home', 'hf-modules', 'home', 'inductor-cache', 'tmp', 'torch-home'}
NAMES = ('b0', 'mapping_v1', 'mapping_v2')
METRICS = ('fields', 'cells', 'normalized_fields', 'normalized_cells', 'rows', 'expected_absences', 'page_count')
ORIGINAL = '0d610695c87f3998deee2b6b3d48f7c7d531eddb'
ORIGINAL_SCORE = 'docs/research/WP-0013/eld-mapping-author/007/evidence/attempt-1/scores.json'

def paired_counts(scores, a, b):
    """Count changed existing per-slot credits; do not redefine a score."""
    output = {}
    for metric in METRICS:
        if metric == 'page_count':
            rows = [(r['fixture_id'], [r['scores'][a][metric]['correct'] > 0], [r['scores'][b][metric]['correct'] > 0], r['raw_available']) for r in scores['records']]
        else:
            key = 'exact' if metric == 'rows' else 'verified_absent' if metric == 'expected_absences' else 'credited_exact'
            rows = [(r['fixture_id'], [bool(d[key]) for d in r['scores'][a][metric]['details']], [bool(d[key]) for d in r['scores'][b][metric]['details']], r['raw_available']) for r in scores['records']]
        totals = Counter(); details = []
        for fixture, before, after, available in rows:
            assert len(before) == len(after)
            counts = Counter()
            for x, y in zip(before, after):
                counts['unavailable' if not available else 'gain' if not x and y else 'loss' if x and not y else 'neutral_correct' if x else 'neutral_uncredited'] += 1
            totals.update(counts); details.append({'fixture_id': fixture, **dict(counts)})
        output[metric] = {'totals': dict(totals), 'documents': details}
    return {'before': a, 'after': b, 'eligible_documents': sum(r['raw_available'] for r in scores['records']),
            'unavailable_documents': sum(not r['raw_available'] for r in scores['records']), 'original_credit_transitions': output,
            'policy_metric_deltas': {k: scores['policy_summary'][b]['all']['metrics'][k] - v for k, v in scores['policy_summary'][a]['all']['metrics'].items()}}

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
    assert load(SCRATCH / 'execute-return.json')['exit_code'] == 0
    assert load(SCRATCH / 'execute-tool.json')['exit_code'] == 0
    assert load(SCRATCH / 'score-execution.json')['exit_code'] == 0
    assert load(SCRATCH / 'score-execution.json')['executing_head'] == BASE
    assert load(SCRATCH / 'score-tool.json')['exit_code'] == 0
    assert not any(x['observed_pid_present'] for x in load(SCRATCH / 'lease-return.json')['checks'])
    assert len(result['calls']) == 14 and all(c['status'] == 'completed' for c in result['calls'])
    assert sum(c['excluded'] for c in result['calls']) == 2
    assert result['failure'] is None and result['child_returncode'] == 0
    assert result['observed_child_exit'] and not result['finalization_errors']
    assert load(RUN / 'evidence/worker-outcome.json')['failure'] is None
    assert len(scores['records']) == 12 and all(r['raw_available'] for r in scores['records'])
    assert all(v == 'available' for v in result['final_observation_status'].values())
    assert all(o['returncode'] == 0 for o in result['observers'])
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
        row = {'run_relative_path': rel.as_posix(), 'bytes': len(data), 'sha256': sha(data), 'original_bytes': len(data), 'original_sha256': sha(data)}
        if rel.parts[0] in CACHES:
            row.update(storage='retained_only_cache', published_path=None); retained.append({'source': str(path), **row})
        else:
            assert len(rel.parts) == 1 or rel.parts[0] == 'evidence', rel
            item = copy(data, 'run/' + rel.as_posix(), str(path)); row.update(storage='published_run_copy', published_path=item['destination'], copy_bytes=item['bytes'], copy_sha256=item['sha256'])
        manifest.append(row)
    for path in sorted(SCRATCH.iterdir()):
        assert path.is_file(), path
        copy(path.read_bytes(), 'scores.json' if path.name == 'scores.json' else 'launch/' + path.name, str(path))
    proofs = [{'commit': AUTHORITY, 'path': RELEASE, 'sha256': sha(obj(AUTHORITY, RELEASE))},
              release['source_review'], release['admission_review'], release['unseal'], *release['lease']['observations']]
    return_paths = git('ls-tree', '-r', '--name-only', return_commit, '--', 'docs/coordination/WP-0013/author-recovery-after').decode().splitlines()
    assert 'docs/coordination/WP-0013/author-recovery-after/lease-return-ack.json' in return_paths, 'Exact root return proof missing'
    proofs += [{'commit': return_commit, 'path': path, 'sha256': sha(obj(return_commit, path))} for path in return_paths]
    for index, proof in enumerate(proofs):
        data = obj(proof['commit'], proof['path']); assert sha(data) == proof['sha256']
        copy(data, f"bindings/{index:02d}-{Path(proof['path']).name}", proof['commit'] + ':' + proof['path'])
    copy(obj(ORIGINAL, ORIGINAL_SCORE), 'original007-scores.json', ORIGINAL + ':' + ORIGINAL_SCORE)
    original_scores = json.loads(obj(ORIGINAL, ORIGINAL_SCORE))
    assert len(original_scores['records']) == 12 and all(not r['raw_available'] for r in original_scores['records'])
    for reference, path, name in [
        (AUTHORITY, 'docs/kickoffs/WP-0013-eld-mapping-author-recovery-012.md', 'recovery-kickoff.md'),
        (git('rev-parse', '76741706').decode().strip(), 'docs/reviews/WP-0013/eld-mapping-reviewer/008/compare_published_recovery012.py', 'preoutput-independent-comparison.py')]:
        copy(obj(reference, path), 'bindings/' + name, reference + ':' + path)
    reservation_path = 'docs/evaluation/WP-0013/reservation/reservation.json'
    reservation = json.loads(obj(BASE, reservation_path)); inputs = []
    assert sha(obj(BASE, reservation_path)) == release['reservation_sha256']
    for fx in reservation['fixtures']:
        for artifact in fx['artifacts']:
            data = (ROOT / artifact['path']).read_bytes()
            assert len(data) == artifact['bytes'] and sha(data) == artifact['sha256'] and obj(CORPUS, artifact['path']) == data
            inputs.append({'fixture_id': fx['fixture_id'], **artifact, 'git_blob': ident(CORPUS, artifact['path']), 'actual_model_input': artifact['role'] == 'pdf', 'scoring_only': artifact['role'] != 'pdf'})
    p = load(ROOT / 'qualification/mapping_v2/runtime_protocol.json')
    for fx in p['historical_warmups']:
        data = (ROOT / fx['file_path']).read_bytes()
        assert len(data) == fx['size_bytes'] and sha(data) == fx['sha256']
        inputs.append({'fixture_id': fx['fixture_id'], 'path': fx['file_path'], 'role': 'excluded_warmup_pdf', 'bytes': len(data), 'sha256': sha(data), 'git_blob': ident(BASE, fx['file_path']), 'actual_model_input': True})
    observations = []
    for call in result['calls']:
        obs = load(RUN / call['observation'])
        render = load(RUN / 'evidence' / f"{call['fixture_id']}.{call['kind']}.render.json")
        for key in ('raw_output', 'token_ids_file'):
            data = (RUN / 'evidence' / obs[key]['name']).read_bytes()
            assert len(data) == obs[key]['bytes_written'] == obs[key]['full_bytes']
            assert sha(data) == obs[key]['sha256_written'] == obs[key]['full_sha256']
            assert obs[key]['truncated_by_writer'] is False
        tokens = load(RUN / 'evidence' / obs['token_ids_file']['name'])
        assert sha(json.dumps(tokens).encode()) == obs['native']['token_ids_sha256']
        assert obs['raw_output']['full_sha256'] == obs['native']['text_sha256']
        assert not obs['flags'] and not obs.get('error') and obs['native']['finish_reason'] == 'stop'
        assert len(render['raster']) == obs['page_count_in'] == obs['native']['num_pages_out']
        pdf = next(x for x in inputs if x['fixture_id'] == call['fixture_id'] and x['actual_model_input'])
        assert render['pdf_sha256'] == pdf['sha256']
        observations.append({**call, 'native': obs['native'], 'timing': obs['timing'], 'host_memory': obs['host_memory'],
                             'cuda_memory': obs['cuda_memory'], 'kernel_path': obs['kernel_path'], 'render': render,
                             'flags': obs['flags'], 'raw': obs['raw_output'], 'tokens': obs['token_ids_file']})
    totals = {name: {metric: {key: sum(r['scores'][name][metric][key] for r in scores['records']) for key in ('correct', 'total')} for metric in METRICS} for name in NAMES}
    documents = [{'fixture_id': r['fixture_id'], 'completion': r['completion'], 'raw_available': r['raw_available'], 'full_score_pointer': f'/records/{i}',
                  'counts': {name: {m: {k: r['scores'][name][m][k] for k in ('correct', 'total')} for m in METRICS} for name in NAMES},
                  'policy_metrics': {name: r['policy_scores'][name]['metrics'] for name in NAMES}} for i, r in enumerate(scores['records'])]
    pairs = [paired_counts(scores, a, b) for a, b in itertools.combinations(NAMES, 2)]
    runtime_summary = {}
    for label, excluded in (('warmups_excluded', True), ('primaries', False)):
        group = [o for o in observations if o['excluded'] == excluded]
        seconds = [o['timing']['external_synchronized_wall_s']['value'] for o in group]
        runtime_summary[label] = {'calls': len(group), 'wall_seconds': {'sum': sum(seconds), 'min': min(seconds), 'max': max(seconds), 'mean': statistics.mean(seconds)},
            'cuda_max_allocated_bytes': max(o['cuda_memory']['max_allocated'] for o in group),
            'cuda_max_reserved_bytes': max(o['cuda_memory']['max_reserved'] for o in group),
            'host_sampled_peak_private_bytes_lower_bound': max(o['host_memory']['window_peak_private_bytes_lower_bound'] for o in group),
            'host_sampled_peak_working_set_lower_bound': max(o['host_memory']['window_peak_working_set_lower_bound'] for o in group),
            'kernel_path_labels': dict(Counter(o['kernel_path']['label'] for o in group))}
    write(out / 'analysis.json', {'source_commit': SOURCE, 'source_tree': TREE, 'corpus_commit': CORPUS, 'corpus_tree': CORPUS_TREE,
          'executing_head': BASE, 'collection_helper': head, 'runtime_authority': AUTHORITY, 'root_lease_return_commit': return_commit,
          'run': str(RUN), 'calls': observations, 'failure': result['failure'], 'completed_model_calls': 14, 'cold_loads': 1,
          'families': 4, 'documents': documents, 'totals': totals, 'pairwise': pairs,
          'historical_summary': scores['historical_summary'], 'policy_summary': scores['policy_summary'],
          'supervisor_elapsed_s': result['elapsed_s'], 'load': load(RUN / 'evidence/load.json'), 'runtime_summary': runtime_summary,
          'child_returncode': result['child_returncode'], 'observed_child_exit': result['observed_child_exit'],
          'final_observation_status': result['final_observation_status'], 'observer_returncodes': [o['returncode'] for o in result['observers']],
          'original007': {'publication': ORIGINAL, 'primary_documents': 12, 'available': 0, 'unavailable': 12, 'separate_score_copy': 'original007-scores.json'},
          'limits': ['This separately authorized recovery does not replace original007: all12 original primaries remain unavailable.',
                     'Four families and12 one-page cases, already exposed at recovery; not a newly blind sample or broad generalization estimate.',
                     'All255 policy slots eligible;252 known,3 ambiguous,0 unknown. Required abstention is not a correct known-value assignment.',
                     'Original row credit is agreement on declared known cells; raw extra_cells is not invention proof for unjudged cells.',
                     'Typed quantity normalization retains historical numeric-magnitude semantics; not separate unit or identifier semantic accuracy.',
                     'No actual-output tuning; all paired gains and losses are retained, including the deliberately suppressed v1 known assignment.',
                     'Text-edit metrics on the bounded reference are not comprehensive OCR character accuracy.',
                     'Shared desktop GPU/WDDM use, fixed order, one load and observer overhead confound performance; no hardware exclusivity.',
                     'Observed kernel label triton_import_failed_dense_fallback is retained; exact internal GPU kernels unobserved.',
                     'Host sampling peaks are lower bounds; no profiler, throughput benchmark, customer-data claim or product promotion.']})
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
          'scheduled_input_files': inputs, 'checks': {'original_copy_bytes_equal': True, 'complete_run_manifest': True, 'all_fourteen_calls_retained': True,
          'all_twelve_primary_scores_retained': True, 'raw_token_render_bindings': True, 'original007_unavailable_retained_separately': True,
          'actual_execute_and_score_exits_preserved': True}})
    print(json.dumps({'helper': head, 'copied_files': len(copied), 'run_files': len(manifest), 'retained_cache_files': len(retained), 'scheduled_inputs': len(inputs), 'source_paths': len(source_paths), 'completed_calls': 14, 'totals': totals}, indent=2))

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
        assert row['destination'] in after, 'Copied evidence absent from Git'
        data = (ROOT / row['destination']).read_bytes(); assert len(data) == row['bytes'] and sha(data) == row['sha256']
        assert obj(deliverable, row['destination']) == data, 'Copied Git evidence differs'
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
