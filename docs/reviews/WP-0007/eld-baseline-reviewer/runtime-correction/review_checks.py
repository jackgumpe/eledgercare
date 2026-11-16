"""Independent CPU review of /009; runtime and release calls are explicit test doubles."""
from __future__ import annotations
import argparse, contextlib, copy, datetime, errno, importlib.abc, io, json, os, stat, subprocess, sys, threading, time, traceback, types, uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
SOURCE = 'f11fcd1141c08d49ac538858354f3b5d87277038'
TREE = '21de152f436f76915855421feae486342860ed92'
AUTHORITY = '4ffc38cf000639a759cd81f8f5afb3f0bfd4b399'
ORIGINAL = 'f807e0ac737df4e9e0aeeb96f716afec57f58ff6'
BLOCKED = ('torch', 'transformers', 'triton', 'q0harness.backend_torch')

class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == x or fullname.startswith(x + '.') for x in BLOCKED):
            raise RuntimeError('CPU-only review refuses ' + fullname)

sys.meta_path.insert(0, NoModelImports())
sys.path[:0] = [str(ROOT / 'qualification/baseline'), str(ROOT / 'qualification/q0/harness')]
import runtime, release, baseline
from q0harness.session import Heartbeat

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def caught(fn):
    try:
        return {'returned': fn(), 'exception': None}
    except Exception as e:
        return {'returned': None, 'exception': {'type': type(e).__name__, 'message': str(e),
            'filename': getattr(e, 'filename', None), 'traceback': traceback.format_exc()}}

def directory_checks(scratch):
    root = scratch / 'directory'; root.mkdir()
    (root / 'nested').mkdir(); (root / 'empty').mkdir()
    (root / 'root.bin').write_bytes(b'abc'); (root / 'nested/child.bin').write_bytes(b'1234567')
    checks = [{'case': 'stable nested full count', 'passed': runtime.directory_size(root) == 10}]
    original_scan = os.scandir
    class Wrapped:
        def __init__(self, entry, action): self.entry, self.action, self.path = entry, action, entry.path
        def stat(self, *, follow_symlinks):
            assert follow_symlinks is False
            if self.action == 'missing_metadata':
                Path(self.path).unlink()
                raise FileNotFoundError(errno.ENOENT, 'enumerated child vanished before metadata', self.path)
            if self.action == 'before': Path(self.path).unlink()
            result = self.entry.stat(follow_symlinks=False)
            if self.action == 'after': Path(self.path).unlink()
            if self.action == 'directory': Path(self.path).rmdir()
            if self.action == 'permission': raise PermissionError(errno.EACCES, 'owned denied child', self.path)
            if self.action == 'reparse': return types.SimpleNamespace(st_mode=result.st_mode, st_size=result.st_size, st_file_attributes=0x400)
            return result
    class Scan:
        def __init__(self, directory, target, action): self.inner = original_scan(directory); self.target = target; self.action = action
        def __enter__(self): return self
        def __exit__(self, *args): self.inner.close()
        def __iter__(self): return self
        def __next__(self):
            entry = next(self.inner)
            return Wrapped(entry, self.action) if Path(entry.path) == self.target else entry
    for action, extra, expected in [('before', 3, (10, 13)), ('missing_metadata', 3, 10), ('after', 3, 13), ('directory', 0, 10), ('permission', 3, None), ('reparse', 3, None)]:
        target = root / ('transient-' + action)
        if action == 'directory': target.mkdir()
        else: target.write_bytes(b'xyz')
        with patch('runtime.os.scandir', side_effect=lambda d: Scan(d, target, action)):
            result = caught(lambda: runtime.directory_size(root))
        expected_error = {'permission': 'PermissionError', 'reparse': 'RuntimeError'}.get(action)
        value_ok = result['returned'] in expected if isinstance(expected, tuple) else result['returned'] == expected
        passed = result['exception']['type'] == expected_error if expected_error and result['exception'] else value_ok and not result['exception']
        checks.append({'case': action, 'passed': passed, **result})
        if target.exists(): target.unlink()
    for case, path, error in [('missing root', root / 'absent', 'FileNotFoundError'), ('file root', root / 'root.bin', 'NotADirectoryError')]:
        result = caught(lambda: runtime.directory_size(path))
        checks.append({'case': case, 'passed': bool(result['exception'] and result['exception']['type'] == error), **result})
    for error in [PermissionError(errno.EACCES, 'root scan denied'), OSError(errno.EIO, 'root scan io'), FileNotFoundError(errno.ENOENT, 'root vanished')]:
        with patch('runtime.os.scandir', side_effect=error): result = caught(lambda: runtime.directory_size(root))
        checks.append({'case': type(error).__name__ + ' root scan', 'passed': bool(result['exception'] and result['exception']['type'] == type(error).__name__), **result})
    return checks

