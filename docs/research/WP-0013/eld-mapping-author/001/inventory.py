"""Complete owned-addition inventory and preservation proof using Git objects."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = '47fbc7612e4a08cf1960ad7ac01bd2843ae645e5'
SOURCE = '6207daf1dc9cbdd141d083ca2d8d1e7507c63b09'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def tree(commit):
    result = {}
    for record in git('ls-tree', '-rz', commit).split(b'\0'):
        if not record: continue
        identity, path = record.split(b'\t', 1)
        result[path.decode()] = identity.decode().split()
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--deliverable', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if git('status', '--porcelain').strip(): raise RuntimeError('Inventory requires clean committed deliverable')
    before = tree(BASE); after = tree(args.deliverable)
    for path, identity in before.items():
        if after.get(path) != identity: raise AssertionError('Protected base file changed: ' + path)
    additions = sorted(set(after) - set(before)); entries = []
    for path in additions:
        if not path.startswith(('qualification/mapping_v2/', 'docs/research/WP-0013/eld-mapping-author/001/')):
            raise AssertionError('Unowned addition: ' + path)
        data = git('show', args.deliverable + ':' + path); working = (ROOT / path).read_bytes()
        entry = {'path': path, 'mode': after[path][0], 'type': after[path][1], 'git_blob': after[path][2],
                 'committed_bytes': len(data), 'committed_sha256': digest(data),
                 'working_bytes': len(working), 'working_sha256': digest(working)}
        if '/evidence/' in path and data != working: raise AssertionError('Evidence representation changed: ' + path)
        entries.append(entry)
    for relative in ('qualification/baseline', 'qualification/mapping_v1', 'qualification/coverage_v1', 'qualification/q0', 'qualification/mapping_v2'):
        if git('rev-parse', args.deliverable + ':' + relative) != git('rev-parse', SOURCE + ':' + relative):
            raise AssertionError('Tested source tree changed: ' + relative)
    source_root = ROOT / 'docs/research/WP-0013/eld-mapping-author/001/evidence/attempt-2'
    source_inventory = json.loads((source_root / 'source-inventory.json').read_text())
    for item in source_inventory:
        if digest((ROOT / item['path']).read_bytes()) != item['sha256']: raise AssertionError('Tested helper changed: ' + item['path'])
    inputs = json.loads((source_root / 'inputs.json').read_text())
    for item in inputs:
        if digest((ROOT / item['path']).read_bytes()) != item['sha256']: raise AssertionError('Exposed input changed: ' + item['path'])
    captures = []
    for attempt in ('attempt-1', 'attempt-2'):
        for name in ('execution.json', 'stdout.txt', 'stderr.txt'):
            original = ROOT / '.scratch/wp0013-protocol' / attempt / name
            published = ROOT / 'docs/research/WP-0013/eld-mapping-author/001/evidence' / attempt / name
            if original.read_bytes() != published.read_bytes(): raise AssertionError('Capture copy changed')
            captures.append({'original': original.relative_to(ROOT).as_posix(), 'published': published.relative_to(ROOT).as_posix(),
                             'bytes': original.stat().st_size, 'sha256': digest(original.read_bytes())})
    output = {'schema': 'eld-wp13-protocol-inventory/1', 'base': BASE, 'source': SOURCE,
              'deliverable': args.deliverable, 'helper_commit': git('rev-parse', 'HEAD').decode().strip(),
              'unchanged_base_files': len(before), 'added_files': len(entries), 'files': entries,
              'tested_source_files_verified': len(source_inventory), 'exposed_inputs_verified': len(inputs),
              'original_capture_copies': captures, 'result': 'PASS'}
    with (ROOT / args.output).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(output, stream, indent=2); stream.write('\n')
    print(json.dumps({k: output[k] for k in ('result', 'deliverable', 'unchanged_base_files', 'added_files', 'tested_source_files_verified', 'exposed_inputs_verified')}))


if __name__ == '__main__':
    main()
