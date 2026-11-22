"""Admit the published WP-0029 routes and record each raw source/feature row."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030")
SCORE = "23c072549886ad9b5f2ab6bb08a98b0fcae423ff"
RESULT = "841233517b4694d18d144f6d2d2b17e0d0a8b444"
RESULT_SHA = "93a6054a9f8b4db7a9e231e843ee6681cf55968e85e6adde5d31959c2cdeae1e"
GATE_REV = "f51fa1dadec3e3f0e61b1d3ddade1891e24779e2"
GATE_SHA = "03e7eb07feae1f25c8db1fb4a7141820f0bda8497ab1b539bb4dbe169c51f870"
NAMES = ("Alder", "Cedar")


def check(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def save(path, data, rows=False):
    with path.open("xb") as out:
        if rows:
            out.write(b"[\n" + b",\n".join(packed(row) for row in data) + b"\n]\n")
        else:
            out.write(json.dumps(data, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def match_source(rev, path):
    rel = path.relative_to(ROOT).as_posix()
    raw = git("cat-file", "blob", rev + ":" + rel)
    check(raw.replace(b"\r\n", b"\n") == path.read_bytes().replace(b"\r\n", b"\n"), rel)
    return sha(raw)


def guards(candidate, work):
    check(git("rev-parse", "HEAD").decode().strip() == candidate, "invocation must use frozen HEAD")
    check(work.parent == PACKET / "trace" and work.is_dir(), "wrong scratch")
    check(Path(sys.executable).resolve() == PACKET / "runtime/venv/Scripts/python.exe", "wrong interpreter")
    check(sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize, "use -I -B")
    check(sys.byteorder == "little" and os.environ.get("CUDA_VISIBLE_DEVICES") == "-1", "CPU LE required")
    for k in ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE", "TRANSFORMERS_OFFLINE", "PIP_NO_INDEX",
              "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        check(os.environ.get(k) == "1", k)
    for k in ("TEMP", "TMP", "TMPDIR", "HF_HOME", "TORCH_HOME", "XDG_CACHE_HOME",
              "TORCHINDUCTOR_CACHE_DIR", "PIP_CACHE_DIR"):
        check(Path(os.environ[k]).resolve() == work / k, k)
    return {p: match_source(candidate, HERE / p) for p in ("inputs30.py", "trace.py", "findings.py", "run.ps1")}


def admit(work):
    old = ROOT / "docs/research/WP-0029/scoring"
    admission_hash = match_source(SCORE, old / "admission.py")
    sys.path.insert(0, str(old))
    import admission as a
    inputs = a.Inputs()
    inputs.hashes[SCORE + ":docs/research/WP-0029/scoring/admission.py"] = admission_hash
    # Only the immutable CPU libraries are imported. Their historical workers
    # and launchers are never run. route_inputs uses the original check_pair.
    for rev, directory, modules in (
        (a.PROBE, "WP-0024/probe", ("matrix", "online", "run", "views")),
        (a.OBSERVER, "WP-0027/owners", ("inputs", "observe")),
        (a.MEASUREMENT, "WP-0028", ("controlled", "measurement", "score_math")),
    ):
        for name in modules:
            a.write(work / "library" / (name + ".py"), inputs.blob(rev, "docs/research/" + directory + "/" + name + ".py"))
    sys.path.insert(0, str(work / "library"))
    gate = inputs.gate(GATE_REV, GATE_SHA)
    check(gate["authenticated"] and gate["eligible_owner_cue"], "independent Cedar gate")
    manifest = json.loads(inputs.blob(a.FIXTURE, "docs/fixtures/WP-0028/manifest.json"))
    pairs = sorted(manifest["pairs"], key=lambda p: p["horizon"])
    check([p["horizon"] for p in pairs] == [12, 30], "frozen pair count")
    inventory = a.route_inputs(inputs, work, pairs, gate)
    ref = json.loads(inputs.blob(RESULT, "docs/research/WP-0029/scoring/evidence/result.json", RESULT_SHA))
    check(len(inventory) == 11 and inventory == ref["capture_inventory"], "archived triples")
    fit = json.loads(inputs.blob(a.FIT, "docs/research/WP-0026/fit/fit.json"))
    check(fit["weights"] == ref["weights_sha256"] and fit["thresholds"] == ref["thresholds"], "frozen fit")
    for arm in ("M1", "M3"):
        a.write(work / (arm + ".pt"), inputs.blob(a.FIT, "docs/research/WP-0026/fit/" + arm + ".pt", fit["weights"][arm]))
    return pairs, inventory, ref, fit, inputs.hashes


def catalog(work, inventory):
    result = {}
    for key, binding in inventory.items():
        path = work / "windows" / key
        meta = json.loads((path / "metadata.json").read_bytes())
        raw = meta["raw"].encode("utf-8")
        features = (path / "pooled.f32").read_bytes()
        check(len(features) == 5120 * len(meta["spans"]), "one FP32[1280] per metadata row")
        rows = []
        for i, span in enumerate(meta["spans"]):
            check(span["index"] == i and 1 <= span["page"] <= 3, "source order")
            lo, hi = span["byte_range"]
            cs, ce = span["char_range"]
            literal = raw[lo:hi]
            token_indices = span["token_indices"]
            check(literal == meta["raw"][cs:ce].encode() and 0 <= lo < hi <= len(raw), "source byte interval")
            check(token_indices and token_indices == list(range(token_indices[0], token_indices[-1] + 1))
                  and 0 <= token_indices[0] <= token_indices[-1] < len(meta["token_ids"]), "source token indices")
            ids = [meta["token_ids"][j] for j in token_indices]
            rows.append({"metadata": span, "metadata_sha256": sha(packed(span)), "raw_span": literal.decode(),
                         "raw_span_sha256": sha(literal), "literal_sha256": sha(span["text"].encode()),
                         "feature_offset_bytes": i * 5120, "feature_sha256": sha(features[i*5120:(i+1)*5120]),
                         "selected_token_ids_u32le_sha256": sha(struct.pack("<" + "I"*len(ids), *ids))})
        result[key] = {**binding, "spans": rows}
    return result
