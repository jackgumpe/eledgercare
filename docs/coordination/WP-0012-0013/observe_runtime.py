"""Read-only WP-0012/WP-0013 host/model observation; this helper grants no lease.

Adapted only for the new output boundary from the accepted WP-0011 observer.
The immutable coverage_v1 protocol supplies the same qualified Q0 paths and bounds.
This is coordinator observation only; production never imports this helper.
No fresh corpus contents, CUDA context or model inference are accessed.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'qualification/q0/harness'))
from q0harness.hostcheck import host_precheck
from q0harness.modelfiles import load_manifest, verify_model_dir, verify_notices


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    target = (ROOT / args.out).resolve()
    boundary = (ROOT / 'docs/coordination/WP-0012-0013').resolve()
    if not target.is_relative_to(boundary) or target == boundary or target.exists():
        raise ValueError('Require a new coordinator observation directory')
    protocol_path = ROOT / 'qualification/coverage_v1/protocol.json'
    protocol_bytes = protocol_path.read_bytes()
    coverage = json.loads(protocol_bytes)
    q0 = json.loads((ROOT / coverage['q0_protocol_path']).read_text())
    manifest = load_manifest(ROOT / coverage['model_manifest_path'])
    base = Path(coverage['read_only_q0_root'])
    target.mkdir(parents=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    model = {
        'started_utc': started,
        'model': verify_model_dir(base / coverage['model_relative'], manifest),
        'notice': verify_notices(base / coverage['notice_relative'], manifest),
    }
    (target / 'model.json').write_text(json.dumps(model, indent=2) + '\n', encoding='utf-8')
    host = host_precheck(q0, manifest, stage='during')
    (target / 'host.json').write_text(json.dumps(host, indent=2) + '\n', encoding='utf-8')
    summary = {
        'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'coverage_tree': subprocess.check_output(['git', 'rev-parse', 'HEAD:qualification/coverage_v1'], cwd=ROOT).decode().strip(),
        'protocol_sha256': hashlib.sha256(protocol_bytes).hexdigest(),
        'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'host_status': host['status'],
        'model_and_notice_verified': True,
        'coverage_free_floor_bytes': coverage['free_floor_bytes'],
        'coverage_free_floor_met': host['free_space']['free_bytes'] >= coverage['free_floor_bytes'],
        'limit': 'Read-only qualified helper reuse. No corpus contents, CUDA context, inference, ownership grant or other process termination. Root must separately inspect process ownership before granting a sole model-job lease; desktop/WDDM sharing remains.',
    }
    (target / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))
    return 0 if host['status'] == 'pass' and summary['coverage_free_floor_met'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
