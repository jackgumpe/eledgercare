"""Metadata-only consolidation of frozen score packets; no model/input re-read or rescoring."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
DEV_COMMIT = '1d6a681f09b0eaf233f838c54465c36a042ec326'
DEV_PATH = 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6'
SUP_COMMIT = '414b24d7a1752698fc9bb3bd95e06715b8ebb677'
SUP_PATH = 'docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca'
SOURCE_TREE = 'deae8e826f4770e880374c68e6a56c8c65b6f8a3'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(name, obj):
    with (HERE / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    assert git('rev-parse', 'HEAD:qualification/baseline').decode().strip() == SOURCE_TREE
    sys.path.insert(0, str(REPO / 'qualification/baseline'))
    from score import summarize
    dev_bytes = git('show', DEV_COMMIT + ':' + DEV_PATH + '/scores.json')
    assert digest(dev_bytes) == '8cc924888baf65ebcb3ee867891402ede6dd0b0224768c6931592a9a3cce710e'
    held_bytes = (HERE / 'scores.json').read_bytes()
    sup_bytes = git('show', SUP_COMMIT + ':' + SUP_PATH + '/scores.json')
    dev, held, sup = [json.loads(x) for x in (dev_bytes, held_bytes, sup_bytes)]
    assert len(dev['scores']) == len(held['scores']) == 13 and len(sup['scores']) == 1
    scores = dev['scores'] + held['scores']
    assert len({s['fixture_id'] for s in scores}) == 26
    summary = summarize(scores)
    assert summary == {**dev['summary'], **held['summary']}
    capture = json.loads((HERE / 'capture.json').read_bytes())
    for entry in capture['copies']:
        data = (REPO / entry['path']).read_bytes()
        assert len(data) == entry['bytes'] and digest(data) == entry['sha256']
    compact = []
    for s in scores:
        compact.append({k: s[k] for k in ['fixture_id', 'family_id', 'split', 'variant_kind', 'completion',
                         'eligible_for_exact_credit', 'parse_errors', 'mapping_coverage', 'reference_coverage', 'text']} |
                       {'metrics': {k: {a: b for a, b in s[k].items() if a not in ('details', 'interpretation')}
                                    for k in ['fields', 'cells', 'normalized_fields', 'normalized_cells', 'rows',
                                              'expected_absences', 'page_count', 'page_sentinels', 'adjacency', 'cross_page_links']}})
    metadata = {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'helper_commit': git('rev-parse', 'HEAD').decode().strip(),
                'helper_sha256': digest(Path(__file__).read_bytes()), 'baseline_tree': SOURCE_TREE,
                'method': 'Unchanged score.summarize on original dev13 plus fixed heldout13; no rescoring or pooled split score. Supplement excluded.',
                'input_packets': {'dev': {'commit': DEV_COMMIT, 'path': DEV_PATH + '/scores.json', 'sha256': digest(dev_bytes)},
                                  'heldout': {'path': str((HERE / 'scores.json').relative_to(REPO)).replace('\\', '/'), 'sha256': digest(held_bytes)},
                                  'supplement_separate': {'commit': SUP_COMMIT, 'path': SUP_PATH + '/scores.json', 'sha256': digest(sup_bytes)}},
                'primary_document_denominator': 26, 'primary_completed_documents': sum(s['completed_documents'] for s in scores),
                'primary_scores': scores, 'summary_by_split': summary,
                'supplement_separate': sup, 'per_document_compact': compact,
                'reference_coverage_status_counts': {status: sum(s['reference_coverage']['status'] == status for s in scores)
                                                    for status in sorted({s['reference_coverage']['status'] for s in scores})}}
    runtime = {}
    for name, base, commit in [('dev_primary', DEV_PATH, DEV_COMMIT), ('heldout_primary', HERE, None), ('supplement_separate', SUP_PATH, SUP_COMMIT)]:
        def read(rel):
            return json.loads(git('show', commit + ':' + base + '/' + rel)) if commit else json.loads((base / rel).read_bytes())
        result = read('run-result.json')
        obs = []
        for call in result['calls']:
            record = dict(call)
            if call.get('observation'):
                o = read(call['observation'].replace('\\', '/'))
                record['observed'] = {k: o.get(k) for k in ['timing', 'native', 'raw_output', 'cuda_memory', 'host_memory', 'kernel_path', 'flags', 'page_count_in']}
            obs.append(record)
        runtime[name] = {'run': result['run'], 'executing_head': result['executing_head'], 'elapsed_s': result['elapsed_s'],
                         'failure': result['failure'], 'child_returncode': result['child_returncode'],
                         'free_bytes_after': result['free_bytes_after'], 'owned_bytes_after': result['owned_bytes_after'],
                         'load': read('evidence/load.json'), 'calls': obs,
                         'interpretation': 'Descriptive individual attempts; warmups excluded; sampled host peaks are lower bounds, lifetime peaks are not per-call. CPU/RAM/WDDM and observer overhead confound timing.'}
    write('primary-results.json', metadata)
    write('runtime-summary.json', runtime)
    print(json.dumps({'primary_denominator': 26, 'primary_completed': metadata['primary_completed_documents'],
                      'copies_verified': len(capture['copies']), 'summary_by_split': summary}, indent=2))


if __name__ == '__main__':
    main()
