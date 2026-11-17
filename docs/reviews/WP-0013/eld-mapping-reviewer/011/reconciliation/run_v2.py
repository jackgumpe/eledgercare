"""Launch real restricted CPU children against original source; preserve all outputs."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'qualification/q0/harness'))
from q0harness.environment import build_child_env, resolve_host_git, audit_child_env
from qualification.mapping_v2.process_identity import process_identity

SOURCE_TREE = '1f48ce375ee15cb5a9fca8a9c873e74f4d0e0b6f'
AUTHORITY = '61f37aa6bd0e67918f2a1225be8028bf8031ce29'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2); f.write('\n')


def main():
    assert len(sys.argv) == 2 and sys.argv[1] == 'corrected-attempt-1'
    assert not git('status', '--porcelain').strip(), 'Freeze helper and retain clean source first'
    assert git('rev-parse', 'HEAD:qualification/mapping_v2').decode().strip() == SOURCE_TREE
    assert git('rev-parse', 'HEAD:evaluation/mapping_v2').decode().strip() == 'af22f632c2b69531f61866ca467c6f04f386df7e'
    head = git('rev-parse', 'HEAD').decode().strip()
    root = ROOT / '.scratch/wp0013-reviewer-011/corrected-attempt-1'
    root.mkdir(parents=True, exist_ok=False)
    p = json.loads((ROOT / 'qualification/mapping_v2/runtime_protocol.json').read_bytes())
    python = Path(p['read_only_q0_root']) / 'venv/Scripts/python.exe'
    original_plan = json.loads(git('show', AUTHORITY + ':docs/coordination/WP-0013/author-failed-after/original-plan.json'))
    fixture = original_plan['release']
    from qualification.mapping_v2.release import schedule
    fixture.update(owner='reviewer', executing_head=head, runtime_root=p['runtime_roots']['reviewer'],
                   schedule=schedule(p, 'reviewer'))
    fixture['source_commit'] = 'b60624ac7a0ae23540ab019b63d7a7e904fb1c36'
    fixture['source_tree'] = SOURCE_TREE
    fixture['protocol_sha256'] = sha((ROOT/'qualification/mapping_v2/runtime_protocol.json').read_bytes())
    fixture['source_review'] = {**fixture['source_review'], 'path': p['source_review_path'], 'reviewed_source_commit': fixture['source_commit']}
    fixture['lease'] = {**fixture['lease'], 'owner': 'reviewer', 'id': 'CPU-ONLY-FIXTURE-NO-RUNTIME-AUTHORITY'}
    inputs = []
    paths = ('qualification/mapping_v2', 'qualification/mapping_v1', 'qualification/baseline',
             'qualification/q0/harness/q0harness/environment.py',
             'qualification/q0/harness/q0harness/outcome.py',
             str(HERE.relative_to(ROOT)).replace('\\', '/'))
    for row in git('ls-tree', '-r', '-z', head, '--', *paths).split(b'\0'):
        if not row: continue
        meta, path = row.split(b'\t', 1); blob = meta.decode().split()[2]; path = path.decode()
        data = git('cat-file', 'blob', blob)
        assert (ROOT/path).read_bytes() == data or (ROOT/path).read_bytes().replace(b'\r\n', b'\n') == data.replace(b'\r\n', b'\n')
        inputs.append({'path': path, 'git_blob': blob, 'bytes_git': len(data), 'sha256_git': sha(data),
                       'bytes_working': (ROOT/path).stat().st_size, 'sha256_working': sha((ROOT/path).read_bytes())})
    write(root/'inputs.json', {'executing_head': head, 'source_tree': SOURCE_TREE, 'inputs': inputs,
        'qualified_python': {'path': str(python), 'bytes': python.stat().st_size, 'sha256': sha(python.read_bytes())},
        'original_root_receipt': {'commit': AUTHORITY, 'path': 'docs/coordination/WP-0013/author-failed-after/original-plan.json',
                                  'sha256': sha(git('show', AUTHORITY + ':docs/coordination/WP-0013/author-failed-after/original-plan.json'))}})
    cases = [('explicit_git_control', 'completed'), ('original_release_pin_boundary', 'FileNotFoundError'),
             ('forbidden_environment', 'Q0Failure'), ('relative_git_binding', 'Q0Failure'),
             ('outside_cache_binding', 'Q0Failure'), ('corrected_pins', 'completed'),
             ('corrected_release_pin_boundary', 'PinBoundaryReached'), ('altered_pin', 'ValueError'),
             ('missing_pin', 'CalledProcessError'), ('missing_git_binding', 'Q0Failure'),
             ('mutable_git_binding', 'Q0Failure'), ('git_configuration', 'Q0Failure')]
    outcomes = []
    for case, expected in cases:
        run = root/'runs/reviewer'/case
        run.mkdir(parents=True, exist_ok=False)
        parent = dict(os.environ)
        parent.update(OPENAI_API_KEY='CPU-ONLY-FAKE-NO-CREDENTIAL', DASH_CPU_CANARY='must-not-inherit',
                      PYTHONPATH='CPU-ONLY-FORBIDDEN')
        env = build_child_env(parent, root=root, owner='reviewer', run_dir=run,
                              gpu_uuid=p['gpu']['uuid'], git_executable=resolve_host_git())
        # Reproduce original runtime's existing-venv and run-local cache wiring exactly.
        base = Path(p['read_only_q0_root'])
        env['VIRTUAL_ENV'] = str(base/'venv'); env['PATH'] = str(base/'venv/Scripts') + os.pathsep + env['PATH']
        for key, suffix in [('HF_HOME','hf-home'), ('HF_HUB_CACHE','hf-home/hub'),
                            ('HUGGINGFACE_HUB_CACHE','hf-home/hub'), ('TRANSFORMERS_CACHE','hf-home/transformers')]:
            env[key] = str(run/suffix)
        audit_child_env(env, root=root, owner='reviewer', run_dir=run)
        assert all(key not in env for key in ('OPENAI_API_KEY', 'DASH_CPU_CANARY', 'PYTHONPATH'))
        if case == 'forbidden_environment': env['OPENAI_API_KEY'] = 'CPU-ONLY-FAKE-NO-CREDENTIAL'
        elif case == 'relative_git_binding': env['Q0_GIT_EXECUTABLE'] = 'git'
        elif case == 'outside_cache_binding': env['HF_HOME'] = str(ROOT/'unused-outside-cache')
        elif case == 'missing_git_binding': del env['Q0_GIT_EXECUTABLE']
        elif case == 'mutable_git_binding':
            fake = run/'fake-git/git.exe'; fake.parent.mkdir(); fake.write_bytes(b'CPU-only invalid executable fixture; never executed')
            env['Q0_GIT_EXECUTABLE'] = str(fake)
        elif case == 'git_configuration': env['GIT_CONFIG_NOSYSTEM'] = '0'
        config = {'case': case, 'expected': expected, 'root': str(root), 'run_dir': str(run),
                  'executing_head': head, 'receipt': str(run/'child-receipt.json'),
                  'fixture_authority': AUTHORITY,
                  'fixture_path': 'docs/coordination/WP-0013/releases/reviewer.json',
                  'cpu_release_fixture': fixture}
        write(run/'config.json', config)
        cmd = [str(python), '-I', '-B', str(HERE/'probe_v2.py'), str(run/'config.json')]
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (run/'stdout.txt').open('xb') as out, (run/'stderr.txt').open('xb') as err:
            proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=out, stderr=err)
            launcher = process_identity(proc.pid)
            try:
                proc.communicate(b'RUN\n', timeout=60)
            except BaseException:
                proc.kill(); proc.wait(timeout=10); raise
        child = json.loads((run/'child-receipt.json').read_bytes())
        row = {'case': case, 'command': cmd, 'start_utc': start,
               'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'launcher_identity': launcher, 'tool_parent_identity': process_identity(os.getpid()),
               'exit_code': proc.returncode, 'expected': expected,
               'expected_outcome_observed': child['expected_outcome_observed'],
               'stdout_sha256': sha((run/'stdout.txt').read_bytes()),
               'stderr_sha256': sha((run/'stderr.txt').read_bytes()),
               'synthetic_fixture_limit': 'Only initial release object substituted; real HEAD/tree/status and pins; deliberate post-pin stop; no proof/fresh-content continuation or runtime authority'}
        write(run/'execution.json', row); outcomes.append(row)
        assert row['expected_outcome_observed'], case
        assert proc.returncode == (0 if expected == 'completed' else 1), case
        assert child['bare_git_on_path'] is None, 'Original restriction not reproduced'
    write(root/'summary.json', {'result': 'PASS', 'helper_head': head, 'source_tree': SOURCE_TREE,
        'original_failure_retained': True, 'groups': len(outcomes), 'cases': outcomes,
        'model_calls': 0, 'live_observers': 0, 'fresh_accesses': 0,
        'corrected_source_acceptance': 'pending evidence reconciliation; narrow real-pin CPU boundary passed'})
    print(json.dumps({'result': 'PASS', 'groups': len(outcomes), 'evidence': str(root),
                      'original_failure_retained': True, 'corrected_candidate_tested': True}))


if __name__ == '__main__':
    main()
