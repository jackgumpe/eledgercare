"""Frozen post-test accounting and complete Git-object preservation inventory."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OWN = 'docs/research/WP-0013/eld-mapping-author/005/'
BASE = 'ad7309f2079ed11bc4a63e52567e6a1e5fba1868'
SOURCE = 'c0a1af638e807803b6014b3a93ecb7f9946ce6e1'


def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))


def write(path, data):
    with (ROOT/path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')


def analyze(output):
    packet = OWN + 'evidence/attempt-1/historical-regression.json'; data = load(packet)
    records = []
    for ri, row in enumerate(data['documents']):
        decisions = row['v2_prediction'].get('mapping_v2_decisions', [])
        for metric, credit in [('fields', 'credited_exact'), ('expected_absences', 'verified_absent')]:
            before = row['scores']['mapping_v1'][metric]['details']; after = row['scores']['mapping_v2'][metric]['details']
            for index, (a, b) in enumerate(zip(before, after)):
                if not (a[credit] and not b[credit]): continue
                page, fid = a['key'] if metric == 'fields' else (a['page'], a['field_id'])
                relevant = [x for x in decisions if x.get('page') == page and x.get('field_id') == fid]
                if len(relevant) != 1 or relevant[0]['action'] != 'abstain': raise AssertionError('Loss is not a uniquely traced abstention')
                records.append({'fixture_id': row['fixture_id'], 'group': row['group'], 'metric': metric,
                                'page': page, 'field_id': fid, 'before': a, 'after': b, 'decision': relevant[0],
                                'raw_path': row['raw_path'], 'packet': packet,
                                'comparison_pointer': '/documents/' + str(ri) + '/scores/mapping_v2/' + metric + '/details/' + str(index)})
    result = {'source': SOURCE, 'helper_commit': git('rev-parse', 'HEAD').decode().strip(),
              'packet_sha256': sha((ROOT/packet).read_bytes()), 'losses': records,
              'field_reasons': dict(Counter(r['decision']['reason'] for r in records if r['metric'] == 'fields')),
              'absence_reasons': dict(Counter(r['decision']['reason'] for r in records if r['metric'] == 'expected_absences')),
              'interpretation': 'Every lost v1 field/absence credit here is a traced withheld candidate, not a newly wrong assigned value. Exposed regression only.'}
    write(output, result)
    print(json.dumps({k: result[k] for k in ('field_reasons', 'absence_reasons')}))


def tree(commit):
    result = {}
    for row in git('ls-tree', '-rz', commit).split(b'\0'):
        if row:
            identity, path = row.split(b'\t', 1); result[path.decode()] = identity.decode().split()
    return result


def inventory(deliverable, output):
    before = tree(BASE); after = tree(deliverable)
    for path, identity in before.items():
        if after.get(path) != identity: raise AssertionError('Immutable base path changed: ' + path)
    files = []
    for path in sorted(set(after) - set(before)):
        if not path.startswith(('qualification/mapping_v2/', OWN)): raise AssertionError('Unowned addition: ' + path)
        committed = git('show', deliverable + ':' + path); working = (ROOT/path).read_bytes()
        if '/evidence/' in path and committed != working: raise AssertionError('Evidence bytes changed: ' + path)
        files.append({'path': path, 'mode': after[path][0], 'git_blob': after[path][2],
                      'committed_bytes': len(committed), 'committed_sha256': sha(committed),
                      'working_bytes': len(working), 'working_sha256': sha(working)})
    for path in ('qualification/mapping_v2', 'qualification/baseline', 'qualification/mapping_v1', 'qualification/coverage_v1', 'qualification/q0'):
        if git('rev-parse', deliverable + ':' + path) != git('rev-parse', SOURCE + ':' + path):
            raise AssertionError('Tested source tree changed: ' + path)
    inputs = load(OWN + 'evidence/attempt-1/inputs.json')
    for item in inputs['files']:
        if sha((ROOT/item['path']).read_bytes()) != item['sha256']: raise AssertionError('Tested input changed: ' + item['path'])
    for item in inputs['public_git_objects']:
        if sha(git('show', item['commit'] + ':' + item['path'])) != item['sha256']: raise AssertionError('Public reservation changed')
    captures = []
    for name in ('stdout.txt', 'stderr.txt', 'execution.json'):
        original = ROOT/'.scratch/wp0013-implementation/attempt-1'/name
        published = ROOT/OWN/'evidence/attempt-1'/name
        if original.read_bytes() != published.read_bytes(): raise AssertionError('Original capture mismatch')
        captures.append({'original': original.relative_to(ROOT).as_posix(), 'published': published.relative_to(ROOT).as_posix(),
                         'bytes': original.stat().st_size, 'sha256': sha(original.read_bytes())})
    record = {'schema': 'eld-wp13-implementation-inventory/1', 'base': BASE, 'tested_source': SOURCE,
              'deliverable': deliverable, 'helper_commit': git('rev-parse', 'HEAD').decode().strip(),
              'unchanged_base_files': len(before), 'added_files': len(files), 'files': files,
              'tested_inputs_verified': len(inputs['files']), 'public_objects_verified': len(inputs['public_git_objects']),
              'original_capture_copies': captures, 'result': 'PASS'}
    write(output, record)
    print(json.dumps({k: record[k] for k in ('result', 'deliverable', 'unchanged_base_files', 'added_files', 'tested_inputs_verified')}))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=('analyze', 'inventory'))
    parser.add_argument('--deliverable'); parser.add_argument('--output', required=True); args = parser.parse_args()
    if git('status', '--porcelain').strip(): raise RuntimeError('Commit frozen helper and deliverable first')
    (ROOT/args.output).resolve().relative_to(ROOT/OWN)
    if args.phase == 'analyze': analyze(args.output)
    else: inventory(args.deliverable, args.output)


if __name__ == '__main__': main()
