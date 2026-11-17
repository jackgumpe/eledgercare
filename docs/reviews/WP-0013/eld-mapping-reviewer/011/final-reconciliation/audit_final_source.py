"""Exact final source delta and affected tests; preserve complete CPU captures."""
import ast,contextlib,datetime,hashlib,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
OLD='c0a1af638e807803b6014b3a93ecb7f9946ce6e1';SOURCE='ae790497f3fdd10573e8179757416bc2d1736250'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def data(rev,path):return git('show',rev+':'+path)
def main():
    assert not git('status','--porcelain').strip()
    assert git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()=='8fd68c96bb18ca0177f227ad9a82505090d997b0'
    out=ROOT/'.scratch/wp0013-reviewer-011-final/source-attempt-1';out.mkdir(parents=True,exist_ok=False)
    changed=git('diff','--name-only',OLD,SOURCE,'--','qualification/').decode().splitlines()
    assert changed==['qualification/mapping_v2/runtime.py','qualification/mapping_v2/runtime_git.py','qualification/mapping_v2/runtime_protocol.json','qualification/mapping_v2/tests/test_runtime.py']
    oldrt=data(OLD,changed[0]).decode();newrt=data(SOURCE,changed[0]).decode()
    block="    q0_imports()\n    from q0harness.environment import audit_child_env\n    audit_child_env(dict(os.environ),root=Path(protocol()['runtime_roots'][owner]),owner=owner,run_dir=Path(run_dir))\n    verify_bare_git_lookup(os.environ)  # Actual worker image/caller cwd, before frozen bare-Git checks.\n"
    assert newrt.count(block)==1
    stripped=newrt.replace(block,'')
    assert stripped.split('\ndef worker(',1)[1]==oldrt.split('\ndef worker(',1)[1]
    oldast=ast.parse(oldrt);newast=ast.parse(stripped)
    newast.body=[n for n in newast.body if not (isinstance(n,ast.FunctionDef) and n.name=='enable_pinned_git_lookup') and not (isinstance(n,ast.ImportFrom) and n.module=='runtime_git')]
    calls=0
    for n in ast.walk(newast):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='enable_pinned_git_lookup':n.func.id='audit_child_env';calls+=1
    assert calls==1 and ast.dump(oldast)==ast.dump(newast)
    a=json.loads(data(OLD,changed[2]));b=json.loads(data(SOURCE,changed[2]))
    assert [k for k in set(a)|set(b) if a.get(k)!=b.get(k)]==['source_review_path']
    assert b['source_review_path']=='docs/agent-reports/eld-mapping-reviewer/WP-0013/011_2026-11-17_review_eld-mapping-reviewer.md'
    assert sha(data(SOURCE,changed[2]))=='ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783'
    protected=['qualification/mapping_v2/protocol','qualification/mapping_v2/mapper.py','qualification/mapping_v2/scoring.py','qualification/mapping_v2/release.py','qualification/baseline','qualification/mapping_v1','qualification/coverage_v1','qualification/q0','evaluation/mapping_v2']
    identities={}
    for path in protected:
        reference='373106d94b56e619e2210308ca3bf237b45affc0' if path=='evaluation/mapping_v2' else OLD
        before=git('rev-parse',reference+':'+path).decode().strip();after=git('rev-parse','HEAD:'+path).decode().strip()
        assert before==after;identities[path]=after
    sys.path[:0]=[str(ROOT),str(ROOT/'qualification/mapping_v2/tests')]
    import test_runtime
    names=['test_runtime_worker_and_model_settings_preserve_accepted_source','test_success_and_failure_retention','test_returned_pre_and_post_observer_failures']
    suite=unittest.TestSuite(test_runtime.RuntimeTests(n) for n in names)
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (out/'unit-stdout.txt').open('x',encoding='utf-8',newline='\n') as stdout,(out/'unit-stderr.txt').open('x',encoding='utf-8',newline='\n') as stderr,contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
        result=unittest.TextTestRunner(stream=stderr,verbosity=2).run(suite)
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','source':SOURCE,'helper_head':git('rev-parse','HEAD').decode().strip(),
        'changed_paths':changed,'runtime_ast_only_bound_changes':True,'worker_body_only_pre_release_gate':True,
        'protocol_changed_keys':['source_review_path'],'protected_identities':identities,'affected_unit_methods':names,
        'tests_run':result.testsRun,'unit_start_utc':start,'unit_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'stdout_sha256':sha((out/'unit-stdout.txt').read_bytes()),'stderr_sha256':sha((out/'unit-stderr.txt').read_bytes()),
        'model_calls':0,'live_observers':0,'limit':'Three affected existing methods rerun; no unrelated full score suite. Final author013 publication audited separately.'}
    with (out/'result.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report));assert result.wasSuccessful()
if __name__=='__main__':main()
