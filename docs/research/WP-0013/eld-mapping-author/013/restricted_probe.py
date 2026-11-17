"""Actual restricted CPU child; test-only proof overlays never authorize runtime."""
import argparse
import ast
import datetime
import importlib.abc
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'qualification/q0/harness'))

class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'transformers', 'triton', 'pypdfium2', 'PIL') or fullname == 'q0harness.backend_torch':
            raise RuntimeError('CPU restricted probe forbids model/renderer import: ' + fullname)

sys.meta_path.insert(0, NoModel())
from qualification.mapping_v2 import runtime, release
from qualification.mapping_v2.common import verify_frozen_mappers, sha, protocol, HERE
from qualification.mapping_v2.protocol import common as frozen
from qualification.mapping_v2.process_identity import process_identity
from q0harness.environment import audit_child_env

AUTHORITY = '6558c3d7cf12fd336fc277d3406b26ffe125960d'
RELEASE = 'docs/coordination/WP-0013/releases/author.json'
SYNTHETIC = '0' * 40

def old_lookup(env, root, run, receipt):
    source = release.git('show', 'b60624ac7a0ae23540ab019b63d7a7e904fb1c36:qualification/mapping_v2/runtime.py').decode()
    function = next(x for x in ast.parse(source).body if isinstance(x, ast.FunctionDef) and x.name == 'enable_pinned_git_lookup')
    namespace = {'Path': Path, 'os': os}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<immutable-b606-lookup-function>', 'exec'), namespace)
    receipt['reproduced_original_source'] = 'b60624ac7a0ae23540ab019b63d7a7e904fb1c36'
    receipt['original_lookup_function_sha256'] = sha(ast.get_source_segment(source, function).encode())
    return namespace['enable_pinned_git_lookup'](env, root=root, owner='author', run_dir=run)

def shadow_fixture(case, root, run, receipt):
    fixtures = []
    if 'path' in case or 'both' in case:
        fixtures.append(root/'venv/Scripts/git.exe')
    if 'cwd' in case or 'both' in case:
        cwd = run/'caller-cwd'; cwd.mkdir(); os.chdir(cwd); fixtures.append(cwd/'git.exe')
    for path in fixtures:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'CPU invalid-image fixture; no executable code; never valid PE')
    receipt['invalid_image_fixtures'] = [{'path': str(path), 'sha256': sha(path.read_bytes())} for path in fixtures]
    receipt['actual_caller_cwd'] = str(Path.cwd())

