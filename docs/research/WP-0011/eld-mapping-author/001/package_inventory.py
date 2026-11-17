"""Inventory committed /001 deliverable and prove all authority-base blobs preserved.

Reads Git objects only. Does not open future corpus content or execute source tests.
Freeze this helper with the deliverable before running it; report metadata follows.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = '8d23d755a35be26ff29c319c527bd770abdcae4b'
SOURCE = 'adb51ac317db18950f3f1ef4629864127956eddc'
ALLOWED = ('qualification/coverage_v1/', 'docs/research/WP-0011/eld-mapping-author/')

def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout

def entries(rev):
    result = {}
    for line in git('ls-tree', '-r', '-z', rev).split(b'\0'):
        if line:
            metadata, path = line.split(b'\t', 1)
            mode, kind, blob = metadata.decode().split()
            result[path.decode()] = (mode, kind, blob)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deliverable', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    target = (ROOT / args.out).resolve()
    target.relative_to(ROOT / 'docs/research/WP-0011/eld-mapping-author')
    assert not target.exists(), 'Preserve inventory attempts'
    assert not git('status', '--porcelain').strip(), 'Commit deliverable/helper first'
    assert git('rev-parse', 'HEAD').decode().strip() == args.deliverable
    base, delivered = entries(BASE), entries(args.deliverable)
    assert all(delivered.get(path) == obj for path, obj in base.items()), 'An authority-base path changed'
    added = sorted(set(delivered) - set(base))
    assert all(path.startswith(ALLOWED) for path in added), 'Path outside ownership'
    source_tree = git('rev-parse', SOURCE + ':qualification/coverage_v1').decode().strip()
    assert source_tree == git('rev-parse', args.deliverable + ':qualification/coverage_v1').decode().strip()
    files = []
    for path in added:
        data = git('cat-file', 'blob', delivered[path][2])
        files.append({'action': 'added', 'path': path, 'bytes_git': len(data),
                      'sha256_git': hashlib.sha256(data).hexdigest(), 'git_blob': delivered[path][2]})
    evidence = {'schema': 'eld-coverage-deliverable-inventory/1', 'base_commit': BASE,
                'deliverable_commit': args.deliverable, 'source_commit': SOURCE, 'coverage_tree': source_tree,
                'unchanged_authority_base_paths': len(base), 'changed_existing_paths': 0,
                'added_paths': len(files), 'files': files,
                'evidence_note': 'Git committed bytes; console logs normalize CRLF to LF under existing attributes. Original per-attempt run metadata remains retained.',
                'failure_evidence_commit': git('rev-parse', '69bc9d7').decode().strip(),
                'helper_commit': args.deliverable,
                'future_model_runtime_roots_created': False,
                'fresh_artifact_content_read': False}
    target.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in evidence.items() if k != 'files'}, indent=2))

if __name__ == '__main__':
    main()
