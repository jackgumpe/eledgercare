"""Inventory public Git bytes and disclose worktree text conversion separately."""
import hashlib, json, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
BASE = '68ed24346039c6b26a8c2010ca0956f958a1e4dc'
def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])
def sha(data):
    return hashlib.sha256(data).hexdigest()
def tree(rev):
    return {line.split('\t', 1)[1]: line.split('\t', 1)[0] for line in git('ls-tree', '-r', rev).decode().splitlines()}
revision = git('rev-parse', 'HEAD').decode().strip()
before, after = tree(BASE), tree(revision)
assert all(after.get(path) == identity for path, identity in before.items())
rows = []
for line in git('diff', '--name-status', BASE, revision).decode().splitlines():
    action, path = line.split('\t')
    assert action == 'A' and path.startswith('docs/reviews/WP-0011/eld-mapping-reviewer/admission/')
    committed, working = git('show', revision + ':' + path), (REPO / path).read_bytes()
    filtered_blob = git('hash-object', '--path=' + path, str(REPO / path)).decode().strip()
    assert filtered_blob == git('rev-parse', revision + ':' + path).decode().strip()
    rows.append({'action': action, 'path': path, 'bytes': len(committed), 'sha256': sha(committed), 'worktree_bytes': len(working), 'worktree_sha256': sha(working), 'git_filter_identity_equal': True})
result = {'schema': 'eld-review-deliverable-inventory/2', 'status': 'PASS', 'base': BASE, 'deliverable': revision, 'hash_authority': 'Committed Git blob bytes; worktree bytes reported separately', 'files': rows, 'file_count': len(rows), 'protected_files_unchanged': len(before), 'private_artifacts_copied_to_public': 0, 'retained_inventory_failures': 1, 'metadata_after_deliverable': ['docs/reviews/WP-0011/eld-mapping-reviewer/admission/public-inventory.json', 'docs/agent-reports/eld-mapping-reviewer/WP-0011/004_2026-11-17_review_eld-mapping-reviewer.md']}
with (HERE / 'public-inventory.json').open('x', encoding='utf-8', newline='\n') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(json.dumps({'status': 'PASS', 'files': len(rows), 'protected': len(before), 'deliverable': revision, 'retained_inventory_failures': 1}))
