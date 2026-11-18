"""One new resident process for an ordered release plan; supervisor launch.py supplies the environment."""
import json
import os
import sys
import traceback
from contextlib import ExitStack, closing
from io import TextIOWrapper
from pathlib import Path
from time import perf_counter_ns as clock

# TextStreamer prints generated text directly. Windows redirected handles can start in CP1252 under -I.
for stream in (sys.stdout, sys.stderr):
    if isinstance(stream, TextIOWrapper):
        stream.reconfigure(encoding="utf-8", errors=stream.errors)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE), str(ROOT/"workers/local_ocr"), str(ROOT/"docs/research/WP-0014/eld-latency-author")]
from formats import digest, publish
from local_ocr.env_guard import audit_worker_environment, current_process_create_filetime
from local_ocr.pdf_render import verify_renderer_identity
from local_ocr import protocol, verify_runtime, worker
from native import GPU, LOCK_SHA, Native, Q0


def inputs(doc, first, last, request):
    rows = []
    for i in range(first, last):
        start = clock()
        with closing(doc[i]) as pg:
            points = pg.get_size()
            bitmap = pg.render(scale=protocol.RENDER_SCALE)
            try:
                image = bitmap.to_pil().convert("RGB")
            finally:
                bitmap.close()
        if max(image.size) > protocol.MAX_RASTER_AXIS_PX:
            raise ValueError("rendered image outside supported bounds")
        rgb = digest(image.tobytes())
        if request.get("rgb_sha256") and request["rgb_sha256"][i] != rgb:
            raise ValueError("raster digest changed")
        rows.append(dict(page=i+1, image=image, points=list(points), rgb_sha256=rgb,
                         width=image.width, height=image.height, render_ns=clock()-start))
    return rows


def document(request, engine, folder, renderer):
    # Accepted when a ready service receives a bound request; source fetch/hash, render,
    # recognition, adapter and durable evidence/publication are all inside the clock.
    accepted = clock()
    folder.mkdir()
    pdf = Path(request["pdf"]).read_bytes()
    if digest(pdf) != request["sha256"]:
        raise ValueError("input bytes disagree with frozen release")
    pages = []
    milestones = []
    import pypdfium2
    with pypdfium2.PdfDocument(pdf) as doc:
        if len(doc) != request["pages"] or not 1 <= len(doc) <= 60:
            raise ValueError("unexpected document page count")
        for first in range(0, len(doc), engine.window):
            batch = inputs(doc, first, min(first+engine.window, len(doc)), request)
            try:
                begin = clock()
                outputs, details = engine.read(batch, folder)
                done = clock()
                window = {"source_sha256":request["sha256"], "first_page":first+1, "pages":len(batch),
                          "engine_begin_ns":begin, "engine_end_ns":done, **details}
                publish(folder/f"window-{first+1:03d}.json",window)
                if len(outputs) != len(batch):
                    raise ValueError("incomplete native window; raw evidence is retained")
                for row, (content, raw) in zip(batch, outputs):
                    physical = row["page"]
                    evidence = {k:v for k,v in row.items() if k != "image"}
                    link = dict(source_sha256=request["sha256"],page=physical)
                    pred = dict(**link, state="complete", **content)
                    publish(folder/f"raw-{physical:03d}.json", dict(**evidence,source_sha256=request["sha256"],**raw))
                    publish(folder/f"page-{physical:03d}.json", pred)
                    pages.append(pred)
                    milestones.append(clock())
            finally:
                for row in batch:
                    row["image"].close()
    if [p["page"] for p in pages] != list(range(1,request["pages"]+1)):
        raise ValueError("incomplete or misordered publication")
    predicted = publish(folder/"prediction.json",dict(source_sha256=request["sha256"],pages=pages))
    committed = clock()
    record = dict(request=request, renderer=renderer, prediction_sha256=predicted, status="completed",
                accepted_ns=accepted, first_page_committed_ns=milestones[0], page_committed_ns=milestones,
                document_committed_ns=committed, elapsed_s=(committed-accepted)/1e9,
                first_page_s=(milestones[0]-accepted)/1e9, complete_pages=len(pages))
    publish(folder/"timing.json",record)
    return record


def main(run):
    requests = json.loads((run/"plan.json").read_bytes())["requests"]
    audit_worker_environment(dict(os.environ),run_dir=run,readonly_q0_root=Q0,leased_gpu_uuid=GPU)
    publish(run/"child.json",dict(pid=os.getpid(),creation_filetime=current_process_create_filetime()))
    rt = worker.RealTorchRuntime()
    lock, _ = verify_runtime.load_json_checked(protocol.DEPENDENCY_LOCK_PATH, LOCK_SHA, "lock")
    renderer = verify_renderer_identity(rt.import_pdfium(),rt.dist_version,lock)
    results = []
    with ExitStack() as resources:
        engines = {}
        for mode in dict.fromkeys(r["mode"] for r in requests):
            start = clock()
            if mode == "native":
                eng = Native(run)
            elif mode == "windows":
                from visual import Visual
                eng = Visual(run)
            else:
                raise ValueError("mode not implemented: " + mode)
            resources.callback(eng.close)
            engines[mode] = eng
            publish(run/f"load-{mode}.json",dict(elapsed_s=(clock()-start)/1e9,renderer=renderer,**eng.info))
        for index, req in enumerate(requests, 1):
            folder = run/f"{index:02d}-{req['label']}-{req['mode']}"
            publish(run/f"started-{index:02d}.json",dict(request=req, start_ns=clock()))
            attempted = clock()
            try:
                results.append(document(req,engines[req["mode"]],folder,renderer))
            except Exception as exc:
                publish(folder/"failure.json" if folder.exists() else run/f"failure-{index:02d}.json",
                        dict(status="failed",request=req,elapsed_since_dispatch_s=(clock()-attempted)/1e9,
                             error=repr(exc),traceback=traceback.format_exc()))
                raise
    publish(run/"session.json",results)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
