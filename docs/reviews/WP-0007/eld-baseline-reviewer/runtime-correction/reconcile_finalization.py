"""Single /010 reconciliation: exact old R1 probes plus affected finalization boundaries."""
from __future__ import annotations
import argparse, ast, contextlib, datetime, errno, hashlib, io, json, os, subprocess, sys, types, uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_checks as prior  # Preserves the existing probe functions and model import guard.
runtime, release = prior.runtime, prior.release
SOURCE = '522f15f1f6e399c36b9c6c107fc08f51862f1fc1'
TREE = 'deae8e826f4770e880374c68e6a56c8c65b6f8a3'
AUTHORITY = '2c54927463b46a96a9b0c0c5d1012636fb4f961e'
OLD_SOURCE = 'f11fcd1141c08d49ac538858354f3b5d87277038'
OLD_HELPER = '19254515f7ee6b70fa36156a1035c554b6816ec0'

def affected_case(scratch, mode):
    import q0harness.environment as env, q0harness.supervisor as observer, winjob
    case = scratch / mode; case.mkdir(); root = case / 'runtime'; base = case / 'never-executed-base'
    (base / 'venv/Scripts').mkdir(parents=True); (base / 'venv/Scripts/python.exe').write_bytes(b'not executable')
    p = release.protocol(); p['read_only_q0_root'] = str(base)
    r = {'runtime_root': str(root), 'gpu_uuid': 'CPU-ONLY-DOUBLE'}
    plan = release.released_schedule(p, r, 'dev', 'author'); active = plan[-1]['fixture_id'] + '.measured'; phase = 'call:' + active
    child_env = {key: str(case / 'cache' / key) for key in ['TEMP','TMP','TMPDIR','HF_HOME','HF_MODULES_CACHE','CUDA_CACHE_PATH','TORCH_HOME','TORCHINDUCTOR_CACHE_DIR','USERPROFILE']}; child_env['PATH'] = ''
    state = {'post': False, 'closes': 0, 'kills': 0, 'waits': 0}
    interrupted = mode in ('combined', 'cleanup_errors', 'destination_denied')
    class Child:
        pid = 987654; returncode = None
        def poll(self): return self.returncode
        def kill(self):
            state['kills'] += 1
            if mode == 'cleanup_errors': raise PermissionError(errno.EACCES, 'owned child kill denied')
            self.returncode = 1
        def wait(self, timeout):
            state['waits'] += 1
            if mode == 'cleanup_errors': raise subprocess.TimeoutExpired('owned CPU stub', timeout)
            return self.returncode
    child = Child(); original_load = runtime.load_json; original_write = runtime.write; original_size = runtime.directory_size
    def spawn(*args, **kwargs):
        run = next((root / 'runs/author').iterdir()); evidence = run / 'evidence'; evidence.mkdir()
        for call in plan:
            (evidence / (call['fixture_id'] + '.' + call['kind'] + '.observation.json')).write_text(json.dumps({'flags': [], 'error': None}), encoding='utf-8')
        outcome = evidence / 'worker-outcome.json'
        outcome.write_text('{' if mode in ('outcome_invalid_json', 'combined') else '[]' if mode == 'outcome_shape' else json.dumps({'failure': None, 'active_call': active}), encoding='utf-8')
        if mode == 'observation_shape': (evidence / (active + '.observation.json')).write_text('{"flags":"invalid"}', encoding='utf-8')
        return child
    def load(path):
        if Path(path).name == 'heartbeat.json': return {'phase': phase, 'progress': 1}
        if Path(path).name == active + '.observation.json' and mode in ('observation_denied', 'combined'):
            raise PermissionError(errno.EACCES, 'observation unreadable', str(path))
        return original_load(path)
    def size(path):
        if interrupted: raise PermissionError(errno.EACCES, 'primary scan error', str(root / 'denied-child'))
        child.returncode = 0
        return original_size(path)
    def observers(commands, run, tag):
        if tag == 'post':
            state['post'] = True
            if mode == 'combined': raise OSError(errno.EIO, 'post observer error', str(run / 'post.txt'))
        return [{'tag': tag, 'cpu_double': True}]
    def disk(path):
        if state['post'] and mode in ('final_disk', 'combined'): raise OSError(errno.EIO, 'final free-space error', str(path))
        return types.SimpleNamespace(free=p['free_floor_bytes'] + 10**10)
    def close(job):
        state['closes'] += 1
        if mode == 'cleanup_errors': raise OSError(errno.EIO, 'owned job close error')
    def write(path, value):
        if Path(path).name == 'run-result.json' and mode == 'destination_denied': raise PermissionError(errno.EACCES, 'result destination denied', str(path))
        return original_write(path, value)
    with contextlib.ExitStack() as stack:
        for target, action in [('runtime.read_release', lambda *a: r), ('runtime.protocol', lambda: p), ('runtime.git', lambda *a: b'owned-cpu-reconciliation'), ('runtime.subprocess.Popen', spawn), ('runtime.load_json', load), ('runtime.directory_size', size), ('runtime.shutil.disk_usage', disk), ('runtime.write', write), ('runtime.time.sleep', lambda *a: None)]: stack.enter_context(patch(target, side_effect=action))
        stack.enter_context(patch.object(env, 'build_child_env', return_value=child_env)); stack.enter_context(patch.object(env, 'audit_child_env')); stack.enter_context(patch.object(env, 'resolve_host_git', return_value='git'))
        stack.enter_context(patch.object(observer, 'run_observers', side_effect=observers)); stack.enter_context(patch.object(winjob, 'create', return_value=123)); stack.enter_context(patch.object(winjob, 'close', side_effect=close))
        with contextlib.redirect_stdout(io.StringIO()): outcome = prior.caught(lambda: runtime.execute('CPU-DOUBLE', 'CPU-DOUBLE', 'dev', 'author'))
    paths = list(root.rglob('run-result.json')); result = json.loads(paths[0].read_text()) if paths else None
    checks = {'cleanup_attempts': state['closes'] == 1 and state['waits'] == 1 and state['kills'] == int(interrupted)}
    if mode == 'destination_denied':
        checks['explicit_persistence_limit'] = result is None and bool(outcome['exception'] and outcome['exception']['type'] == 'PermissionError')
    else:
        checks['result_saved'] = bool(result) and outcome['exception'] is None
        if result:
            checks['complete_plan'] = [{k: c[k] for k in ('fixture_id','kind','excluded')} for c in result['calls']] == plan
            checks['13_measured'] = sum(not c['excluded'] for c in result['calls']) == 13
            checks['honest_exit'] = outcome['returned'] == (0 if mode == 'normal' else 1)
            primary = result['supervisor_error']; secondary = [e['stage'] for e in result['secondary_errors']]
            if mode == 'normal': checks['normal_success'] = not result['failure'] and primary is None and not secondary and all(c['status'] == 'completed' for c in result['calls'])
            else: checks['structured_failed_result'] = bool(result['failure'] and primary and primary['traceback'] and primary['active_phase'] == phase)
            if interrupted:
                checks['primary_preserved'] = primary['stage'] == 'supervision' and primary['type'] == 'PermissionError' and primary['filename'] == str(root / 'denied-child') and 'primary scan error' in primary['message']
                checks['unavailable_owned'] = result['owned_bytes_after'] is None and result['final_observation_status']['owned_bytes_after'] == 'unavailable'
                checks['active_failed'] = result['calls'][-1]['status'] == 'failed'
            if mode in ('outcome_invalid_json','outcome_shape','combined'): checks['outcome_unavailable'] = result['final_observation_status']['worker_outcome'] == 'unavailable'
            if mode in ('observation_denied','observation_shape','combined'):
                active_result = result['calls'][-1]
                checks['unreadable_record_not_completed'] = active_result['status'] == 'failed' and active_result['observation'] is None and active_result['observation_status'] == 'unavailable'
            if mode in ('final_disk','combined'): checks['unavailable_free'] = result['free_bytes_after'] is None and result['final_observation_status']['free_bytes_after'] == 'unavailable'
            if mode == 'combined':
                checks['all_secondary_preserved'] = secondary == ['post_observers','worker_outcome','call_observation:' + active,'free_bytes_after','owned_bytes_after']
                checks['pre_observer_retained'] = result['observers'] == [{'tag': 'pre', 'cpu_double': True}]
            if mode == 'cleanup_errors':
                checks['cleanup_errors_preserved'] = secondary == ['cleanup_job_close','cleanup_child_kill','cleanup_child_wait','owned_bytes_after']
                checks['no_false_child_exit'] = result['observed_child_exit'] is False and result['child_returncode'] is None
    return {'case': mode, 'passed': all(checks.values()), 'checks': checks, 'outcome': outcome, 'result': result, 'cleanup': state,
        'limit': 'Full execute control flow, explicitly doubled release/process/observer/environment; no model or process launched.'}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True); args = parser.parse_args()
    git = prior.git
    assert git('rev-parse','HEAD:qualification/baseline').decode().strip() == TREE
    assert not git('status','--porcelain').strip(), 'Freeze helper before reconciliation'
    helper_path = 'docs/reviews/WP-0007/eld-baseline-reviewer/runtime-correction/review_checks.py'
    assert git('rev-parse', OLD_HELPER + ':' + helper_path) == git('rev-parse', 'HEAD:' + helper_path)
    scratch = ROOT / '.scratch' / ('finalization-reconcile-' + uuid.uuid4().hex); scratch.mkdir(parents=True)
    report = {'authority': AUTHORITY, 'source': SOURCE, 'source_tree': TREE, 'helper_head': git('rev-parse','HEAD').decode().strip(),
        'prior_probe_freeze': OLD_HELPER, 'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scratch': str(scratch), 'python': sys.version}
    protected = ['qualification/baseline/' + name for name in ['native.py','score.py','typed_values.py','corpus.py','mapping.json','protocol.json','winjob.py','release.py','baseline.py']] + ['qualification/q0','evaluation','docs/evidence/WP-0007/eld-rd-astra/runtime-dev']
    report['protected_objects'] = [{'path': path, 'before': git('rev-parse',OLD_SOURCE+':'+path).decode().strip(), 'after': git('rev-parse','HEAD:'+path).decode().strip()} for path in protected]
    texts = [git('show', rev+':qualification/baseline/runtime.py').decode() for rev in (OLD_SOURCE,SOURCE)]
    functions = []
    for name in ('directory_size','guard_reason','worker','write','q0_imports','supervisor_diagnostic'):
        bodies = [ast.get_source_segment(text, next(node for node in ast.parse(text).body if isinstance(node,ast.FunctionDef) and node.name == name)) for text in texts]
        functions.append({'function': name, 'identical': bodies[0] == bodies[1], 'sha256': hashlib.sha256(bodies[1].encode()).hexdigest()})
    report['unchanged_runtime_functions'] = functions
    report['original_R1_probes'] = [prior.supervisor_case(scratch, mode) for mode in ('transient_scan','persistent_scan','final_scan','post_observer')]
    for case in report['original_R1_probes']:
        result = case['result']
        case['reconciliation_passed'] = bool(case['passed'] and case['outcome']['returned'] == 1 and result['failure'] and len(result['calls']) == 15 and sum(not c['excluded'] for c in result['calls']) == 13)
    report['affected_boundaries'] = [affected_case(scratch, mode) for mode in ('normal','outcome_invalid_json','outcome_shape','observation_denied','observation_shape','final_disk','combined','cleanup_errors','destination_denied')]
    environment = dict(os.environ)
    for key in ('TEMP','TMP','TMPDIR'): environment[key] = str(scratch)
    report['selected_author_tests'] = []
    for name, selectors in [('test_runtime_correction.py',['FinalizationTests']), ('test_baseline.py',['CorpusReleaseTests.test_timeout_stall_storage_log_guard','CorpusReleaseTests.test_worker_job_ownership_kills_only_owned_child'])]:
        command = [sys.executable,'-I','-B',str(ROOT/'qualification/baseline/tests'/name),*selectors,'-v']
        cp = subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,timeout=60)
        report['selected_author_tests'].append({'argv':command,'exit_code':cp.returncode,'stdout':cp.stdout.decode(errors='replace'),'stderr':cp.stderr.decode(errors='replace')})
    report['blocked_modules_loaded'] = [name for name in sys.modules if any(name == x or name.startswith(x+'.') for x in prior.BLOCKED)]
    report['passed'] = (all(x['reconciliation_passed'] for x in report['original_R1_probes']) and all(x['passed'] for x in report['affected_boundaries'])
        and all(x['before'] == x['after'] for x in report['protected_objects']) and all(x['identical'] for x in functions)
        and all(x['exit_code'] == 0 for x in report['selected_author_tests']) and not report['blocked_modules_loaded'])
    report['limits'] = 'Single R1 reconciliation, CPU/dev only. No model/GPU/heldout/external runtime access. Original failing evidence and reviewer expectation correction remain immutable. Result persistence requires a writable destination; no runtime acceptance or new GPU lease is implied.'
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as output: json.dump(report,output,indent=2);output.write('\n')
    print(json.dumps({'passed':report['passed'],'original_R1':{x['case']:x['reconciliation_passed'] for x in report['original_R1_probes']},'affected':{x['case']:x['passed'] for x in report['affected_boundaries']}}))

if __name__ == '__main__': main()
