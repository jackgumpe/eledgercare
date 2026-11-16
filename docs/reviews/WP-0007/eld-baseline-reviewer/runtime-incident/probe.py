"""Bounded CPU diagnosis of exact accepted directory_size versus transient files."""
from __future__ import annotations
import argparse, datetime, importlib.abc, json, os, subprocess, sys, threading, time, traceback, uuid
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
SOURCE = 'f807e0ac737df4e9e0aeeb96f716afec57f58ff6'
TREE = 'df44162c62641596032df04bc834754da38a5f7b'
AUTHORITY = '7d8a9d1052caca53312db76aa54b09a6182a9e4a'
BLOCKED = ('torch', 'transformers', 'triton', 'q0harness.backend_torch')

class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + '.') for name in BLOCKED):
            raise RuntimeError('CPU probe forbids model import: ' + fullname)

sys.meta_path.insert(0, NoModelImports())
sys.path[:0] = [str(ROOT / 'qualification/baseline'), str(ROOT / 'qualification/q0/harness')]
from runtime import directory_size
from q0harness.session import Heartbeat

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()

def exception(e):
    return {'type': type(e).__name__, 'repr': repr(e), 'str': str(e),
            'filename': getattr(e, 'filename', None), 'errno': getattr(e, 'errno', None),
            'traceback': traceback.format_exc()}

def deterministic(root, after_is_file):
    root.mkdir()
    transient = root / 'heartbeat.tmp'
    transient.write_bytes(b'transient heartbeat')
    if after_is_file:
        original = Path.is_file
        def is_file(path):
            result = original(path)
            if path == transient:
                transient.unlink()  # Only the newly created owned scratch file.
            return result
        injection = patch.object(Path, 'is_file', is_file)
    else:
        original = Path.rglob
        def rglob(path, pattern):
            for entry in original(path, pattern):
                if entry == transient:
                    os.replace(transient, root / 'heartbeat.json')
                yield entry
        injection = patch.object(Path, 'rglob', rglob)
    try:
        with injection:
            size = directory_size(root)
        return {'reproduced': False, 'returned_size': size}
    except FileNotFoundError as e:
        return {'reproduced': True, 'injection': 'after is_file' if after_is_file else 'after enumeration',
                'exception': exception(e)}

def concurrent(root):
    root.mkdir()
    stopped = threading.Event()
    ready = threading.Event()
    state = {'beats': 0, 'writer_error': None}
    heartbeat = Heartbeat(root / 'heartbeat.json', 5, lambda: state['beats'])
    heartbeat.set_phase('owned_cpu_probe', 30, False)
    def writer():
        try:
            while not stopped.is_set():
                heartbeat.beat()  # Actual unchanged Q0 write_text + os.replace implementation.
                state['beats'] += 1
                ready.set()
        except BaseException as e:
            state['writer_error'] = exception(e)
            ready.set()
    thread = threading.Thread(target=writer, name='reviewer-owned-heartbeat')
    thread.start()
    ready.wait(timeout=2)
    scans = 0
    failure = None
    start = time.monotonic()
    try:
        while time.monotonic() - start < 5 and state['writer_error'] is None:
            try:
                directory_size(root)
                scans += 1
            except FileNotFoundError as e:
                failure = exception(e)
                break
    finally:
        stopped.set()
        thread.join(timeout=5)
    assert not thread.is_alive(), 'Owned heartbeat writer did not exit'
    return {'reproduced': failure is not None, 'successful_scans': scans, **state,
            'elapsed_s': time.monotonic() - start, 'exception': failure,
            'method': 'Unpatched source; tight CPU-only Heartbeat.beat loop versus directory_size. Accelerated overlap, not the original five-second cadence.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assert git('rev-parse', 'HEAD:qualification/baseline') == TREE
    assert not git('status', '--porcelain'), 'Freeze helpers and preserve clean worktree before probes'
    scratch = ROOT / '.scratch' / ('runtime-incident-' + uuid.uuid4().hex)
    assert scratch.resolve().is_relative_to((ROOT / '.scratch').resolve())
    scratch.mkdir(parents=True)
    stable = scratch / 'stable'
    stable.mkdir()
    (stable / 'a').write_bytes(b'abc')
    (stable / 'b').write_bytes(b'123456')
    stable_bytes = directory_size(stable)
    report = {'authority': AUTHORITY, 'reviewer': 'eld-baseline-reviewer', 'actual_model_effort': 'not exposed',
              'helper_head': git('rev-parse', 'HEAD'), 'source': SOURCE, 'source_tree': TREE,
              'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'python': sys.version, 'scratch': str(scratch), 'stable_file_bytes': stable_bytes,
              'stable_count_passed': stable_bytes == 9,
              'after_enumeration': deterministic(scratch / 'enumeration', False),
              'after_is_file': deterministic(scratch / 'final-stat', True),
              'concurrent_heartbeat': concurrent(scratch / 'concurrent'),
              'limits': 'Confirms only a latent source defect if reproduced. The original supervisor error lacks filename/traceback, so its call stack remains unproven. No external runtime, model/GPU or heldout content access.'}
    report['blocked_modules_loaded'] = [name for name in sys.modules if any(name == x or name.startswith(x + '.') for x in BLOCKED)]
    assert not report['blocked_modules_loaded']
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    print(json.dumps({k: report[k] if k == 'stable_count_passed' else report[k]['reproduced']
                      for k in ('stable_count_passed', 'after_enumeration', 'after_is_file', 'concurrent_heartbeat')}))

if __name__ == '__main__':
    main()
