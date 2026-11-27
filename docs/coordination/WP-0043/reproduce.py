"""Run the frozen WP-0043 CPU entries in a new scratch directory, serially."""
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile


FIXTURE = "f52d6ffe227dcb165299578bf2ad01978e63cb48"
REVIEW = "ba0bf6a44af7308a071ca005029ece154f6a6aec"
ROOT = Path(__file__).resolve().parents[3]


def export(revision, path, destination):
    if not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("Use a full commit SHA")
    bundle = subprocess.check_output(["git", "-C", ROOT, "archive", "--format=zip", revision, path])
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            output = (destination / member.filename).resolve()
            if not output.is_relative_to(destination):
                raise ValueError(member.filename)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(archive.read(member))
    return destination / path


def main(candidate, out):
    if sys.version_info[:3] != (3, 12, 10):
        raise RuntimeError("Use the pinned CPython 3.12.10")
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = export(FIXTURE, "docs/fixtures/WP-0043", out)
    stock = export(candidate, "docs/research/WP-0043", out)
    review = export(REVIEW, "docs/reviews/WP-0043", out)
    plan = out / "suite"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", CUDA_VISIBLE_DEVICES="")
    commands = []

    def run(name, script, *args):
        argv = [sys.executable, "-B", str(script), *map(str, args)]
        started = time.perf_counter()
        result = subprocess.run(argv, env=env, cwd=out, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out / (name + ".stdout")).write_bytes(result.stdout)
        (out / (name + ".stderr")).write_bytes(result.stderr)
        commands.append(dict(argv=argv, elapsed_seconds=time.perf_counter() - started,
                             exit=result.returncode, stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
                             stderr_sha256=hashlib.sha256(result.stderr).hexdigest()))
        (out / "commands.json").write_text(json.dumps(commands, indent=2), encoding="utf8")
        result.check_returncode()
        return out / (name + ".stdout")

    bridge = fixture / "bridge/bridge.py"
    run("plan", bridge, "plan", "--out", plan)
    run("capture-score", bridge, "run", "--plan", plan, "--candidate-dir", stock)
    run("fidelity", bridge, "fidelity", "--plan", plan)
    for version in ("2", "2.1"):
        rows = plan / ("semantic.jsonl" if version == "2" else "semantic-2.1.jsonl")
        run("compare-" + version, fixture / "bridge/semantic_compare.py", "--version", version,
            "--expected", fixture / "expected/expected.jsonl", "--plan", plan,
            "--out", rows, "--summary", out / ("summary-" + version + ".json"))
    extended = run("supplement", review / "fixture_supplement.py", stock, fixture / "generated", out / "supplement")
    equivalent = run("equivalence", review / "equal_artifacts.py", stock, fixture / "generated", out / "equivalence")
    run("reconcile", review / "reconcile.py", plan, extended, equivalent, out / "all-cases.jsonl")
    observed = [json.loads(row) for row in (out / "all-cases.jsonl").read_bytes().splitlines()]
    expected = {row["case_id"]: row["expected"]["verdict"] for row in map(json.loads,
                (fixture / "expected/expected.jsonl").read_bytes().splitlines())}
    source_verdicts = {}
    for row in observed:
        verdict = row.get("supplement", {}).get("verdict", row["candidate"])
        if verdict is not None:
            source_verdicts[row["case"]] = verdict
    assert set(expected) == {row["case"] for row in observed} and len(observed) == 50
    artifacts = json.loads(equivalent.read_bytes())
    summary = dict(candidate=candidate, fixture=FIXTURE, independent_methods=REVIEW,
                   frozen_cases=len(observed), source_cases=len(source_verdicts),
                   source_verdicts=dict(Counter(source_verdicts.values())),
                   source_only_oracle_disagreements={k: [expected[k], v] for k, v in source_verdicts.items()
                                                     if expected[k] != v},
                   without_alternative_producer=sorted(set(expected) - set(source_verdicts)),
                   artifact_pairs={row["alternative"]: row["two_normal_scorer_verdicts"] for row in artifacts},
                   public_document_scope="F5 runs two constructed greedy programs. Native F07 is a separate measurement.")
    print(json.dumps(summary, indent=2))
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate")
    parser.add_argument("new_scratch_directory", type=Path)
    args = parser.parse_args()
    main(args.candidate, args.new_scratch_directory)
