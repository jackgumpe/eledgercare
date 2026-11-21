"""CPU-only orchestration replay using archived native bytes, with no Baidu load or device calls."""
from contextlib import ExitStack, chdir
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import worker as w

AUTHOR = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0026/author")


def fixture(tmp, pid):
    plan = w.read(w.ROOT / "docs/coordination/WP-0025/p1-plan.json")
    old = w.read(w.previous.HISTORICAL)
    # Distinct stand-ins for the three W0 pages in an orchestration-only replay.
    pdf = tmp / "cpu-only.pdf"
    pdf.write_bytes(b"archival test stub")
    pages = [{"image": str(tmp / f"{i}.png"), "sha256": str(i)*64, "rgb_sha256": str(i+5)*64} for i in range(3)]
    req = dict(pdf=str(pdf), sha256=w.shafile(pdf), pages=3, rgb_sha256=[p["rgb_sha256"] for p in pages])
    warm = dict(fixture_sha256="e"*64, pages=pages, request=req, raster_root=str(tmp))
    calls = [dict(old["calls"][2*i + (mode == "H")], mode=mode, ordinal=2+i)
             for i, mode in enumerate(w.H0_MODES[pid])]
    plan.update(packet="WP-0026", process_id=pid, split="h0", phase="h0", lease="h0-r1", calls=calls,
                warmup=warm, requests=[req, *old["requests"]], check_groups=[], raster_root=old["raster_root"])
    return plan


def exercise(archive, tmp, pid, problem=None):
    folder = tmp / (pid + (problem or ""))
    folder.mkdir()
    plan = fixture(folder, pid)
    events = []
    cold = json.loads(archive.read("run/sensor/cold.json"))["model"]
    actual_model = w.previous.Q0 / "models/Unlimited_OCR_2_04809669"

    class Resident:
        def __init__(self, cwd):
            assert cwd == folder == Path.cwd()
            self.model = object()
            self.tokenizer = object()
            self.info = cold
            self.pin = SimpleNamespace(verify=lambda *args: None, manifest=None)
            events.append("load")

        def close(self):
            events.append("close")

    def warm(model, tokenizer, images):
        assert len(images) == 3
        events.append("W0")
        raw = json.loads(archive.read("run/sensor/b01w01S/native.json"))
        if problem == "warm_eos":
            raw["terminal_observation"]["nxt"] += 1
        return raw

    def replay(native, images, sample, hooked, retain):
        assert hooked == retain and isinstance(native, Resident) and len(images) == 3
        events.append(sample.name)
        sample.mkdir()
        for name in w.previous.COMMON_FILES | (w.previous.HIDDEN_FILES if hooked else set()):
            (sample / name).write_bytes(archive.read("run/sensor/" + sample.name + "/" + name))
        if problem == "scored_hidden" and hooked:
            (sample / "token_hidden.bf16").unlink()
        return w.read(sample / "duration.json")

    if problem == "wrong_order":
        plan["calls"].reverse()
    if problem == "wrong_prompt":
        plan["prompt_token_ids"][0] += 1
    if problem == "study_overlap":
        plan["warmup"]["pages"][0]["rgb_sha256"] = plan["calls"][0]["pages"][0]["rgb_sha256"]
        plan["warmup"]["request"]["rgb_sha256"][0] = plan["warmup"]["pages"][0]["rgb_sha256"]
    cuda_stub = SimpleNamespace(synchronize=lambda: None, reset_peak_memory_stats=lambda: None,
                                max_memory_allocated=lambda: 0, max_memory_reserved=lambda: 0)
    with ExitStack() as stack:
        stack.enter_context(chdir(folder))
        stack.enter_context(patch.dict(sys.modules, native=SimpleNamespace(MODEL=actual_model, NOTICE=None, Native=Resident),
                                       torch=SimpleNamespace(cuda=cuda_stub)))
        stack.enter_context(patch.object(w.previous, "clean_source"))
        stack.enter_context(patch.object(w.previous, "check_environment", return_value={}))
        stack.enter_context(patch.object(w, "stock", warm))
        stack.enter_context(patch.object(w, "infer", replay))
        stack.enter_context(patch.object(w, "read_images", side_effect=lambda *a: [SimpleNamespace(close=lambda: None) for _ in range(3)]))
        try:
            w.conduct(plan, w.sha256(w.pack_json(plan)).hexdigest(), folder)
        except ValueError as exc:
            if not problem:
                raise
            error = str(exc)
        else:
            assert not problem
            error = None
    before_load = problem in ("wrong_order", "wrong_prompt", "study_overlap")
    result = w.read(folder / ("error.json" if problem else "outcome.json"))
    started = 0 if before_load or problem == "warm_eos" else 1 if problem == "scored_hidden" else 8
    verified = 0 if problem else 8
    tags = [c["tag"] for c in plan["calls"]]
    assert events == ([] if before_load else ["load", "W0", *tags[:started], "close"])
    assert result["started_tags"] == tags[:started] and result["verified_tags"] == tags[:verified]
    if not before_load:
        receipt = w.read(folder / "warmup.json")
        assert receipt["ordinal"] == 1 and receipt["success"] is (problem != "warm_eos")
        assert "text" not in receipt and "token_ids" not in receipt and not (folder / "W0").exists()
    if not problem:
        assert result["real_inference_calls"] == 8 and result["warmup_calls"] == 1 and result["total_inference_calls"] == 9
        for index, tag in enumerate(tags, 2):
            p = folder / tag
            slot = w.read(p / "receipt.json")
            assert slot["ordinal"] == index and slot["warmup_sha256"] == w.shafile(folder / "warmup.json")
            assert slot["model_load_id"] == receipt["model_load_id"] == result["model_load_id"]
            assert result["rows"][tag]["through_eos_sha256"] == w.shafile(p / "through-eos.u32le")
    return dict(case=problem or pid, started=started, verified=verified, error=error)


