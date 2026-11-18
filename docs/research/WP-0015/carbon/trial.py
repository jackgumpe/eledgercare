"""Execute one single-mode contiguous plan segment inside an isolated child process."""
from __future__ import annotations

import json
import os
import sys
import traceback
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter_ns as clock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ASTRA = ROOT / "docs/research/WP-0015/astra"
WP14 = ROOT / "docs/research/WP-0014/eld-latency-author"
WORKER = ROOT / "workers/local_ocr"
sys.path[:0] = [str(HERE), str(ASTRA), str(WP14), str(WORKER)]

import importlib.util
from engine import MODES, create_engine
from formats import publish
from local_ocr import protocol, verify_runtime, worker
from local_ocr.env_guard import audit_worker_environment, current_process_create_filetime
from local_ocr.pdf_render import verify_renderer_identity
from native import GPU, LOCK_SHA, Q0

_astra_spec = importlib.util.spec_from_file_location("astra_trial", ASTRA / "trial.py")
_astra_trial = importlib.util.module_from_spec(_astra_spec)
_astra_spec.loader.exec_module(_astra_trial)
run_document = _astra_trial.document  # reuse Astra's exact stopwatch/render/publish boundary


def main(seg_dir: Path) -> None:
    plan_obj = json.loads((seg_dir / "plan.json").read_bytes())
    requests = plan_obj["requests"]
    modes = list(dict.fromkeys(r["mode"] for r in requests))
    if len(modes) != 1 or modes[0] not in MODES:
        raise ValueError(f"Expected single valid mode per isolated child segment, got {modes!r}")
    mode = modes[0]

    audit_worker_environment(dict(os.environ), run_dir=seg_dir, readonly_q0_root=Q0, leased_gpu_uuid=GPU)
    publish(
        seg_dir / "child.json",
        dict(pid=os.getpid(), creation_filetime=current_process_create_filetime(), mode=mode),
    )

    rt = worker.RealTorchRuntime()
    lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
    renderer = verify_renderer_identity(rt.import_pdfium(), rt.dist_version, lock)

    results = []
    with ExitStack() as resources:
        load_start = clock()
        eng = create_engine(mode, seg_dir)
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


if __name__ == "__main__":
    main(Path(sys.argv[1]))
