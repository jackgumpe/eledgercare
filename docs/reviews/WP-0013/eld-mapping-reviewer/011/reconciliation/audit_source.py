"""Independent exact correction scope, publication and affected CPU test audit."""
import ast,hashlib,json,subprocess,sys,unittest,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
OUT=ROOT/'.scratch/wp0013-reviewer-011/corrected-attempt-1'
SOURCE='b60624ac7a0ae23540ab019b63d7a7e904fb1c36'
OLD='c0a1af638e807803b6014b3a93ecb7f9946ce6e1'
PUB='bd59cb57ad8f621ec98762b8bfdd76b3eee26e6f'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def tree(rev):
    out={}
    for row in git('ls-tree','-r','-z',rev).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);out[path.decode()]=meta.decode()
    return out
def blob(rev,path):return git('cat-file','blob',tree_cache.setdefault(rev,tree(rev))[path].split()[2])
tree_cache={}
def main():
    assert OUT.is_dir() and not git('status','--porcelain').strip()
    source=tree(SOURCE);old=tree(OLD)
    changed=[p for p in sorted(set(old)|set(source)) if p.startswith('qualification/') and old.get(p)!=source.get(p)]
    assert changed==['qualification/mapping_v2/runtime.py','qualification/mapping_v2/runtime_protocol.json','qualification/mapping_v2/tests/test_runtime.py']
    oldrt=blob(OLD,changed[0]).decode();newrt=blob(SOURCE,changed[0]).decode()
    assert oldrt.split('\ndef worker(',1)[1]==newrt.split('\ndef worker(',1)[1]
    oldast=ast.parse(oldrt);newast=ast.parse(newrt)
    newast.body=[n for n in newast.body if not isinstance(n,ast.FunctionDef) or n.name!='enable_pinned_git_lookup']
    changed_calls=0
    for node in ast.walk(newast):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='enable_pinned_git_lookup':
            node.func.id='audit_child_env';changed_calls+=1
    assert changed_calls==1 and ast.dump(oldast)==ast.dump(newast)
    oldp=json.loads(blob(OLD,changed[1]));newp=json.loads(blob(SOURCE,changed[1]))
    assert [k for k in sorted(set(oldp)|set(newp)) if oldp.get(k)!=newp.get(k)]==['source_review_path']
    assert newp['source_review_path']=='docs/agent-reports/eld-mapping-reviewer/WP-0013/011_2026-11-17_review_eld-mapping-reviewer.md'
    assert sha(blob(SOURCE,changed[1]))=='ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783'
    addition="            environment['Q0_GIT_EXECUTABLE']='git'  # Synthetic build/audit/host resolver are mocked together here.\n"
    assert blob(SOURCE,changed[2]).decode().replace(addition,'')==blob(OLD,changed[2]).decode()
    prefix='docs/research/WP-0013/eld-mapping-author/010/'
    inv=json.loads(blob(PUB,prefix+'deliverable-inventory.json'));base=tree(inv['base']);end=tree(inv['deliverable']);pub=tree(PUB)
    diff={p for p in set(base)|set(end) if base.get(p)!=end.get(p)}
    assert diff=={r['path'] for r in inv['files']} and len(diff)==len(inv['files'])
    existing={p for p in diff if p in base};assert existing==set(changed)
    assert all(p.startswith(prefix) for p in diff-existing)
    for row in inv['files']:
        data=blob(inv['deliverable'],row['path'])
        assert len(data)==row['bytes_git'] and sha(data)==row['sha256_git']
        assert end[row['path']].split()[2]==row['git_blob'] and pub[row['path']]==end[row['path']]
    copies=json.loads(blob(PUB,prefix+'evidence/copy-manifest.json'))
    for row in copies['copied_files']:
        data=blob(PUB,row['published_path']);assert len(data)==row['bytes'] and sha(data)==row['sha256']
    for row in copies['input_files']:
        data=blob(row['revision'],row['path']);assert len(data)==row['bytes_git'] and sha(data)==row['sha256_git']
        assert tree_cache[row['revision']][row['path']].split()[2]==row['git_blob']
    for row in copies['external_executables']:
        data=Path(row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    assert git('rev-parse','HEAD:qualification/mapping_v2').decode().strip()=='1f48ce375ee15cb5a9fca8a9c873e74f4d0e0b6f'
    assert git('rev-parse','HEAD:evaluation/mapping_v2').decode().strip()=='af22f632c2b69531f61866ca467c6f04f386df7e'
    sys.path[:0]=[str(ROOT),str(ROOT/'qualification/mapping_v2/tests')]
    import test_runtime
    names=['test_runtime_worker_and_model_settings_preserve_accepted_source','test_success_and_failure_retention','test_returned_pre_and_post_observer_failures']
    suite=unittest.TestSuite(test_runtime.RuntimeTests(name) for name in names)
    with (OUT/'affected-unit-stderr.txt').open('x',encoding='utf-8',newline='\n') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','source':SOURCE,'publication':PUB,'changed_source_paths':changed,
        'worker_body_unchanged':True,'runtime_ast_only_new_helper_and_one_call':True,'protocol_changed_keys':['source_review_path'],
        'author_inventory_files':len(diff),'protected_author_paths':len(base)-len(existing),'author_copies_verified':len(copies['copied_files']),
        'author_input_descriptors_verified':len(copies['input_files']),'external_executables_verified':len(copies['external_executables']),
        'affected_unit_names':names,'affected_units_run':result.testsRun,'affected_units_pass':result.wasSuccessful(),
        'source_helper_head':git('rev-parse','HEAD').decode().strip(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'limit':'Published author original-copy hashes authenticated; author live scratch not reread. Actual source checks and three affected unit methods independently executed. No full original score suite repeated.'}
    with (OUT/'source-publication-audit.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report));assert result.wasSuccessful()
if __name__=='__main__':main()