def feature_only(archive, tmp):
    p = tmp / "feature-only"
    p.mkdir()
    for name in w.previous.COMMON_FILES | {"pooled.f32", "capture.json"}:
        (p / name).write_bytes(archive.read("run/sensor/b01w01H/" + name))
    plan = w.read(w.ROOT / "docs/coordination/WP-0025/p1-plan.json")
    sealed = w.seal_sample(p, dict(hooked=True, retain_hidden=False), w.read(p / "duration.json"), plan)
    assert (p / "through-eos.u32le").is_file() and not (p / "token_hidden.bf16").exists()
    a = {"artifacts": dict(sealed["artifacts"], **{"observed-positions.json": "a", "token_hidden.bf16": "b"})}
    b = deepcopy(a)
    test = {"check_groups": [{"left": "a", "right": "b", "mode": "duplicate"}]}
    assert w.duplicate_checks(test, {"a": a, "b": b})[0]["passed"]
    b["artifacts"]["pooled.f32"] = "c"
    assert w.duplicate_checks(test, {"a": a, "b": b})[0]["differing"] == ["pooled.f32"]
    return sealed["through_eos_sha256"]


if __name__ == "__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    assert Path(sys.executable).resolve() == (w.previous.Q0 / "venv/Scripts/python.exe").resolve()
    AUTHOR.mkdir(parents=True, exist_ok=True)
    archive = w.ROOT / "docs/reviews/WP-0024/h0-r1.zip"
    assert w.shafile(archive) == w.previous.ARCHIVE_SHA
    with ZipFile(archive) as z, TemporaryDirectory(dir=AUTHOR) as tmp:
        cases = [exercise(z, Path(tmp), pid) for pid in w.H0_MODES]
        for case in ("warm_eos", "scored_hidden", "wrong_order", "wrong_prompt", "study_overlap"):
            cases.append(exercise(z, Path(tmp), "p2", case))
        pooled = feature_only(z, Path(tmp))
    assert "torch" not in sys.modules
    print(json.dumps(dict(cpu_archival_replays=cases, pooled_only_through_eos_sha256=pooled), indent=2))
