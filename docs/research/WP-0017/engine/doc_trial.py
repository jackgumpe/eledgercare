"""Execute one single-mode contiguous document trial segment (Stage A2 / A3) in an isolated process.

Reuses original Astra trial.document persisted schema verbatim so prediction.json,
timing.json, window-NNN.json, raw-NNN.json, and page-NNN.json remain 100% compatible
with inventory.py, Stage 1 pre-key verifier, and separate-process score.py.
"""
from __future__ import annotations

from contextlib import ExitStack
import importlib.util
from io import TextIOWrapper
import json
import os
import sys
import traceback
from pathlib import Path
from time import perf_counter_ns as clock

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors=_stream.errors)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP15_CARBON = ROOT / "docs/research/WP-0015/carbon"
WP15_ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
for _p in reversed((str(HERE), str(WP15_CARBON), str(WP15_ASTRA), str(WP14), str(WORKER))):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from ablation_engine import create_wp0017_engine
from formats import publish
from local_ocr import protocol, verify_runtime, worker
from local_ocr.env_guard import audit_worker_environment, current_process_create_filetime
from local_ocr.pdf_render import verify_renderer_identity
from native import GPU, LOCK_SHA, Q0
from switches import resolve_mode

_astra_spec = importlib.util.spec_from_file_location("astra_trial", WP15_ASTRA / "trial.py")
_astra_trial = importlib.util.module_from_spec(_astra_spec)
_astra_spec.loader.exec_module(_astra_trial)
run_document = _astra_trial.document


def execute_doc_segment(
    seg_dir: Path,
    *,
    engine_factory=create_wp0017_engine,
    skip_env_and_lock_audit: bool = False,
) -> list[dict]:
    plan_obj = json.loads((seg_dir / "plan.json").read_bytes())
    requests = plan_obj["requests"]
    surgical_override = plan_obj.get("surgical_override")
    modes = list(dict.fromkeys(r["mode"] for r in requests))
    if len(modes) != 1:
        raise ValueError(f"Expected single mode per isolated child segment, got {modes!r}")
    mode = modes[0]
    resolved = resolve_mode(mode, surgical_override=surgical_override)

    if not skip_env_and_lock_audit:
        audit_worker_environment(dict(os.environ), run_dir=seg_dir, readonly_q0_root=Q0, leased_gpu_uuid=GPU)
        rt = worker.RealTorchRuntime()
        lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
        renderer = verify_renderer_identity(rt.import_pdfium(), rt.dist_version, lock)
    else:
        renderer = "cpu_synthetic_stub_renderer"

    publish(
        seg_dir / "child.json",
        dict(
            pid=os.getpid(),
            creation_filetime=current_process_create_filetime(),
            mode=mode,
            canonical_mode=resolved.canonical_name,
            switch_bits=resolved.switch_config.bits,
            implementation=resolved.implementation,
        ),
    )

    results = []
    with ExitStack() as resources:
        load_start = clock()
        eng = engine_factory(mode, seg_dir, surgical_override=surgical_override)
        resources.callback(eng.close)
        publish(
            seg_dir / f"load-{mode}.json",
            dict(elapsed_s=(clock() - load_start) / 1e9, renderer=renderer, **eng.info),
        )
        for index, req in enumerate(requests, 1):
            folder = seg_dir / f"{index:02d}-{req['label']}-{req['mode']}"
            publish(seg_dir / f"started-{index:02d}.json", dict(request=req, start_ns=clock()))
            attempted = clock()
            try:
                results.append(run_document(req, eng, folder, renderer))
            except Exception as exc:
                fail_path = folder / "failure.json" if folder.exists() else seg_dir / f"failure-{index:02d}.json"
                publish(
                    fail_path,
                    dict(
                        status="failed",
                        request=req,
                        elapsed_since_dispatch_s=(clock() - attempted) / 1e9,
                        error=repr(exc),
                        traceback=traceback.format_exc(),
                    ),
                )
                raise
    publish(seg_dir / "session.json", results)
    return results


def main(seg_dir: Path) -> None:
    execute_doc_segment(seg_dir)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
