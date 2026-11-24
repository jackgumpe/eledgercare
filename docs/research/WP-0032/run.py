"""Reproduce the six released reads in a new candidate-specific CPU scratch directory."""
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "537ab866bb5803328d378bc00f11f5782bb5ef00"
SPEED = Path("C:/Users/jackg/eLedgerCare-Speed")
PYTHON = SPEED / "WP-0030/runtime/venv/Scripts/python.exe"
PYTHON_SHA = "0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14"
PRIOR = "8f31cc66c4878ca086fa5da1498c4a73ed6a6306"
PRIOR_SOURCE = "5e1a464a38ad4213b94b3b25695bd70d9054a6a3"
PROBE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
PRIOR_REVIEW = "6ee777088c7d6121611091556246bb964c5a4227"
CLOSURE = "8962868f6476ce26b4c108daa960a13265db10cc"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
ARCHIVE = "docs/research/WP-0031/evidence/"
BLOBS = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(rev, path, expected=None):
    spec = f"{rev}:{path}"
    data = git("cat-file", "blob", spec)
    observed = digest(data)
    assert expected is None or expected == observed, spec
    BLOBS[spec] = observed
    return data


def save(path, value):
    path.write_bytes((json.dumps(value, indent=2, allow_nan=False) + "\n").encode())


