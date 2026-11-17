"""Independent execution of the exact public interface checkpoint; CPU only."""
import hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SEALED = HERE.parent / 'sealed'
PUBLIC = Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-reviewer')
CHECKPOINT = '63a14cafa1dee7db7cb70aca00cee529c46452fc'
sys.path.insert(0, str(PUBLIC))
import qualification
for name in ('__init__.py', 'common.py', 'contract.py'):
    actual = (SEALED / 'interface_checkpoint' / name).read_bytes()
    frozen = subprocess.check_output(['git', '-C', str(PUBLIC), 'show', CHECKPOINT + ':qualification/coverage_v1/' + name])
    assert actual == frozen, name
spec = importlib.util.spec_from_file_location('qualification.coverage_v1', SEALED / 'interface_checkpoint/__init__.py', submodule_search_locations=[str(SEALED / 'interface_checkpoint')])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
from qualification.coverage_v1.contract import validate_family, support_control
records = []
for family in ('WP11-F01', 'WP11-F02', 'WP11-F03'):
    rows = []
    for condition in ('control', 'layout', 'vocabulary', 'degraded'):
        fid = family + '-' + condition + '-v0'
        rows.append(tuple(json.loads((SEALED / 'corpus/r1' / role / (fid + '.json')).read_text()) for role in ('expected', 'reference', 'annotations')))
    assert validate_family(rows)
    records.append({'family': family, 'schema': 'PASS', 'support': support_control(*rows[0])})
assert not any(x.split('.')[0] in ('torch', 'transformers', 'triton') for x in sys.modules)
assert subprocess.check_output(['git', '-C', str(SEALED), 'status', '--porcelain']) == b''
result = {'status': 'PASS', 'checkpoint': CHECKPOINT, 'helper_commit': subprocess.check_output(['git', '-C', str(HERE), 'rev-parse', 'HEAD']).decode().strip(), 'families': 3, 'fixtures': 12, 'control_mapper_checks': 6, 'known_checkpoint_gaps': ['quantity_unit presence/value not bound by public semantic signature', 'absence expected_state not bound', 'expected absence label not compared to annotation label'], 'independent_coverage': 'audit.py checks these metadata independently; final diagnostic source acceptance remains separate', 'records': records}
with (HERE / 'interface-attempt-1.json').open('x', encoding='utf-8', newline='\n') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(json.dumps({k: result[k] for k in ('status', 'checkpoint', 'families', 'fixtures', 'control_mapper_checks')}))