def heartbeat_check(scratch):
    root = scratch / 'heartbeat'; root.mkdir(); (root / 'stable').write_bytes(b'x' * 1000)
    state = {'writes': 0, 'writer_error': None}; stop = threading.Event(); ready = threading.Event()
    heartbeat = Heartbeat(root / 'heartbeat.json', 5, lambda: state['writes'])
    heartbeat.set_phase('independent_cpu_overlap', 30, False)
    def writer():
        try:
            while not stop.is_set(): heartbeat.beat(); state['writes'] += 1; ready.set()
        except BaseException as e: state['writer_error'] = repr(e); ready.set()
    thread = threading.Thread(target=writer, name='reviewer-correction-heartbeat'); thread.start(); ready.wait(2)
    scans = 0; start = time.perf_counter(); failure = None
    try:
        while time.perf_counter() - start < 3:
            if runtime.directory_size(root) < 1000: raise AssertionError('Stable bytes omitted')
            scans += 1
    except Exception as e: failure = repr(e)
    finally: stop.set(); thread.join(5)
    return {'passed': scans > 0 and state['writes'] > 0 and not failure and not state['writer_error'] and not thread.is_alive(),
        **state, 'scans': scans, 'scan_error': failure, 'thread_joined': not thread.is_alive(), 'elapsed_s': time.perf_counter() - start,
        'limit': 'Accelerated real unchanged Q0 heartbeat, no original-cause or original-cadence claim.'}

def supervisor_case(scratch, mode):
    import q0harness.environment as env, q0harness.supervisor as observer, winjob
    case = scratch / ('supervisor-' + mode); case.mkdir(); root = case / 'runtime'
    base = case / 'pinned-stub'; (base / 'venv/Scripts').mkdir(parents=True)
    (base / 'venv/Scripts/python.exe').write_bytes(b'never executed')
    p = release.protocol(); p['read_only_q0_root'] = str(base)
    r = {'runtime_root': str(root), 'gpu_uuid': 'CPU-TEST-DOUBLE'}
    child_env = {k: str(case / 'cache' / k) for k in ['TEMP','TMP','TMPDIR','HF_HOME','HF_MODULES_CACHE','CUDA_CACHE_PATH','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','USERPROFILE']}; child_env['PATH'] = ''
    class Child:
        pid = 999999; returncode = None; kills = 0; waits = 0
        def poll(self): return self.returncode
        def kill(self): self.kills += 1; self.returncode = 1
        def wait(self, timeout): self.waits += 1; return self.returncode
    child = Child(); size_calls = []; observer_calls = []; original_size = runtime.directory_size; original_load = runtime.load_json
    phase = 'call:SYN-MP-01-v2-skew-pos4deg.measured'
    def size(path):
        size_calls.append(str(path))
        if mode == 'persistent_scan' or (len(size_calls) == 1 and mode != 'final_scan'):
            raise PermissionError(errno.EACCES, 'reviewer persistent child metadata failure', str(root / 'denied-child'))
        if mode == 'final_scan':
            if len(size_calls) == 1: child.returncode = 0; return original_size(path)
            raise OSError(errno.EIO, 'reviewer final scan failure', str(root / 'late-child'))
        return original_size(path)
    def load(path):
        if Path(path).name == 'heartbeat.json': return {'phase': phase, 'progress': 1}
        return original_load(path)
    def observations(commands, run, tag):
        observer_calls.append(tag)
        if tag == 'post' and mode == 'post_observer': raise OSError(errno.EIO, 'reviewer post observer failure')
        return []
    with contextlib.ExitStack() as stack:
        for target, value in [('runtime.read_release', lambda *a: r), ('runtime.protocol', lambda: p), ('runtime.git', lambda *a: b'CPU-TEST-DOUBLE'), ('runtime.subprocess.Popen', lambda *a, **k: child), ('runtime.directory_size', size), ('runtime.load_json', load), ('runtime.time.sleep', lambda *a: None)]: stack.enter_context(patch(target, side_effect=value))
        stack.enter_context(patch.object(env, 'build_child_env', return_value=child_env)); stack.enter_context(patch.object(env, 'audit_child_env')); stack.enter_context(patch.object(env, 'resolve_host_git', return_value='git'))
        stack.enter_context(patch.object(observer, 'run_observers', side_effect=observations)); stack.enter_context(patch.object(winjob, 'create', return_value=73)); close = stack.enter_context(patch.object(winjob, 'close'))
        with contextlib.redirect_stdout(io.StringIO()): outcome = caught(lambda: runtime.execute('CPU-TEST-DOUBLE', 'CPU-TEST-DOUBLE', 'dev', 'author'))
    results = list(root.rglob('run-result.json')); result = json.loads(results[0].read_text()) if results else None
    diagnostic = result.get('supervisor_error') if result else None
    persisted = bool(diagnostic and diagnostic.get('traceback') and diagnostic.get('active_phase') == phase)
    return {'case': mode, 'passed': persisted and outcome['exception'] is None, 'result_persisted': bool(result),
        'diagnostic_persisted': persisted, 'outcome': outcome, 'result': result, 'directory_size_calls': len(size_calls),
        'job_close_calls': close.call_args_list.__str__(), 'child_kills': child.kills, 'child_waits': child.waits,
        'child_returncode': child.returncode, 'observers': observer_calls,
        'limit': 'Full supervisor control flow with explicit CPU-only process/observer/release doubles; no runtime authority or process launch.'}