def run(candidate):
    assert re.fullmatch("[0-9a-f]{40}", candidate) and git("rev-parse", "HEAD").decode().strip() == candidate
    assert git("merge-base", candidate, BASE).decode().strip() == BASE
    assert git("branch", "--show-current").decode().strip() == "research/wp-0032-accounting"
    source_hashes = {}
    for name in ("run.py", "restore.py", "account.py"):
        path = HERE / name
        actual = path.read_bytes()
        pinned = blob(candidate, path.relative_to(ROOT).as_posix())
        assert actual.replace(b"\r\n", b"\n") == pinned.replace(b"\r\n", b"\n")
        source_hashes[name] = digest(actual)
    assert sys.flags.isolated and sys.flags.dont_write_bytecode and not sys.flags.optimize
    assert Path(sys.executable).resolve() == PYTHON.resolve() and digest(PYTHON.read_bytes()) == PYTHON_SHA
    assert sys.version_info[:3] == (3, 12, 10) and sys.byteorder == "little"
    scratch = SPEED / "WP-0032/author" / candidate
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        execute(candidate, scratch, source_hashes)
    except Exception:
        (scratch / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise


def execute(candidate, scratch, source_hashes):
    for key in ("TEMP", "TMP", "TORCH_HOME", "XDG_CACHE_HOME", "TORCHINDUCTOR_CACHE_DIR", "HF_HOME"):
        (scratch / key).mkdir()
        os.environ[key] = str(scratch / key)
    os.environ.update(HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PIP_NO_INDEX="1",
                      CUDA_VISIBLE_DEVICES="-1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    evidence = scratch / "evidence"
    evidence.mkdir()
    library = scratch / "library"
    library.mkdir()

    previous = json.loads(blob(PRIOR, ARCHIVE + "runtime.json"))
    assert previous["candidate"] == previous["git_head"] == PRIOR_SOURCE
    upstream = json.loads(blob(PRIOR, ARCHIVE + "inputs.json", previous["evidence_sha256"]["inputs.json"]))["blobs_sha256"]
    for name in ("experiment.py", "inputs.py", "replay.py"):
        blob(PRIOR_SOURCE, "docs/research/WP-0031/" + name)
    for name in ("matrix.py", "online.py"):
        path = "docs/research/WP-0024/probe/" + name
        (library / name).write_bytes(blob(PROBE, path, upstream[f"{PROBE}:{path}"]))
    sys.path[:0] = [str(library), str(HERE)]
    import numpy
    import torch
    import matrix
    import online
    import restore
    import account

    assert str(torch.__version__) == "2.13.0+cpu" and torch.version.cuda is None and numpy.__version__ == "2.2.6"
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.default_generator.manual_seed(2401)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1 and torch.get_default_dtype() == torch.float32
    assert matrix.EPS == account.EPS == 1e-8
    for module in (matrix, online):
        file = Path(module.__file__)
        assert file == library / file.name and digest(file.read_bytes()) == upstream[f"{PROBE}:docs/research/WP-0024/probe/{file.name}"]
        source_hashes[file.name] = digest(file.read_bytes())
    for module in (restore, account):
        assert Path(module.__file__) == HERE / (module.__name__ + ".py")

    prior_review = json.loads(blob(PRIOR_REVIEW, "docs/reviews/WP-0031/evidence/replay.json"))
    closing = json.loads(blob(CLOSURE, "docs/coordination/WP-0031/reconciliation.json"))
    assert (closing["author_revision"], closing["review_revision"]) == (PRIOR, PRIOR_REVIEW)
    fit_path = "docs/research/WP-0026/fit/fit.json"
    fit = json.loads(blob(FIT, fit_path, upstream[f"{FIT}:{fit_path}"]))
    gates = {}
    with torch.inference_mode():
        for arm, labels in (("M1", ("AA", "AC", "CA", "CC")), ("M3", ("0A", "0C"))):
            archived = json.loads(blob(PRIOR, ARCHIVE + arm + ".json", previous["evidence_sha256"][arm + ".json"]))
            path = f"docs/research/WP-0026/fit/{arm}.pt"
            assert fit["weights"][arm] == upstream[f"{FIT}:{path}"]
            params = blob(FIT, path, fit["weights"][arm])
            assert archived["thresholds"] == fit["thresholds"][arm] == [1.0, 0.1]
            def snapshot(name):
                return blob(PRIOR, ARCHIVE + name, previous["evidence_sha256"][name])
            model, sources = restore.prepare(arm, archived, params, snapshot)
            rows = {}
            for label in labels:
                native = restore.native_read(arm, label, model, sources, archived, prior_review["probes"][arm]["cells"][label],
                                             closing["probes"][arm]["cells"][label])
                rows[label] = account.cell(arm, label, native, gates)
            contrasts = account.donor_contrasts(arm, rows, gates)
            save(evidence / (arm + ".json"), {"arm": arm, "literal_order": restore.NAMES, "thresholds": archived["thresholds"],
                                              "cells": rows, "alder_donor_minus_cedar_donor": contrasts})
    summaries = account.summaries(gates)
    save(evidence / "gates.json", {"rule": account.RULE, "groups": gates, "maxima": summaries})
    passed = all(row["pass"] for group in gates.values() for row in group)
    save(evidence / "runtime.json", {"status": "passed" if passed else "blocked", "candidate": candidate, "base": BASE,
         "literal_order": restore.NAMES, "matrix": {"M1": ["AA", "AC", "CA", "CC"], "M3": ["0A", "0C"]},
         "worktree": str(ROOT), "scratch": str(scratch), "argv": sys.orig_argv, "sys_executable": sys.executable,
         "python_sha256": PYTHON_SHA, "python": sys.version, "platform": platform.platform(), "torch": str(torch.__version__),
         "torch_build_cuda": torch.version.cuda, "numpy": numpy.__version__, "deterministic": torch.are_deterministic_algorithms_enabled(),
         "threads_intra_inter": [torch.get_num_threads(), torch.get_num_interop_threads()], "git_blobs_sha256": BLOBS,
         "loaded_source_sha256": source_hashes, "completed_utc": datetime.now(timezone.utc).isoformat(),
         "evidence_sha256": {p.name: digest(p.read_bytes()) for p in sorted(evidence.iterdir())}})
    assert passed, "precommitted reconstruction gate failed; inspect retained gates and withhold interpretation"
    print("Six original FP32 reads matched; reconstruction gates passed.", evidence)


if __name__ == "__main__":
    run(*sys.argv[1:])
