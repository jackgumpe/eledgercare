"""Frozen byte-copy and Git inventory only; never repeats CPU or model checks."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = '5cbf8ffe9dc8c5b04d5bc2fff43bb63b4fdad916'
SOURCE = 'ae790497f3fdd10573e8179757416bc2d1736250'
TREE = '8fd68c96bb18ca0177f227ad9a82505090d997b0'
PREFIX = 'docs/research/WP-0013/eld-mapping-author/013/'
ALLOWED = {'qualification/mapping_v2/runtime.py', 'qualification/mapping_v2/runtime_git.py', 'qualification/mapping_v2/tests/test_runtime.py'}
def git(*argv): return subprocess.check_output(['git', *argv], cwd=ROOT)
def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream: json.dump(value, stream, indent=2); stream.write('\n')
def entries(rev):
    result = {}
    for row in git('ls-tree', '-r', '-z', rev).split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1); result[path.decode()] = tuple(meta.decode().split())
    return result
def blobs(ids):
    ids = list(dict.fromkeys(ids))
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], input=('\n'.join(ids)+'\n').encode(), cwd=ROOT)
    stream = io.BytesIO(raw); result = {}
    for expected in ids:
        actual, kind, size = stream.readline().decode().split(); assert actual == expected and kind == 'blob'
        data = stream.read(int(size)); assert stream.read(1) == b'\n'; result[expected] = data
    assert not stream.read(); return result
def capture(out):
    assert not out.exists() and not git('status', '--porcelain').strip()
    assert git('rev-parse', 'HEAD:qualification/mapping_v2').decode().strip() == TREE
    head = git('rev-parse', 'HEAD').decode().strip(); copied = []
    for folder, dest in [('attempt-1', 'attempt-1'), ('capture-attempt-1', 'capture-attempt-1')]:
        origin = ROOT / '.scratch/wp0013-runtime-shadow' / folder
        for path in sorted(origin.rglob('*')):
            assert not path.is_symlink() and not getattr(path.stat(), 'st_file_attributes', 0) & 0x400
            if not path.is_file(): continue
            rel = path.relative_to(origin).as_posix()
            published_rel = rel + '.fixture-bytes' if rel.endswith('/git.exe') else rel
            target = out / dest / published_rel; target.parent.mkdir(parents=True, exist_ok=True)
            data = path.read_bytes()
            with target.open('xb') as stream: stream.write(data)
            assert target.read_bytes() == data
            copied.append({'original': str(path), 'original_relative_path': folder+'/'+rel, 'published_path': target.relative_to(ROOT).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
    tree = entries(SOURCE)
    paths = [p for p in tree if p.startswith(('qualification/', 'evaluation/mapping_v2/', PREFIX))]
    content = blobs(tree[p][2] for p in paths); inputs = []
    for path in paths:
        data = content[tree[path][2]]; local = (ROOT/path).read_bytes()
        inputs.append({'path': path, 'revision': SOURCE, 'git_blob': tree[path][2], 'bytes_git': len(data), 'sha256_git': sha(data), 'bytes_worktree': len(local), 'sha256_worktree': sha(local)})
    authority = '6558c3d7cf12fd336fc277d3406b26ffe125960d'; release_path = 'docs/coordination/WP-0013/releases/author.json'
    original_release = json.loads(git('show', authority+':'+release_path))
    bindings = [{'commit': authority, 'path': release_path},
                {'commit': 'b60624ac7a0ae23540ab019b63d7a7e904fb1c36', 'path': 'qualification/mapping_v2/runtime.py'},
                {'commit': BASE, 'path': 'docs/kickoffs/WP-0013-runtime-correction-013.md'},
                {'commit': '64a456db726080c124e0188e11b3445c02a1d754', 'path': 'docs/reviews/WP-0013/eld-mapping-reviewer/011/findings/F011-01.md'},
                original_release['source_review'], original_release['admission_review'], original_release['unseal'], *original_release['lease']['observations']]
    proof_inputs = []
    for binding in bindings:
        spec = binding['commit']+':'+binding['path']; data = git('show', spec)
        if 'sha256' in binding: assert sha(data) == binding['sha256']
        proof_inputs.append({'revision': binding['commit'], 'path': binding['path'], 'git_blob': git('rev-parse', spec).decode().strip(), 'bytes': len(data), 'sha256': sha(data)})
    result = json.loads((out/'attempt-1/results.json').read_bytes()); assert result['status'] == 'PASS' and result['source'] == SOURCE
    external = []
    for path in sorted({row['arguments'][0] for row in result['cases']} | {row['actual_env']['Q0_GIT_EXECUTABLE'] for row in result['cases']} | {row['result']['python'] for row in result['cases']}):
        data = Path(path).read_bytes(); external.append({'path': path, 'bytes': len(data), 'sha256': sha(data), 'role': 'actual qualified interpreter or explicit Git executable'})
    write(out/'copy-manifest.json', {'helper_commit': head, 'source_commit': SOURCE, 'source_tree': TREE, 'copied_files': copied,
          'input_files': inputs, 'proof_and_original_source_inputs': proof_inputs, 'external_executables': external, 'limits': 'Complete declared source/corpus input trees, not an assertion that every source file was imported. CPU synthetic Git fixtures are copied with .fixture-bytes suffix; original bytes and paths remain recorded.'})
    print(json.dumps({'source': SOURCE, 'copied': len(copied), 'input_tree_files': len(inputs), 'proof_inputs': len(proof_inputs), 'external_executables': len(external)}))
def verify(deliverable, out):
    assert not out.exists() and not git('status', '--porcelain').strip()
    assert git('rev-parse', 'HEAD').decode().strip() == deliverable
    before = entries(BASE); after = entries(deliverable)
    changed = [p for p in after if before.get(p) != after[p]]
    assert set(before) <= set(after)
    assert all(p in ALLOWED or p.startswith(PREFIX) for p in changed)
    assert all(before[p] == after[p] for p in before if p not in ALLOWED)
    content = blobs(after[p][2] for p in changed); rows = []
    for path in sorted(changed):
        data = content[after[path][2]]; local = (ROOT/path).read_bytes()
        if path.startswith(PREFIX+'evidence/'): assert data == local
        rows.append({'path': path, 'action': 'modified' if path in before else 'added', 'git_blob': after[path][2], 'bytes_git': len(data), 'sha256_git': sha(data), 'bytes_worktree': len(local), 'sha256_worktree': sha(local)})
    manifest = json.loads((ROOT/PREFIX/'evidence/copy-manifest.json').read_bytes())
    for row in manifest['copied_files']:
        original = Path(row['original']).read_bytes(); copied = (ROOT/row['published_path']).read_bytes()
        assert original == copied and len(copied) == row['bytes'] and sha(copied) == row['sha256']
    for row in manifest['input_files']:
        local = (ROOT/row['path']).read_bytes(); assert len(local) == row['bytes_worktree'] and sha(local) == row['sha256_worktree']
    for row in manifest['external_executables']:
        data = Path(row['path']).read_bytes(); assert len(data) == row['bytes'] and sha(data) == row['sha256']
    for row in manifest['proof_and_original_source_inputs']:
        data = git('cat-file', 'blob', row['git_blob']); assert len(data) == row['bytes'] and sha(data) == row['sha256']
    write(out, {'base': BASE, 'source': SOURCE, 'source_tree': TREE, 'deliverable': deliverable, 'files': rows, 'changed_files': len(rows),
          'preserved_base_files': len(before)-sum(path in before for path in changed), 'only_two_explicit_existing_paths_modified': True,
          'all_copied_bytes_and_inputs_reverified': True, 'original007_and_all_other_base_objects_unchanged': True})
    print(json.dumps({'changed_files': len(rows), 'preserved_base_files': len(before)-sum(path in before for path in changed), 'copied_originals_verified': len(manifest['copied_files'])}))
if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=('capture', 'verify')); parser.add_argument('--out', required=True); parser.add_argument('--deliverable'); args = parser.parse_args()
    target = (ROOT/args.out).resolve(); target.relative_to(ROOT/PREFIX)
    if args.mode == 'capture': capture(target)
    else: verify(args.deliverable, target)