def recovery_checks(scratch):
    p = release.protocol(); binding = copy.deepcopy(release.RECOVERY_BINDING)
    r = {'allow_test_content': False, 'supplemental_recovery': binding}
    release.validate_recovery(r, p, 'dev', 'author')
    plan = release.released_schedule(p, r, 'dev', 'author')
    checks = [{'case': 'actual immutable prior lineage and exact three-call schedule', 'passed': len(plan) == 3 and
        [c['fixture_id'] for c in plan if c['excluded']] == p['warmups'] and [c['fixture_id'] for c in plan if not c['excluded']] == [binding['fixture_id']], 'plan': plan}]
    for key in binding:
        bad = copy.deepcopy(r); bad['supplemental_recovery'].pop(key)
        outcome = caught(lambda: release.validate_recovery(bad, p, 'dev', 'author'))
        checks.append({'case': 'missing binding ' + key, 'passed': bool(outcome['exception'] and outcome['exception']['type'] == 'PermissionError')})
    for field, value in [('fixture_id', 'SYN-WO-01-v0-clean'), ('fixture_id', 'SYN-MP-02-v0-clean'), ('fixture_id', 'unknown'), ('fixture_id', [binding['fixture_id']] * 2), ('prior_evidence_commit', '0' * 40), ('extra', True)]:
        bad = copy.deepcopy(r); bad['supplemental_recovery'][field] = value
        outcome = caught(lambda: release.validate_recovery(bad, p, 'dev', 'author'))
        checks.append({'case': 'invalid binding ' + field + ' ' + str(value), 'passed': bool(outcome['exception'] and outcome['exception']['type'] == 'PermissionError')})
    for split, owner, allowed in [('eval_holdout', 'author', False), ('dev', 'reviewer', False), ('dev', 'author', True)]:
        outcome = caught(lambda: release.validate_recovery({**r, 'allow_test_content': allowed}, p, split, owner))
        checks.append({'case': 'invalid recovery scope ' + split + '/' + owner + '/' + str(allowed), 'passed': bool(outcome['exception'] and outcome['exception']['type'] == 'PermissionError')})
    original = release.git('show', binding['prior_evidence_commit'] + ':' + binding['prior_run_result_path'])
    prior_authority = release.git('show', binding['prior_authority_commit'] + ':' + binding['prior_release_path'])
    with patch('release.git', return_value=original + b' '): outcome = caught(lambda: release.validate_recovery(r, p, 'dev', 'author'))
    checks.append({'case': 'changed actual prior bytes rejected', 'passed': bool(outcome['exception'] and outcome['exception']['type'] == 'PermissionError')})
    for mutation in ('selected_completed', 'extra_record', 'missing_record', 'earlier_failed', 'no_failure'):
        prior = json.loads(original)
        if mutation == 'selected_completed': prior['calls'][-1]['status'] = 'completed'
        if mutation == 'extra_record': prior['calls'].append(copy.deepcopy(prior['calls'][-1]))
        if mutation == 'missing_record': prior['calls'].pop()
        if mutation == 'earlier_failed': prior['calls'][2]['status'] = 'failed'
        if mutation == 'no_failure': prior['failure'] = None
        with patch('release.sha', return_value=binding['prior_run_result_sha256']), patch('release.git', side_effect=[json.dumps(prior).encode(), prior_authority]): outcome = caught(lambda: release.validate_recovery(r, p, 'dev', 'author'))
        checks.append({'case': 'semantic ' + mutation, 'passed': bool(outcome['exception'] and outcome['exception']['type'] == 'PermissionError'), 'limit': 'Hash gate deliberately bypassed only to isolate subsequent semantic refusal.'})
    ordinary = json.loads(prior_authority)
    for split in ('dev', 'eval_holdout'):
        for owner in ('author', 'reviewer'):
            actual = release.released_schedule(p, ordinary, split, owner)
            expected = release.schedule(p, split, ordinary['sentinels'] if owner == 'reviewer' else None)
            checks.append({'case': 'ordinary matrix ' + split + '/' + owner, 'passed': actual == expected})
    outcome = caught(lambda: release.validate_release(ordinary, p, 'dev', 'author', tree=TREE))
    checks.append({'case': 'old /003 route rejected', 'passed': bool(outcome['exception'] and 'Wrong independent review report' in outcome['exception']['message']) and '/010_' in release.REVIEW_PATH})
    run = scratch / 'supplemental-score'; run.mkdir(); (run / 'run-result.json').write_text(json.dumps({'release': r, 'calls': []}), encoding='utf-8')
    with patch('baseline.read_release', return_value=r): baseline.score_run(run, run / 'scores.json', 'CPU-TEST-DOUBLE', 'CPU-TEST-DOUBLE', 'dev', 'author')
    score = json.loads((run / 'scores.json').read_text()); item = score['scores'][0]
    checks.append({'case': 'actual dev expected one-document missing-output denominators', 'passed': len(score['scores']) == 1 and item['fixture_id'] == binding['fixture_id'] and item['fields']['total'] == 15 and item['cells']['total'] == 180 and item['fields']['correct'] == item['cells']['correct'] == 0 and score['summary']['dev']['document_denominator'] == 1 and score['supplemental_recovery'] == binding and score['scope'].startswith('supplemental_single_failed_dev'), 'packet': score})
    return checks

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True); parser.add_argument('--directory-only', action='store_true'); args = parser.parse_args()
    assert git('rev-parse', 'HEAD:qualification/baseline').decode().strip() == TREE
    assert not git('status', '--porcelain').strip(), 'Freeze reviewer helper first'
    scratch = ROOT / '.scratch' / ('review-runtime-correction-' + uuid.uuid4().hex); scratch.mkdir(parents=True)
    report = {'authority': AUTHORITY, 'helper_head': git('rev-parse', 'HEAD').decode().strip(), 'source': SOURCE, 'source_tree': TREE,
        'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'python': sys.version, 'scratch': str(scratch)}
    if args.directory_only:
        report['directory'] = directory_checks(scratch)
        report['limit'] = 'Focused reviewer expectation correction only. Windows DirEntry may retain enumeration metadata after removal; counting that cached snapshot is allowed. A separate missing_metadata injection exercises genuine FileNotFoundError tolerance. Initial results remain immutable.'
        with Path(args.output).open('x', encoding='utf-8', newline='\n') as out: json.dump(report, out, indent=2); out.write('\n')
        print(json.dumps({'directory': all(x['passed'] for x in report['directory']), 'cases': len(report['directory'])}))
        return
    protected = ['qualification/baseline/' + x for x in ['native.py','score.py','typed_values.py','corpus.py','mapping.json','protocol.json','winjob.py']] + ['qualification/q0','evaluation']
    report['protected'] = [{'path': path, 'old': git('rev-parse', ORIGINAL + ':' + path).decode().strip(), 'current': git('rev-parse', 'HEAD:' + path).decode().strip()} for path in protected]
    evidence_path = 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev'
    report['original_raw_tree_unchanged'] = git('rev-parse', '69ee8796b9b86e7c0090ae91d9efc27999088a7a:' + evidence_path) == git('rev-parse', 'HEAD:' + evidence_path)
    report['directory'] = directory_checks(scratch); report['heartbeat'] = heartbeat_check(scratch)
    report['supervisor'] = [supervisor_case(scratch, mode) for mode in ('transient_scan', 'persistent_scan', 'final_scan', 'post_observer')]
    report['recovery'] = recovery_checks(scratch)
    environment = dict(os.environ)
    for key in ('TEMP','TMP','TMPDIR'): environment[key] = str(scratch)
    command = [sys.executable, '-I', '-B', str(ROOT / 'qualification/baseline/tests/test_runtime_correction.py'), '-v']
    cp = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, timeout=60)
    report['author_focused_suite'] = {'command': command, 'exit_code': cp.returncode, 'stdout': cp.stdout.decode(errors='replace'), 'stderr': cp.stderr.decode(errors='replace')}
    report['blocked_modules_loaded'] = [name for name in sys.modules if any(name == x or name.startswith(x + '.') for x in BLOCKED)]
    assert not report['blocked_modules_loaded']
    report['limits'] = 'CPU/dev-only. No model/GPU/heldout/external runtime access. Supervisor process, observers and releases explicitly doubled; existing Windows job primitive is unchanged. No source fixes or score tuning.'
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as out: json.dump(report, out, indent=2); out.write('\n')
    print(json.dumps({'directory': all(x['passed'] for x in report['directory']), 'heartbeat': report['heartbeat']['passed'], 'supervisor': {x['case']: x['passed'] for x in report['supervisor']}, 'recovery': all(x['passed'] for x in report['recovery']), 'author_focused_exit': cp.returncode}))

if __name__ == '__main__': main()
