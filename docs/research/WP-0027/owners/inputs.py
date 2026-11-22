"""Resolve only the published calibration inputs and verify every member used."""
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[4]
PROBE = "7db67283a4ffd3e7a20bb8d80499572cc7118c71"
FIT = "6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc"
ARCHIVE = "1f246c71378e973e23ebeabfeb7fda56a8ccca2b"
REFERENCE = "b0d2dc9efee1ef27cf47e2929c05e8fbfde2fde0"
TRUTH = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/custody/v2/private/cal/truth.json")
TRUTH_SHA = "a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def check(ok, message):
    if not ok:
        raise ValueError(message)


def prepare(work):
    hashes = {}

    def blob(commit, name):
        key = f"{commit}:{name}"
        data = subprocess.check_output(["git", "cat-file", "blob", key], cwd=ROOT)
        hashes[key] = sha(data)
        return data

    def copy(path, data):
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("xb") as stream:
            stream.write(data)
        return path

    for module in ("matrix", "online", "run", "views"):
        copy(work / "probe" / (module + ".py"), blob(PROBE, f"docs/research/WP-0024/probe/{module}.py"))
    prefix = "docs/research/WP-0026/fit/"
    fit_bytes = blob(FIT, prefix + "fit.json")
    fit = json.loads(fit_bytes)
    for arm in ("M1", "M3"):
        data = blob(FIT, prefix + arm + ".pt")
        check(sha(data) == fit["weights"][arm], f"wrong {arm} weights")
        copy(work / (arm + ".pt"), data)
    data = blob(FIT, prefix + "cal-transport.json")
    check(sha(data) == fit["input_hashes"]["cal"], "wrong transport")
    routes = json.loads(data)
    truth = TRUTH.read_bytes()
    check(sha(truth) == TRUTH_SHA == fit["input_hashes"]["cal_truth"], "wrong cal truth")
    hashes[str(TRUTH)] = sha(truth)
    prefix = "docs/reviews/WP-0026/"
    reference = json.loads(blob(REFERENCE, prefix + "calibration-independent.json"))
    check(sha(fit_bytes) == reference["fit_sha256"], "wrong fit")
    inv = json.loads(blob(ARCHIVE, prefix + "cal-features-primary/inventory.json"))
    zip_bytes = blob(ARCHIVE, prefix + "cal-features-primary/primary-001.zip")
    check(sha(zip_bytes) == inv["parts"]["primary-001.zip"]["sha256"], "wrong archive")
    logical = {}
    for pair in routes["pairs"]:
        for twin in pair["twins"]:
            tags = []
            for raw in twin["windows"]:
                p = Path(raw)
                check(p.parent == Path("C:/Users/jackg/eLedgerCare-Speed/WP-0026/review/runs/cal-features-r1/sensor")
                      and re.fullmatch(r"k\d{4}", p.name), "unexpected calibration source")
                tags.append(p.name)
            check(twin["binder"] not in logical, "duplicate transport binder")
            logical[twin["binder"]] = tags
            twin["windows"] = [str(work / "windows" / tag) for tag in tags]
    tags = {tag for seq in logical.values() for tag in seq}
    check(len(tags) == 29 and sum(map(len, logical.values())) == 140, "wrong physical or logical count")
    physical = {}
    with ZipFile(io.BytesIO(zip_bytes)) as archive:
        for tag in sorted(tags):
            def member(name):
                path = f"runs/cal-features-r1/sensor/{tag}/{name}"
                raw = archive.read(path)
                check(sha(raw) == inv["members"][path]["sha256"], f"wrong archive member {path}")
                return raw
            receipt = member("receipt.json")
            r = json.loads(receipt)
            check(r["tag"] == tag and r["split"] == "cal" and r["verified"], "wrong sensor receipt")
            physical[tag] = {"receipt_sha256": sha(receipt), "ordered_rgb_sha256": [p["rgb_sha256"] for p in r["pages"]]}
            for name in ("metadata.json", "pooled.f32"):
                raw = member(name)
                check(sha(raw) == r["artifacts"][name], f"wrong receipt for {tag} {name}")
                copy(work / "windows" / tag / name, raw)
                physical[tag][name] = sha(raw)
    manifest = work / "routed.json"
    record(manifest, routes)
    return (fit, reference, manifest, logical, physical, hashes)
