"""Frozen CPU-only real-child regression, source audit and existing unit suite."""
import argparse
import datetime
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
BASE = '86fe8420ecd4fa57d800ce51f6411627ecd71d05'
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'qualification/q0/harness'))
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'transformers', 'triton', 'pypdfium2', 'PIL') or fullname == 'q0harness.backend_torch':
            raise RuntimeError('CPU check forbids model/renderer import: ' + fullname)
sys.meta_path.insert(0, NoModel())
from qualification.mapping_v2 import runtime
from qualification.mapping_v2.common import git, protocol, verify_frozen_mappers
from qualification.mapping_v2.process_identity import process_identity
from q0harness.environment import build_child_env, resolve_host_git, audit_child_env

def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream: json.dump(value, stream, indent=2); stream.write('\n')

def main(out):
    assert not out.exists() and not git('status', '--porcelain').strip(), 'Freeze source and retain each attempt'
    head = git('rev-parse', 'HEAD').decode().strip(); out.mkdir(parents=True)
    verify_frozen_mappers(); p = protocol()
    old = json.loads(git('show', BASE + ':qualification/mapping_v2/runtime_protocol.json'))
    changes = {key for key in set(old) | set(p) if old.get(key) != p.get(key)}
    assert changes == {'source_review_path'}
    assert p['source_review_path'] == 'docs/agent-reports/eld-mapping-reviewer/WP-0013/011_2026-11-17_review_eld-mapping-reviewer.md'
    changed_paths = git('diff', '--name-only', BASE, head).decode().splitlines()
    permitted = {'qualification/mapping_v2/runtime.py', 'qualification/mapping_v2/runtime_protocol.json', 'qualification/mapping_v2/tests/test_runtime.py'}
    assert all(path in permitted or path.startswith('docs/research/WP-0013/eld-mapping-author/010/') for path in changed_paths)
    original_runtime = git('show', BASE + ':qualification/mapping_v2/runtime.py').decode().replace('\r\n', '\n')
    current_runtime = (ROOT / 'qualification/mapping_v2/runtime.py').read_text()
    assert original_runtime.split('\ndef worker(', 1)[1] == current_runtime.split('\ndef worker(', 1)[1]
    audit = {'base': BASE, 'source': head, 'source_tree': git('rev-parse', 'HEAD:qualification/mapping_v2').decode().strip(),
             'runtime_protocol_sha256': sha((ROOT / 'qualification/mapping_v2/runtime_protocol.json').read_bytes()),
             'changed_paths': changed_paths, 'protocol_changed_keys': sorted(changes), 'worker_body_unchanged': True,
             'preserved': {path: git('rev-parse', 'HEAD:' + path).decode().strip() for path in ('qualification/mapping_v2/protocol', 'qualification/mapping_v2/mapper.py', 'qualification/mapping_v2/scoring.py', 'qualification/mapping_v2/release.py', 'qualification/baseline', 'qualification/mapping_v1', 'qualification/coverage_v1', 'qualification/q0', 'evaluation/mapping_v2')}}
    for path, value in audit['preserved'].items(): assert value == git('rev-parse', BASE + ':' + path).decode().strip()
    write(out / 'source-audit.json', audit)
    cases = [('original', 1, 'FileNotFoundError'), ('corrected_pins', 0, None), ('full_release', 0, None),
             ('altered_pin', 1, 'ValueError'), ('missing_pin', 1, 'CalledProcessError'), ('missing_git', 1, 'Q0Failure'),
             ('relative_git', 1, 'Q0Failure'), ('missing_binary', 1, 'Q0Failure'), ('mutable_git', 1, 'Q0Failure'),
             ('forbidden_env', 1, 'Q0Failure'), ('git_config', 1, 'Q0Failure'), ('stale_actual_release', 1, 'PermissionError'),
             ('release_source', 1, 'PermissionError'), ('release_schedule', 1, 'PermissionError'),
             ('release_digest', 1, 'PermissionError'), ('release_lease', 1, 'PermissionError')]
    restricted_root = out / 'owned-runtime'; python = Path(p['read_only_q0_root']) / 'venv/Scripts/python.exe'
    assert python.is_file()
    child_rows = []
    for case, expected_exit, expected_error in cases:
        run = restricted_root / 'runs/author' / case; run.mkdir(parents=True)
        env = build_child_env(dict(os.environ), root=restricted_root, owner='author', run_dir=run, gpu_uuid=p['gpu']['uuid'], git_executable=resolve_host_git())
        env['VIRTUAL_ENV'] = str(python.parents[1]); env['PATH'] = str(python.parent) + os.pathsep + env['PATH']
        original_env = dict(env)
        if case not in ('original', 'missing_git', 'relative_git', 'missing_binary', 'mutable_git', 'forbidden_env', 'git_config'):
            runtime.enable_pinned_git_lookup(env, root=restricted_root, owner='author', run_dir=run)
            assert {key for key in env if env[key] != original_env[key]} == {'PATH'}
            assert env['PATH'] == original_env['PATH'] + os.pathsep + str(Path(env['Q0_GIT_EXECUTABLE']).parent)
        audit_child_env(env, root=restricted_root, owner='author', run_dir=run)
        argv = [str(python), '-I', '-B', str(HERE / 'restricted_probe.py'), '--case', case, '--root', str(restricted_root), '--run', str(run), '--out', str(run / 'probe.json')]
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (run / 'stdout.txt').open('xb') as stdout, (run / 'stderr.txt').open('xb') as stderr:
            proc = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
            launcher = process_identity(proc.pid); code = proc.wait(timeout=60)
        result = json.loads((run / 'probe.json').read_bytes())
        row = {'case': case, 'arguments': argv, 'started_utc': started, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'launcher_identity': launcher, 'exit_code': code, 'expected_exit': expected_exit, 'expected_error': expected_error,
               'original_env': original_env, 'actual_env': env, 'result': result}
        child_rows.append(row); write(run / 'execution.json', row)
        assert code == expected_exit and result.get('error_type') == expected_error, case
        assert not result['prohibited_imports_present'], case
        if case == 'full_release': assert result['actual_contracts_validated'] == 12 and result['actual_families_validated'] == 4
        print(json.dumps({'case': case, 'exit': code, 'expected_error': expected_error, 'worker_pid': result['identity']['pid']}), flush=True)
    # Existing public/synthetic tests; no fresh corpus scoring or historical rerun.
    from qualification.mapping_v2.protocol.tests import test_protocol
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'qualification/mapping_v2/tests'))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(test_protocol))
    with (out / 'unit-tests.txt').open('x', encoding='utf-8', newline='\n') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    test_record = {'tests': result.testsRun, 'failures': [[str(t), d] for t, d in result.failures], 'errors': [[str(t), d] for t, d in result.errors], 'skipped': [[str(t), d] for t, d in result.skipped]}
    write(out / 'unit-tests.json', test_record)
    assert result.wasSuccessful(), 'Existing CPU unit suite failed'
    assert not git('status', '--porcelain').strip(), 'Test changed tracked or unignored state'
    write(out / 'results.json', {'status': 'PASS', 'source': head, 'restricted_children': len(cases), 'cases': child_rows, 'unit_tests': test_record,
        'no_model_renderer_imports': True, 'no_live_observers': True, 'synthetic_release_limit': 'Only three test-only Git-object reads overlaid; no independent acceptance, unseal or runtime authorization inferred. Actual pins/trees/cleanHEAD/contracts/known proof objects are not bypassed.'})
    print(json.dumps({'status': 'PASS', 'source': head, 'real_restricted_children': len(cases), 'unit_tests': result.testsRun}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True); args = parser.parse_args()
    output = (ROOT / args.out).resolve(); output.relative_to(ROOT / '.scratch/wp0013-runtime-correction')
    main(output)
