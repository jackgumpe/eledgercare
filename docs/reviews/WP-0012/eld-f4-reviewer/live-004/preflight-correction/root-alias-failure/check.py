"""Read-only actual host observation, no runtime entry point or model import."""
import datetime, hashlib, importlib.util, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
WORK = ROOT.parent / 'eledgercare-worktrees/eld-f4-reviewer'
SOURCE = '651146fa704fe0df262057540587399277ff6a23'
PREFIX = 'docs/reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/helpers/'
OUT = pathlib.Path(__file__).resolve().parent

def git(*args):
    return subprocess.check_output(['git', '-C', str(WORK), *args])

for name in ['ownership_v6.py', 'run_wp0012_reviewer_rehearsal_v6.py']:
    assert git('show', SOURCE + ':' + PREFIX + name) == (WORK / PREFIX / name).read_bytes()
sys.path.insert(0, str(WORK / PREFIX))
spec = importlib.util.spec_from_file_location('root_v6_probe', WORK / PREFIX / 'run_wp0012_reviewer_rehearsal_v6.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
baseline = json.loads((ROOT / 'docs/coordination/WP-0012/reviewer-004-release/ownership-before.json').read_text(encoding='utf-8'))
baseline['accounted_idle_ollama'] = [{k: row[k] for k in ['ProcessId', 'CreationDate', 'Name', 'ExecutablePath']}
    for row in baseline['candidate_and_gpu_processes'] if row['ProcessId'] == 3892]
assert len(baseline['accounted_idle_ollama']) == 1
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source': SOURCE,
          'root_check_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip(),
          'method': 'Actual read-only v6 observation with explicit CPU-test idle declaration matching root original observed identity; no lease or runtime invocation'}
try:
    snapshot = module.collect_live_ownership_snapshot(WORK)
    (OUT / 'snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
    result['evaluation'] = module.evaluate_gpu_and_model_ownership(snapshot, pre_lease_blobs={'root-original-plus-explicit-idle': baseline})
    result['status'] = 'PASS'
except Exception as exc:
    result.update(status='FAIL', error_type=type(exc).__name__, error=str(exc))
finally:
    (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
raise SystemExit(0 if result['status'] == 'PASS' else 1)
