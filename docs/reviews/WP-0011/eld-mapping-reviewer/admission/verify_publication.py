"""Publish only count/hash/status evidence from an authorized private admission."""
import hashlib, json, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
PRIVATE = Path('C:/Users/jackg/eLedgerCare-Coverage/WP-0011/admission')
SEALED = PRIVATE.parent / 'sealed'
BASE = '68ed24346039c6b26a8c2010ca0956f958a1e4dc'
def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])
def sha(data):
    return hashlib.sha256(data).hexdigest()
def tree(rev):
    return {line.split('\t', 1)[1]: line.split('\t', 1)[0] for line in git(REPO, 'ls-tree', '-r', rev).decode().splitlines()}
receipt = json.loads((HERE / 'receipt.json').read_text())
assert git(PRIVATE, 'rev-parse', 'HEAD').decode().strip() == receipt['private_evidence']['receipt_commit']
assert not git(PRIVATE, 'status', '--porcelain').strip() and not git(PRIVATE, 'remote').strip()
inv_bytes = (PRIVATE / 'final-inventory.json').read_bytes()
assert sha(inv_bytes) == receipt['private_evidence']['inventory_sha256']
inv = json.loads(inv_bytes)
tracked = set(git(PRIVATE, 'ls-tree', '-r', '--name-only', 'HEAD').decode().splitlines())
assert tracked == {x['path'] for x in inv['files']} | {'final-inventory.json'}
for row in inv['files']:
    data = (PRIVATE / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
    assert data == git(PRIVATE, 'show', inv['evidence_commit'] + ':' + row['path'])
assert git(SEALED, 'rev-parse', 'HEAD').decode().strip() == receipt['inputs']['sealed_receipt']
assert not git(SEALED, 'status', '--porcelain').strip() and not git(SEALED, 'remote').strip()
assert sha((SEALED / 'inventory/sha256-r1.json').read_bytes()) == receipt['inputs']['inventory_sha256']
before, after = tree(BASE), tree('HEAD')
assert all(after.get(path) == identity for path, identity in before.items())
assert all(path.startswith('docs/reviews/WP-0011/eld-mapping-reviewer/admission/') for path in after.keys() - before.keys())
assert not git(REPO, 'diff', '--name-only').strip()
assert git(REPO, 'rev-parse', 'HEAD:qualification/baseline').decode().strip() == 'deae8e826f4770e880374c68e6a56c8c65b6f8a3'
assert git(REPO, 'rev-parse', 'HEAD:qualification/mapping_v1').decode().strip() == '59f66d0d3d9be145a43efcc9258eb260d3ef2f00'
result = {'status': 'PASS', 'base': BASE, 'helper_commit': git(REPO, 'rev-parse', 'HEAD').decode().strip(), 'protected_public_files': len(before), 'private_inventory_entries': len(inv['files']), 'private_tracked_files': len(tracked), 'private_inventory_sha256': sha(inv_bytes), 'private_clean_no_remote': True, 'sealed_clean_no_remote': True, 'baseline_and_mapping_source_unchanged': True}
with (HERE / 'verification-attempt-1.json').open('x', encoding='utf-8', newline='\n') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(json.dumps(result))