def main(args, receipt):
    env = dict(os.environ); root = Path(args.root); run = Path(args.run)
    if 'shadow' in args.case:
        shadow_fixture(args.case, root, run, receipt)
    if args.case.startswith('old_'):
        env = old_lookup(env, root, run, receipt); os.environ.clear(); os.environ.update(env)
        receipt['old_audits_passed'] = True
        import subprocess
        control = subprocess.run([env['Q0_GIT_EXECUTABLE'], '--version'], capture_output=True, timeout=10)
        receipt['explicit_git_exit'] = control.returncode; assert control.returncode == 0
        verify_frozen_mappers()  # Actual Windows bare-Git selection, not shutil.which.
        raise AssertionError('Original shadow was not selected')
    if args.case.startswith('worker_'):
        actual_protocol = runtime.protocol; actual_read = runtime.read_release
        receipt['test_only_interceptions'] = ['runtime.protocol owned CPU root only', 'runtime.read_release call counter delegates unchanged']
        receipt['actual_read_release_calls'] = 0
        def cpu_protocol():
            value = actual_protocol(); value['runtime_roots'] = {**value['runtime_roots'], 'author': str(root)}; return value
        def counted_release(*a, **kw):
            receipt['actual_read_release_calls'] += 1; return actual_read(*a, **kw)
        runtime.protocol = cpu_protocol; runtime.read_release = counted_release
        try:
            runtime.worker(AUTHORITY, RELEASE, 'author', str(run), args.job)
        finally:
            runtime.protocol = actual_protocol; runtime.read_release = actual_read
        raise AssertionError('CPU worker unexpectedly passed stale actual release')
    if args.case in ('path_shadow', 'cwd_shadow', 'both_shadow'):
        runtime.enable_pinned_git_lookup(env, root=root, owner='author', run_dir=run)
        raise AssertionError('Shadowed Git accepted')
    # The parent uses the real production correction before spawning positive cases.
    # Negative environment cases use the original restricted PATH and invoke that
    # same correction here so its audit, rather than a parent pre-check, rejects.
    if args.case == 'missing_git': env.pop('Q0_GIT_EXECUTABLE')
    elif args.case == 'relative_git': env['Q0_GIT_EXECUTABLE'] = 'git'
    elif args.case == 'missing_binary': env['Q0_GIT_EXECUTABLE'] = str(root / 'missing/git.exe')
    elif args.case == 'mutable_git':
        path = run / 'git.exe'; path.write_bytes(b'CPU never-executed invalid binary'); env['Q0_GIT_EXECUTABLE'] = str(path)
    elif args.case == 'forbidden_env': env['PYTHONPATH'] = 'CPU forbidden inherited override'
    elif args.case == 'git_config': env['GIT_CONFIG_GLOBAL'] = 'CPU forbidden host configuration'
    if args.case in ('missing_git', 'relative_git', 'missing_binary', 'mutable_git', 'forbidden_env', 'git_config'):
        runtime.enable_pinned_git_lookup(env, root=root, owner='author', run_dir=run)
        raise AssertionError('Invalid environment accepted')
    audit_child_env(env, root=root, owner='author', run_dir=run)
    if args.case != 'original':
        receipt['selected_git'] = runtime.verify_bare_git_lookup(env)
    if args.case == 'altered_pin': frozen.PINS['qualification/baseline'] = '0' * 40
    if args.case == 'missing_pin': frozen.PINS['qualification/does-not-exist-WP13-CPU'] = '0' * 40
    verify_frozen_mappers()  # Real original Git lookups and original full pin guards.
    receipt['frozen_pins_verified'] = True
    if args.case in ('original', 'corrected_pins', 'altered_pin', 'missing_pin'): return
    if args.case == 'stale_actual_release':
        release.read_release(AUTHORITY, RELEASE, 'author', execution=False)
        raise AssertionError('Old exact-source release unexpectedly accepted')

    # Only three immutable-proof reads are overlaid because corrected /011 and
    # corrected root unseal/release do not exist yet. All Git pin/tree/status,
    # source/artifact hashes, existing admission/observations, contracts and
    # envelope checks execute unchanged against actual objects/worktree.
    real_git = release.git; head = real_git('rev-parse', 'HEAD').decode().strip(); p = protocol()
    r = json.loads(real_git('show', AUTHORITY + ':' + RELEASE))
    r.update(source_commit=head, executing_head=head, source_tree=release.tree('HEAD', 'qualification/mapping_v2'),
             protocol_sha256=sha((HERE / 'runtime_protocol.json').read_bytes()), synthetic_cpu_only=True)
    review_bytes = b'CPU-ONLY synthetic pending review; NOT independent acceptance or runtime authority\n'
    review_path = p['source_review_path']; unseal_path = 'docs/coordination/WP-0013/CPU-ONLY-unseal.json'
    r['source_review'] = {'commit': SYNTHETIC, 'path': review_path, 'sha256': sha(review_bytes), 'decision': 'accepted', 'reviewed_source_commit': head}
    unseal_bytes = json.dumps({'schema': 'eld-mapping-v2-unseal/1', 'allow_content': True, 'source_commit': head,
        'source_review_commit': SYNTHETIC, 'admission_review_commit': r['admission_review']['commit'],
        'reservation_sha256': p['public_reservation_sha256'], 'synthetic_cpu_only': True}).encode()
    r['unseal'] = {'commit': SYNTHETIC, 'path': unseal_path, 'sha256': sha(unseal_bytes)}
    if args.case == 'release_source': r['source_tree'] = '1' * 40
    if args.case == 'release_schedule': r['schedule'] = r['schedule'][:-1]
    if args.case == 'release_digest': r['source_review']['sha256'] = '1' * 64
    if args.case == 'release_lease': r['lease']['sole_lease'] = False
    overlays = {SYNTHETIC + ':' + RELEASE: json.dumps(r).encode(), SYNTHETIC + ':' + review_path: review_bytes,
                SYNTHETIC + ':' + unseal_path: unseal_bytes}
    receipt['test_only_interceptions'] = []; receipt['synthetic_cpu_release_not_authority'] = True
    def overlay_git(*argv):
        if len(argv) == 2 and argv[0] == 'show' and argv[1] in overlays:
            receipt['test_only_interceptions'].append(argv[1]); return overlays[argv[1]]
        return real_git(*argv)
    release.git = overlay_git  # Local test module binding, never production/global subprocess.
    try:
        result = release.read_release(SYNTHETIC, RELEASE, 'author', execution=False)
        assert result == r
        receipt['full_read_release_passed'] = True
        receipt['actual_contracts_validated'] = 12
        receipt['actual_families_validated'] = 4
    finally:
        release.git = real_git

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--case', required=True); parser.add_argument('--root', required=True)
    parser.add_argument('--run', required=True); parser.add_argument('--out', required=True); parser.add_argument('--job'); args = parser.parse_args()
    receipt = {'case': args.case, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'identity': process_identity(os.getpid()), 'python': sys.executable, 'path': os.environ.get('PATH'),
               'git_pin': os.environ.get('Q0_GIT_EXECUTABLE'), 'model_imports_prohibited': True}
    status = 0
    try: main(args, receipt); receipt['status'] = 'returned'
    except Exception as exc:
        status = 1; receipt.update(status='raised', error_type=type(exc).__name__, error=str(exc), winerror=getattr(exc, 'winerror', None), traceback=traceback.format_exc())
        traceback.print_exc()
    receipt['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat(); receipt['exit_code'] = status
    receipt['prohibited_imports_present'] = [name for name in sys.modules if name.split('.')[0] in ('torch', 'transformers', 'triton', 'pypdfium2', 'PIL') or name == 'q0harness.backend_torch']
    with Path(args.out).open('x', encoding='utf-8', newline='\n') as stream: json.dump(receipt, stream, indent=2); stream.write('\n')
    raise SystemExit(status)
