"""Independent restricted CPU child; no live worker/model/renderer invocation."""
import datetime
import importlib.abc
import json
import os
from pathlib import Path
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[6]
DENIED = ('torch', 'transformers', 'pypdfium2', 'PIL', 'triton',
          'q0harness.backend_torch', 'q0harness.render', 'q0harness.session',
          'q0harness.supervisor', 'q0harness.telemetry', 'q0harness.procmem')
blocked_imports = []


class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == p or fullname.startswith(p + '.') for p in DENIED):
            blocked_imports.append(fullname)
            raise AssertionError('Forbidden CPU probe import: ' + fullname)


sys.meta_path.insert(0, NoModelImports())
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'qualification/q0/harness'))
from qualification.mapping_v2.process_identity import process_identity
from q0harness.environment import audit_child_env, run_git


class PinBoundaryReached(Exception):
    pass


def main():
    config = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    receipt = {'schema': 'eld-wp13-reviewer-cpu-child/1', 'case': config['case'],
               'pid_identity': process_identity(os.getpid()),
               'start_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'q0_git_executable': os.environ.get('Q0_GIT_EXECUTABLE'),
               'bare_git_on_path': shutil.which('git'),
               'path': os.environ.get('PATH'), 'pin_entered': False,
               'pin_completed': False, 'fresh_accesses': 0,
               'synthetic_release_is_runtime_authority': False}
    print(json.dumps({'phase': 'ready', 'pid_identity': receipt['pid_identity']}), flush=True)
    if sys.stdin.readline().strip() != 'RUN':
        raise RuntimeError('Missing owned parent launch acknowledgement')
    expected = config['expected']
    try:
        audit_child_env(dict(os.environ), root=Path(config['root']), owner='reviewer',
                        run_dir=Path(config['run_dir']))
        case = config['case']
        if case == 'explicit_git_control':
            result = run_git(['rev-parse', 'HEAD'], cwd=ROOT)
            assert result.returncode == 0
            assert result.stdout.decode().strip() == config['executing_head']
            receipt['git_stdout'] = result.stdout.decode()
        elif case == 'original_release_pin_boundary':
            from qualification.mapping_v2 import release
            real_git = release.git
            real_verify = release.verify_frozen_mappers
            # Only the initial coordinator object is replaced with labeled CPU data.
            # HEAD/tree/status and every actual frozen pin command remain real Git.
            binding = config['fixture_authority'] + ':' + config['fixture_path']
            fixture_bytes = json.dumps(config['cpu_release_fixture']).encode()

            def cpu_fixture_git(*args):
                if args == ('show', binding):
                    return fixture_bytes
                return real_git(*args)

            def real_pins_then_stop():
                receipt['pin_entered'] = True
                real_verify()
                receipt['pin_completed'] = True
                raise PinBoundaryReached('CPU-only stop after real frozen pin validation')

            def no_fresh(*args, **kwargs):
                receipt['fresh_accesses'] += 1
                raise AssertionError('Unexpected fresh access')

            release.git = cpu_fixture_git
            release.verify_frozen_mappers = real_pins_then_stop
            release.read_artifact = no_fresh
            release.read_release(config['fixture_authority'], config['fixture_path'],
                                 'reviewer', execution=False)
            raise AssertionError('CPU boundary did not stop')
        else:
            raise AssertionError('Environment negative case was not rejected')
        receipt['outcome'] = 'completed'
        receipt['expected_outcome_observed'] = expected == 'completed'
    except BaseException as exc:
        traceback.print_exc()
        receipt['outcome'] = 'exception'
        receipt['exception'] = {'type': type(exc).__name__, 'message': str(exc),
                                'errno': getattr(exc, 'errno', None),
                                'winerror': getattr(exc, 'winerror', None),
                                'code': getattr(exc, 'code', None)}
        receipt['expected_outcome_observed'] = type(exc).__name__ == expected
        if config['case'] == 'original_release_pin_boundary':
            receipt['expected_outcome_observed'] &= (receipt['pin_entered'] and
                not receipt['pin_completed'] and isinstance(exc, FileNotFoundError))
    finally:
        receipt['blocked_import_attempts'] = blocked_imports
        receipt['forbidden_modules_loaded'] = sorted(n for n in sys.modules
            if any(n == p or n.startswith(p + '.') for p in DENIED))
        receipt['end_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        assert not blocked_imports and not receipt['forbidden_modules_loaded']
        assert receipt['fresh_accesses'] == 0
        with Path(config['receipt']).open('x', encoding='utf-8', newline='\n') as f:
            json.dump(receipt, f, indent=2); f.write('\n')
    # Preserve an actual nonzero child exit for rejected/failed cases.
    return 0 if receipt['outcome'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
