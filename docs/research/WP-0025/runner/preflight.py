"""Replay archival receipts on CPU, including abort and partial-evidence cases."""
from argparse import ArgumentParser
from contextlib import ExitStack, chdir
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import process as p
from probe import isolated_env

EXPECTED = {"S": "887ff948d9da26e2933d1d2f396dd04c865e43c7efd860aeaf3773bfc6f60705",
            "H": "d63703395cdc61e15fb86b3df73f021a56adb823ed563eb8065978023ea1554c"}


def exercise(archive, scratch, pid, failure=None):
    old = p.read(p.HISTORICAL)
    get_json = lambda name: json.loads(archive.read("run/sensor/" + name))
    cold = get_json("cold.json")["model"]
    raw = get_json("b01w01S/native.json")
    folder = scratch / (pid + (failure or "")) / "sensor"
    env = isolated_env(folder)
    for key in p.EXTRA_CACHE_VARS:
        path = folder / "cache" / key
        path.mkdir()
        env[key] = str(path)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf8")
    plan = dict(packet="WP-0025", process_id=pid, process_ordinal=int(pid[1]), deadline_seconds=1200,
                historical_plan_sha256=p.HISTORICAL_SHA, historical_archive_sha256=p.ARCHIVE_SHA,
                historical_sensor_revision=p.SOURCE, candidate="cpu-archival-preflight", environment=env,
                executable_sha256=p.shafile(sys.executable), q0_python=sys.executable, interpreter_flags=["-I", "-B"],
                model_revision=old["model_revision"], target_dtype=cold["target_dtype"], historical_platform=cold["platform"],
                model_manifest_sha256=cold["manifest_sha256"], environment_lock_sha256=cold["dependency_lock_sha256"],
                module_sha256=old["module_sha256"], tokenizer_sha256=cold["tokenizer_sha256"],
                api_prompt=p.protocol.PROMPT, eos_id=raw["eos_id"], prompt=raw["prompt"], prompt_token_ids=raw["prompt_token_ids"],
                prompt_sha256=p.PROMPT_SHA, settings=p.protocol.build_call_kwargs(3), raster_root=old["raster_root"],
                requests=old["requests"][:1], calls=[])
    for ordinal, mode in enumerate(p.ORDERS[pid], 1):
        plan["calls"].append(dict(tag=f"{pid}J{ordinal}{mode}", ordinal=ordinal, mode=mode, hooked=mode == "H",
                                  retain_hidden=mode == "H", pages=old["calls"][0]["pages"]))

    events = []

    class Resident:
        def __init__(self, location):
            assert location == Path.cwd() == folder
            events.append("load")
            self.info = cold

        def close(self):
            events.append("close")

    def replay(native, imgs, out, hooked, retain):
        mode = "H" if hooked else "S"
        events.append(mode)
        assert len(imgs) == 3 and retain == hooked and isinstance(native, Resident)
        out.mkdir()
        for name in p.COMMON_FILES | (p.HIDDEN_FILES if hooked else set()):
            (out / name).write_bytes(archive.read(f"run/sensor/b01w01{mode}/{name}"))
        if out.name == plan["calls"][1]["tag"]:
            if failure == "missing_hidden":
                (out / "token_hidden.bf16").unlink()
            if failure in ("unverified_eos", "guard_mismatch"):
                result = p.read(out / "native.json")
                if failure == "unverified_eos":
                    result["terminal_observation"]["nxt"] = 4
                else:
                    result["terminal_observation"]["guard"]["scanned"] -= 1
                (out / "native.json").write_bytes(p.pack_json(result))
        return p.read(out / "duration.json")

    if failure == "wrong_order":
        plan["calls"].reverse()
    if failure == "wrong_prompt":
        plan["prompt_token_ids"][0] = 987
    if failure == "wrong_environment":
        plan["environment"] = dict(env, HF_HUB_OFFLINE="0")
    model = p.Q0 / "models/Unlimited_OCR_2_04809669"
    archived_native = SimpleNamespace(Native=Resident, MODEL=model)
    digest = p.sha256(p.pack_json(plan)).hexdigest()
    with ExitStack() as stack:
        stack.enter_context(chdir(scratch))
        stack.enter_context(patch.dict(os.environ, env, clear=True))
        stack.enter_context(patch.dict(sys.modules, native=archived_native))
        stack.enter_context(patch.object(p, "infer", replay))
        stack.enter_context(patch.object(p, "clean_source"))  # Temp fixtures exist inside this author worktree.
        try:
            p.conduct(plan, digest, folder, time.perf_counter_ns())
        except ValueError:
            if not failure:
                raise
        else:
            assert failure is None
    before_load = failure in ("wrong_order", "wrong_prompt", "wrong_environment")
    started = 0 if before_load else 2 if failure else 4
    verified = 0 if before_load else 1 if failure else 4
    assert events == ([] if before_load else ["load", *p.ORDERS[pid][:started], "close"])
    result = p.read(folder / ("error.json" if failure else "outcome.json"))
    tags = [c["tag"] for c in plan["calls"]]
    assert result["status"] == ("incomplete" if failure else "complete")
    assert result["started_tags"] == tags[:started] and result["verified_tags"] == tags[:verified]
    for j, call in enumerate(plan["calls"]):
        sample = folder / call["tag"]
        assert (sample / "native.json").exists() == (j < started)
        assert (sample / "receipt.json").exists() == (j < verified)
        if j < verified:
            receipt = p.read(sample / "receipt.json")
            assert receipt["verified"] is True and receipt["through_eos_sha256"] == EXPECTED[call["mode"]]
            assert receipt["through_eos_length"] == 285 and receipt["pid"] == result["pid"]
            assert receipt["artifacts"] == {f.name: p.shafile(f) for f in sample.iterdir() if f.name != "receipt.json"}
    return {"case": failure or pid, "started": started, "verified": verified, "status": result["status"],
            "error": result.get("message")}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", help="Check the clean execution revision before creating temporary fixtures")
    args = parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    if args.candidate:
        p.clean_source(args.candidate)
    archive = p.ROOT / "docs/reviews/WP-0024/h0-r1.zip"
    assert p.shafile(archive) == p.ARCHIVE_SHA
    with ZipFile(archive) as z, TemporaryDirectory(dir=HERE) as tmp:
        cases = [(pid, None) for pid in p.ORDERS]
        cases += [("P1", case) for case in ("wrong_order", "wrong_prompt", "wrong_environment", "unverified_eos",
                                             "guard_mismatch", "missing_hidden")]
        results = [exercise(z, Path(tmp), pid, failure) for pid, failure in cases]
    assert "torch" not in sys.modules
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
