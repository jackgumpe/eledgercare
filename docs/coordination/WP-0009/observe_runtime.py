"""Coordinator read-only qualified host/model observations; never grants a lease."""
import argparse
import datetime
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
    boundary = (ROOT / 'docs/coordination/WP-0009').resolve()
    if not target.is_relative_to(boundary) or target.exists():
        raise ValueError('Require a new coordinator observation directory')
    target.mkdir(parents=True)
    q0 = json.loads((ROOT / 'qualification/q0/harness/protocol.json').read_text())
    mapping = json.loads((ROOT / 'qualification/mapping_v1/protocol.json').read_text())
    manifest = load_manifest(ROOT / mapping['model_manifest_path'])
    base = Path(mapping['read_only_q0_root'])
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    model = {'started_utc': started,
             'model': verify_model_dir(base / mapping['model_relative'], manifest),
             'notice': verify_notices(base / mapping['notice_relative'], manifest)}
    (target / 'model.json').write_text(json.dumps(model, indent=2) + '\n', encoding='utf-8')
    host = host_precheck(q0, manifest, stage='during')
    (target / 'host.json').write_text(json.dumps(host, indent=2) + '\n', encoding='utf-8')
    summary = {'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
               'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'host_status': host['status'], 'model_and_notice_verified': True,
               'mapping_free_floor_bytes': mapping['free_floor_bytes'],
               'mapping_free_floor_met': host['free_space']['free_bytes'] >= mapping['free_floor_bytes'],
               'limit': 'Read-only qualified helper reuse. No CUDA context, model inference, ownership grant or other process termination.'}
    (target / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))
    return 0 if host['status'] == 'pass' and summary['mapping_free_floor_met'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
