"""Offline inspection of the one completed immutable dev capture, without runtime access."""
from __future__ import annotations
import argparse, collections, json, re, sys
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reproduce import GitBlobs, SOURCE, TREE, git, oid, sha, require

EVIDENCE = '1d6a681f09b0eaf233f838c54465c36a042ec326'
AUTHORITY = '7d8a9d1052caca53312db76aa54b09a6182a9e4a'
PREFIX = 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6/'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    require(oid('HEAD', 'qualification/baseline') == TREE, 'Reviewed source changed')
    read = GitBlobs(EVIDENCE)
    artifact = {path[len(PREFIX):]: read(path) for path in read.files if path.startswith(PREFIX)}
    def obj(name):
        return json.loads(artifact[name])
    capture = obj('capture.json')
    inventory = capture['files']
    require(len({r['relative_path'] for r in inventory}) == len(inventory), 'Duplicate inventory entries')
    require({r['relative_path'] for r in inventory} == set(artifact) - {'capture.json'}, 'Capture inventory incomplete')
    for row in inventory:
        raw = artifact[row['relative_path']]
        require(row['path'] == PREFIX + row['relative_path'], 'Inventory path mismatch')
        require(row['bytes'] == len(raw) and row['sha256'] == sha(raw), 'Inventory bytes differ')
    for path, tree in capture['protected_git_objects'].items():
        require(oid(capture['executing_head'], path) == tree, 'Archived original tree differs: ' + path)
    p = json.loads((ROOT / 'qualification/baseline/protocol.json').read_text())
    manifest = json.loads((ROOT / p['model_manifest_path']).read_text())
    preflight = obj('evidence/preflight.json')
    result = obj('run-result.json')
    load = obj('evidence/load.json')
    require(preflight['release'] == result['release'] and not preflight['release']['allow_test_content'], 'Dev release mismatch')
    model = {r['path']: r for r in preflight['model']['files']}
    require(set(model) == {r['path'] for r in manifest['files']}, 'Model object set differs')
    for expected in manifest['files']:
        observed = model[expected['path']]
        key = 'sha256' if expected['digest_kind'] == 'lfs_sha256' else 'git_blob_sha1'
        require(observed['ok'] and observed['size'] == expected['size'] and observed[key] == expected[key], 'Archived model digest differs')
    for module in load['module_cache']['modules']:
        require(module['identical'] and module['cache_sha256'] == module['model_sha256'] == model[module['file']]['sha256'], 'Archived module cache differs')
    wheels = preflight['wheels']['wheels']
    require(all(w['payload_ok'] and w['metadata']['ok'] and w['metadata']['requires_match'] for w in wheels), 'Archived wheel check failed')
    renderer = preflight['renderer']
    require(renderer['distribution_version'] == p['renderer']['version'] and p['renderer']['pdfium_version'] in renderer['PDFIUM_INFO'], 'Renderer differs')
    fixtures = {f['fixture_id']: f for f in p['fixtures'] if f['split'] == 'dev'}
    renders = []
    observations = []
    for call in result['calls']:
        f = fixtures[call['fixture_id']]
        name = f['fixture_id'] + '.' + call['kind']
        render = obj('evidence/' + name + '.render.json')
        require(render['pdf_sha256'] == f['sha256'], 'Rendered input differs from frozen dev input')
        require([r['page'] for r in render['raster']] == list(range(1, f['page_count'] + 1)), 'Rendered pages reordered/missing')
        require(all(r['width'] > 0 and r['height'] > 0 and re.fullmatch('[0-9a-f]{64}', r['rgb_sha256']) for r in render['raster']), 'Raster record invalid')
        renders.append({'call': name, **render})
        if not call['observation']:
            require(call['status'] == 'failed', 'Unexpected missing completed observation')
            continue
        obs = obj(call['observation'])
        tokens = obj('evidence/' + obs['token_ids_file']['name'])
        positions = [i for i, token in enumerate(tokens) if token == p['call']['page_token_id']]
        require(positions == obs['page_markers']['marker_token_positions'] and len(positions) == f['page_count'], 'Native page marker evidence differs')
        require(obs['native']['prompt'] == '<PAGE><image>' * f['page_count'] + p['call']['prompt'], 'Native prompt differs')
        require(obs['native']['prompt_len'] + 8000 * f['page_count'] <= p['call']['fixed_kwargs']['max_length'], 'Context budget exceeded')
        require(all(t['value'] >= 0 for t in obs['timing'].values()), 'Negative call timing')
        require(not obs['flags'] and not obs.get('error'), 'Completed observation flagged')
        require(all(t['starts'] == 0 for t in obs['targets'].values() if t['role'] in ('forbidden_save_path', 'forbidden_eval_site')), 'Forbidden native site entered')
        observations.append({'call': name, 'status': call['status'], 'excluded': call['excluded'],
            'native': obs['native'], 'timing': obs['timing'], 'cuda_memory': obs['cuda_memory'],
            'host_memory': obs['host_memory'], 'prefill_memory': obs['prefill_memory'],
            'kernel_path': obs['kernel_path'], 'page_markers': obs['page_markers']})
    observer_records = []
    for item in result['observers']:
        name = PureWindowsPath(item['path']).name
        require(item['returncode'] == 0 and item['bytes'] == len(artifact[name]), 'Archived observer failure or missing bytes')
        observer_records.append({**item, 'sha256': sha(artifact[name])})
    events = [json.loads(line) for line in artifact['evidence/events.jsonl'].splitlines()]
    expected_phases = ['preflight', 'load'] + [phase for call in result['calls'] for phase in
        ('render:' + call['fixture_id'], 'call:' + call['fixture_id'] + '.' + call['kind'])]
    require([event['phase'] for event in events] == expected_phases, 'Phase transcript differs')
    heartbeat = obj('heartbeat.json')
    require(heartbeat['phase'] == expected_phases[-1], 'Final heartbeat differs')
    last = result['calls'][-1]
    last_name = last['fixture_id'] + '.' + last['kind']
    require(last['status'] == 'failed' and last['observation'] is None, 'Final failed call misclassified')
    missing = ['evidence/worker-outcome.json'] + ['evidence/' + last_name + suffix for suffix in ('.observation.json', '.raw.txt', '.token_ids.json')]
    require(all(name not in artifact for name in missing), 'Unexpected completed last-call artifact')
    start = obj('author-process-start.json')
    receipt = obj('author-process-exit-and-lease-return.json')
    require(receipt['lease_returned'] and not receipt['observed_owned_processes'], 'Archived author did not return lease')
    require(result['child_launcher_pid'] in [x['ProcessId'] for x in start['processes']], 'Launcher not in archived process chain')
    require(result['observed_child_exit'] and result['child_returncode'] != 0, 'Failed child exit not recorded')
    scores = obj('scores.json')
    failed_score = next(s for s in scores['scores'] if s['fixture_id'] == last['fixture_id'])
    require(not failed_score['eligible_for_exact_credit'] and failed_score['completion'] == 'failed', 'Failed document eligible for credit')
    report = {'authority': AUTHORITY, 'helper_head': git('rev-parse', 'HEAD').decode().strip(),
        'source': SOURCE, 'source_tree': TREE, 'author_evidence': EVIDENCE, 'all_checks_passed': True,
        'inventory_entries_verified': len(inventory), 'published_files_read': len(artifact), 'immutable_artifacts_read': read.reads,
        'preflight': {'model_objects_bound_to_manifest': len(model), 'notice': preflight['notice'], 'installed': preflight['installed'],
            'wheel_records_passed': len(wheels), 'renderer': renderer, 'worker_pid': preflight['worker_pid']},
        'load': load, 'renders': renders, 'observations': observations, 'observer_records': observer_records,
        'phase_events': events, 'last_heartbeat': heartbeat, 'author_exit_receipt': receipt,
        'completion_counts': dict(collections.Counter(c['status'] for c in result['calls'] if not c['excluded'])),
        'excluded_warmups': sum(c['excluded'] for c in result['calls']), 'missing_final_artifacts': missing,
        'failure': result['failure'], 'failed_score': failed_score,
        'stdout_last_300_characters': artifact['stdout.txt'].decode('utf-8', errors='replace')[-300:],
        'stderr': artifact['stderr.txt'].decode('utf-8', errors='replace'),
        'limits': 'Immutable evidence inspection only. Native timings, model/environment checks, render hashes and process records are retained author observations, not fresh measurements. Partial streamed stdout is not completed native output. Original exception has no filename or traceback. Independent GPU sentinels and heldout results remain unreleased.'}
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    print(json.dumps({k: report[k] for k in ('all_checks_passed', 'inventory_entries_verified', 'published_files_read', 'completion_counts')}))

if __name__ == '__main__':
    main()
