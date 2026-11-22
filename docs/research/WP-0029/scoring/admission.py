"""Resolve immutable, development-only capture identities before the CPU probe runs."""
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[4]
BASE = "4d94271a56f550bcf96b76d970f54e4c8b845ad5"
MEASUREMENT = "9cb018cecab739097abb9e1554e8c61768b257b0"
PROTOCOL = "3780eab7919108bf37c7fc32adfce0adb30da4e0"
OBSERVER = "0573f69c481eea2e815899e00ddd5e68bb4e3c42"
PROBE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
FIXTURE = "ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893"
HISTORY = "fcaf30465f0ce120c8077369155e4b624044baad"
GATE = "docs/reviews/WP-0029/capture-gate.json"
RETURN = "docs/research/WP-0029/acquisition/native-return.zip"
CEDAR = "33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5"
SENSOR = "sensor/k0001/"
OLD = "docs/reviews/WP-0026/cal-features-primary/primary-001.zip"
OLD_SHA = "e708b33aa56fbcb78ceae2e3c59a795482d9a8f09bd6796b5d5291969540b46d"
ARTIFACTS = {"metadata.json": "metadata_sha256", "pooled.f32": "pooled_sha256",
             "through-eos.u32le": "through_eos_sha256", "receipt.json": "receipt_sha256",
             "capture.json": "capture_sha256", "native.json": "native_sha256"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


class Inputs:
    def __init__(self):
        self.hashes = {}

    def blob(self, revision, path, digest=None):
        require(re.fullmatch("[0-9a-f]{40}", revision), "full immutable Git revision required")
        ref = revision + ":" + path
        result = subprocess.check_output(["git", "cat-file", "blob", ref], cwd=ROOT)
        actual = sha(result)
        require(digest is None or digest == actual, "Git artifact digest mismatch: " + ref)
        self.hashes[ref] = actual
        return result

    def stage(self, work, candidate):
        here = Path(__file__).resolve().parent
        for name in ("admission.py", "scoring.py", "run.ps1"):
            path = here / name
            raw = self.blob(candidate, path.relative_to(ROOT).as_posix())
            require(path.read_bytes().replace(b"\r\n", b"\n") == raw.replace(b"\r\n", b"\n"),
                    "candidate differs from invoked source: " + name)
        self.blob(PROTOCOL, "docs/research/WP-0028/protocol.md")
        self.blob(BASE, "docs/coordination/WP-0029/owner-math.pdf",
                  "926356c85d186244cfa7e22947d72604d44dc3f483ea3cb91979ab20d1ed0f94")
        for rev, folder, names in (
            (PROBE, "docs/research/WP-0024/probe", ("online", "matrix", "run", "views")),
            (OBSERVER, "docs/research/WP-0027/owners", ("inputs", "observe")),
            (MEASUREMENT, "docs/research/WP-0028", ("controlled", "measurement", "score_math")),
        ):
            for name in names:
                write(work / "library" / (name + ".py"), self.blob(rev, f"{folder}/{name}.py"))
        fit = json.loads(self.blob(FIT, "docs/research/WP-0026/fit/fit.json"))
        for arm in ("M1", "M3"):
            write(work / (arm + ".pt"), self.blob(FIT, "docs/research/WP-0026/fit/" + arm + ".pt",
                                                  fit["weights"][arm]))
        return fit

    def gate(self, revision, digest):
        require(re.fullmatch("[0-9a-f]{64}", digest), "full independent gate digest required")
        gate = json.loads(self.blob(revision, GATE, digest))
        require(type(gate["authenticated"]) is bool, "gate disposition missing")
        if gate["authenticated"]:
            require(gate["rgb_key"] == CEDAR and type(gate["eligible_owner_cue"]) is bool,
                    "wrong capture identity or missing separate eligibility disposition")
            require(re.fullmatch("[0-9a-f]{64}", gate["archive_sha256"]), "gate archive SHA-256")
        else:
            require(isinstance(gate.get("reason"), str) and gate["reason"], "gate denial reason missing")
        return gate


def read_capture(archive, prefix, window, expected, new):
    signature = {}
    content = {}
    for name in ARTIFACTS:
        data = archive.read(prefix + name)
        signature[name] = sha(data)
        if not new or name != "native.json" or name in expected:
            require(signature[name] == expected[name], "capture artifact mismatch: " + prefix + name)
        if name in ("receipt.json", "capture.json", "pooled.f32", "metadata.json"):
            content[name] = data
    receipt = json.loads(content["receipt.json"])
    require(receipt["verified"] is True and receipt["tag"] == prefix.rstrip("/").split("/")[-1],
            "invalid native receipt")
    require(all(receipt["artifacts"][name] == digest for name, digest in signature.items()
                if name != "receipt.json"), "receipt-to-artifact mismatch")
    require(receipt["through_eos_sha256"] == signature["through-eos.u32le"], "native EOS digest mismatch")
    capture = json.loads(content["capture.json"])
    require(capture["pooled_sha256"] == signature["pooled.f32"], "BF16 capture-to-pool mismatch")
    expected_pages = [(p["sha256"], p["rgb_sha256"]) for p in window["pages"]]
    require([(p["sha256"], p["rgb_sha256"]) for p in receipt["pages"]] == expected_pages,
            "actual ordered PNG or RGB identity differs")
    return signature, content


def route_inputs(inputs, work, pairs, gate):
    """One immutable staged record per RGB triple. The ten historical routes come from /001."""
    from controlled import check_pair

    old_files, new_uses, inventory = {}, [], {}
    for pair in pairs:
        members, missing = check_pair(pair)
        require(len(missing) == 1 and missing[0]["rgb_key"] == CEDAR, "unexpected fixture gap")
        for member in members:
            for window in member["windows"]:
                key = window["rgb_key"]
                if window["feature"] is None:
                    require(window["window"] == 1 and member["owner"] == "Cedar", "wrong Cedar role")
                    new_uses.append((pair["horizon"], member["binder"], window))
                elif key in old_files:
                    require(old_files[key]["feature"] == window["feature"] and
                            old_files[key]["pages"] == window["pages"], "inconsistent historical identity")
                else:
                    old_files[key] = window
    require(len(old_files) == 10 and sorted(n for n, _, _ in new_uses) == [12, 30],
            "wrong unique historical or Cedar use count")
    require(new_uses[0][2]["pages"] == new_uses[1][2]["pages"], "different Cedar triples")

    def stage(window, archive, prefix, expected, source, new=False):
        signature, data = read_capture(archive, prefix, window, expected, new)
        key = window["rgb_key"]
        for name in ("metadata.json", "pooled.f32"):
            write(work / "windows" / key / name, data[name])
        inventory[key] = {"source": source, "prefix": prefix, "members_sha256": signature,
                          "pages": window["pages"]}

    old_revs = {w["feature"]["archive_revision"] for w in old_files.values()}
    require(len(old_revs) == 1, "multiple old archive revisions")
    rev, = old_revs
    with ZipFile(io.BytesIO(inputs.blob(rev, OLD, OLD_SHA))) as z:
        for window in old_files.values():
            f = window["feature"]
            require(f["archive"] == OLD and f["run"] == "cal-features-r1" and
                    f["prefix"] == "runs/cal-features-r1/sensor/" + f["tag"] + "/", "wrong historical route")
            stage(window, z, f["prefix"], {name: f[key] for name, key in ARTIFACTS.items()}, rev + ":" + OLD)
    if gate and gate["authenticated"]:
        raw = inputs.blob(gate["archive_revision"], RETURN, gate["archive_sha256"])
        with ZipFile(io.BytesIO(raw)) as z:
            require(len(z.namelist()) == len(set(z.namelist())), "duplicate capture ZIP name")
            checked = gate["members_sha256"]
            required = {"sensor/warmup.json"} | {SENSOR + name for name in ARTIFACTS if name != "native.json"}
            require(required <= checked.keys(), "required independently checked member missing")
            for path, digest in checked.items():
                require(sha(z.read(path)) == digest, "independent ZIP member identity mismatch: " + path)
            expected = {name: checked[SENSOR + name] for name in ARTIFACTS if SENSOR + name in checked}
            stage(new_uses[0][2], z, SENSOR, expected, gate["archive_revision"] + ":" + RETURN, new=True)
    return inventory
