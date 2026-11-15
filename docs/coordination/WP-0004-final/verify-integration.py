"""Compare immutable R&D branch objects with an integration commit; never execute candidate code."""
import argparse
import json
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--seed', required=True)
p.add_argument('--astra', required=True)
p.add_argument('--candidate', required=True)
p.add_argument('--review', required=True)
p.add_argument('--merged', required=True)
a = p.parse_args()

def git(*args):
    return subprocess.check_output(['git', *args]).decode('utf-8')

def tree(rev):
    result = {}
    for record in git('ls-tree', '-r', '-z', rev).split('\0'):
        if not record:
            continue
        meta, path = record.split('\t', 1)
        mode, kind, oid = meta.split(' ')
        result[path] = {'mode': mode, 'kind': kind, 'oid': oid}
    return result

seed, astra, candidate, review, merged = [tree(r) for r in (a.seed, a.astra, a.candidate, a.review, a.merged)]

def delta(base, other):
    return sorted(path for path in base.keys() | other.keys() if base.get(path) != other.get(path))

def compare(label, paths, expected):
    return {'label': label, 'path_count': len(paths),
            'differences': [path for path in paths if expected.get(path) != merged.get(path)],
            'expected_objects': {path: expected.get(path) for path in paths}}

checks = [compare('Astra initial proposal and exchange', delta(seed, astra), astra),
          compare('Final Carbon candidate and prior publications', delta(seed, candidate), candidate),
          compare('Author and independent reviewer publications after candidate', delta(candidate, review), review)]
# All candidate entries must also survive the reviewer publication unchanged.
preserved = [path for path in candidate if candidate[path] != review.get(path)]
accepted_paths = set(delta(seed, astra)) | set(delta(seed, review))
rd_prefixes = ('research/', 'evaluation/generation/', 'evaluation/manifests/', 'evaluation/synthetic/',
               'docs/reviews/WP-0004/', 'docs/agent-reports/eld-rd-')
extra_rd = sorted(path for path in merged if path.startswith(rd_prefixes)
                  and path not in accepted_paths and path not in seed)
passed = not preserved and not extra_rd and all(not c['differences'] for c in checks)
print(json.dumps({'revisions': vars(a), 'checks': checks,
                  'candidate_entries_changed_by_review_publication': preserved,
                  'unexpected_rd_paths': extra_rd, 'all_compared_git_objects_identical': passed,
                  'limits': 'Compares exact Git modes and objects; runtime and visible-page checks remain attributed to the independent reviewer.'}, indent=2))
raise SystemExit(0 if passed else 1)
