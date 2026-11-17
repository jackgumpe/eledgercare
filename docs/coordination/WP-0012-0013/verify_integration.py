"""Coordinator Git preservation audit; no application, renderer or model import."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = '73c8d3c4f0a00312e3444328331b6cbd6406e882'
MUTABLE = {'AGENTS.md', 'CURRENT.md', 'INDEX.md'}
ACCEPTED = {
    'c1fed68020ae67e8b4763bc6ea5473adaa86de2b': ['src', 'web', 'tests', 'deploy', 'workers/local_ocr'],
    'c0a1af638e807803b6014b3a93ecb7f9946ce6e1': ['qualification/mapping_v2'],
    '373106d94b56e619e2210308ca3bf237b45affc0': ['evaluation/mapping_v2'],
}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def revision(value):
    if not re.fullmatch(r'[0-9a-f]{40}', value) or git('rev-parse', value + '^{commit}').decode().strip() != value:
        raise ValueError('Exact full commit required')
    return value

def tree(rev):
    rows = {}
    for entry in git('ls-tree', '-rz', rev).split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        if kind != 'blob':
            raise ValueError('Unexpected tracked non-blob')
        rows[path.decode()] = {'mode': mode, 'blob': oid}
    return rows

def blob_hashes(oids):
    ordered = sorted(set(oids))
    raw = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
                         input=('\n'.join(ordered) + '\n').encode(), capture_output=True, check=True).stdout
    cursor, result = 0, {}
    for wanted in ordered:
        end = raw.index(b'\n', cursor)
        oid, kind, size = raw[cursor:end].decode().split()
        assert oid == wanted and kind == 'blob'
        count = int(size)
        content = raw[end + 1:end + 1 + count]
        assert len(content) == count and raw[end + 1 + count:end + 2 + count] == b'\n'
        result[oid] = {'bytes': count, 'sha256': hashlib.sha256(content).hexdigest()}
        cursor = end + 2 + count
    assert cursor == len(raw)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=revision, required=True)
    parser.add_argument('--publication', type=revision, action='append', default=[])
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    output = (ROOT / args.out).resolve()
    assert output.is_relative_to(Path(__file__).resolve().parent) and not output.exists()
    for rev in [BASE, *ACCEPTED, *args.publication]:
        subprocess.run(['git', 'merge-base', '--is-ancestor', rev, args.candidate], cwd=ROOT, check=True)
    before, after = tree(BASE), tree(args.candidate)
    protected = {k: v for k, v in before.items() if k not in MUTABLE}
    for path, value in protected.items():
        assert after.get(path) == value, 'Protected historical path changed: ' + path
    accepted = {}
    for source, paths in ACCEPTED.items():
        for path in paths:
            expected = git('rev-parse', source + ':' + path).decode().strip()
            actual = git('rev-parse', args.candidate + ':' + path).decode().strip()
            assert actual == expected, 'Accepted tree changed: ' + path
            accepted[path] = {'source': source, 'tree': actual}
    changed = [{'path': path, 'before': before.get(path), 'after': after.get(path),
                'action': 'A' if path not in before else 'D' if path not in after else 'M'}
               for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
    hashes = blob_hashes(row['after']['blob'] for row in changed if row['after'])
    for row in changed:
        if row['after']:
            row.update(hashes[row['after']['blob']])
    result = {'schema': 'eld-wp0012-wp0013-preservation/1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'audit_executing_head': git('rev-parse', 'HEAD').decode().strip(),
              'audit_helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'base': BASE, 'candidate': args.candidate, 'accepted_trees': accepted,
              'publication_ancestry_checked': args.publication, 'protected_base_path_count': len(protected),
              'protected_base_paths': protected, 'complete_changed_path_count': len(changed), 'changed_paths': changed,
              'result': 'PASS', 'limits': 'Git preservation only; exact independent runtime and research reports govern acceptance.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'result': 'PASS', 'protected': len(protected), 'changed': len(changed),
                      'accepted_trees': len(accepted), 'publications': len(args.publication)}))

if __name__ == '__main__':
    main()
