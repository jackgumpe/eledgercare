"""Run the exact offered public schema/support contract on authorized sealed inputs.

The offered checkpoint is not a diagnostic source acceptance. No model/diagnostic
treatment executes. Copied contract/common modules are byte-exact public Git blobs.
"""
import importlib.util, json, subprocess, sys, traceback
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-custodian')
CHECKPOINT='63a14cafa1dee7db7cb70aca00cee529c46452fc'
out=ROOT/'evidence/interface-r1';assert not out.exists();out.mkdir(parents=True)
result={'schema':'eld-wp11-public-interface-check/1','public_checkpoint':CHECKPOINT,'status':'running',
        'scope':'Schema/matched-family/control-witness support only; no fresh inference or author disclosure.'}
try:
    for name in ('__init__.py','common.py','contract.py'):
        actual=(ROOT/'interface_checkpoint'/name).read_bytes()
        expected=subprocess.check_output(['git','-C',str(PUBLIC),'show',CHECKPOINT+':qualification/coverage_v1/'+name])
        assert actual==expected,'public checkpoint bytes'
    sys.path.insert(0,str(PUBLIC))
    import qualification
    spec=importlib.util.spec_from_file_location('qualification.coverage_v1',ROOT/'interface_checkpoint/__init__.py',submodule_search_locations=[str(ROOT/'interface_checkpoint')])
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    from qualification.coverage_v1.contract import validate_family,support_control
    records=[]
    for family in ('WP11-F01','WP11-F02','WP11-F03'):
        group=[]
        for condition in ('control','layout','vocabulary','degraded'):
            fid=family+'-'+condition+'-v0'
            group.append(tuple(json.loads((ROOT/'corpus/r1'/role/(fid+'.json')).read_text()) for role in ('expected','reference','annotations')))
        validate_family(group)
        records.append({'family_id':family,'family_schema':'passed','control_support':support_control(*group[0])})
    result.update(status='passed',families=3,fixtures=12,control_mapper_checks=6,records=records)
except Exception:
    result.update(status='failed',failure=traceback.format_exc())
(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({'status':result['status'],'public_checkpoint':CHECKPOINT,'evidence':str(out/'result.json')}))
raise SystemExit(0 if result['status']=='passed' else 1)
