"""Dependency lock bound to the exact Astra /007 metadata graph (Git object), plus local-digest
records. Fail closed: the lock is structurally valid and fully bound even while one artifact
lacks a wheel SHA-256, but nothing can be installed until every artifact has an effective
digest and any local-sha256-TOFU exception is listed in the coordinator release record.

Non-circularity: the lock never contains the SHA of the review that accepts it. Accepted
review, code, protocol and lock identities are bound together by the separate coordinator
release record (release.py).
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import zipfile
from pathlib import Path

from .hashing import file_digests, git_blob_sha1_bytes, is_hex, sha256_bytes
from .outcome import Q0Failure

SCHEMA = "eldq0-lock/2"
TOFU = "local-sha256-TOFU"
PUBLISHER = "publisher-declared"
FIXED_VERSIONS = {"transformers": "4.52.1", "pypdfium2": "5.15.2", "torch": "2.13.0+cu130",
                  "torchvision": "0.28.0+cu130"}
# Distributions the pinned source imports at module scope plus loader/renderer stack.
REQUIRED_DISTRIBUTIONS = ("torch", "torchvision", "transformers", "tokenizers", "huggingface-hub", "safetensors",
                          "pypdfium2", "pillow", "numpy", "einops", "addict", "easydict", "requests", "tqdm")
# Optional backends whose mere importability changes the pinned source's code paths.
ALWAYS_FORBIDDEN_IMPORTABLE = ("flash_attn", "xformers", "triton")
_EXACT = re.compile(r"^[0-9][0-9A-Za-z.+!_-]*$")


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_lock(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_blob_reader(repo_root: Path):
    def read(oid: str) -> bytes:
        cp = subprocess.run(["git", "cat-file", "blob", oid], cwd=str(repo_root), capture_output=True)
        if cp.returncode != 0:
            raise Q0Failure("DEPENDENCY_LOCK_PENDING", f"pinned Git object {oid} unavailable: {cp.stderr[:200]!r}")
        return cp.stdout
    return read


def _fail(msg, evidence=None):
    raise Q0Failure("DEPENDENCY_LOCK_PENDING", msg, evidence)


def bound_artifacts(lock: dict, reader) -> list[dict]:
    """Read the pinned metadata graph by exact Git blob and check it against the lock's expectations."""
    src = lock["source"]
    data = reader(src["git_blob"])
    if git_blob_sha1_bytes(data) != src["git_blob"] or len(data) != src["size"]:
        _fail("metadata source bytes do not match the pinned Git blob/size")
    meta = json.loads(data.decode("utf-8"))
    if meta.get("status") != src["status"]:
        _fail("metadata source status differs", meta.get("status"))
    if meta.get("environment") != lock["platform"]["marker_environment"]:
        _fail("marker environment differs from the lock platform", meta.get("environment"))
    if meta.get("requested_extras") != []:
        _fail("extras were requested in the metadata graph")
    arts = meta["artifacts"]
    exp = lock["expect"]
    names = [canonical(a["name"]) for a in arts]
    if len(arts) != exp["artifact_count"] or len(set(names)) != len(names):
        _fail("artifact count/uniqueness differs", len(arts))
    if sum(a["size"] for a in arts) != exp["total_advertised_bytes"] or meta.get("total_advertised_bytes") != exp["total_advertised_bytes"]:
        _fail("total advertised bytes differ")
    pub = [a for a in arts if a.get("hash_kind") == PUBLISHER]
    if len(pub) != exp["publisher_declared"] or not all(is_hex(a.get("sha256"), 64) for a in pub):
        _fail("publisher-declared hash count/shape differs")
    missing = sorted(a["name"] for a in arts if a.get("sha256") is None)
    if missing != sorted(exp["missing_publisher_hash"]):
        _fail("artifacts without publisher hash differ from the expected gap", missing)
    for a in arts:
        if not _EXACT.match(str(a["version"])) or not a["filename"].endswith(".whl") or not a["url"].startswith("https://"):
            _fail(f"artifact {a['name']} lacks exact version/wheel/https url")
        if not a["filename"].endswith(("-none-any.whl", "-win_amd64.whl")):
            _fail(f"artifact {a['name']} is not a Windows AMD64/pure wheel")
    by = {canonical(a["name"]): a for a in arts}
    for name, version in FIXED_VERSIONS.items():
        if by.get(name, {}).get("version") != version:
            _fail(f"{name} must be {version}")
    absent = [d for d in REQUIRED_DISTRIBUTIONS if canonical(d) not in by]
    if absent:
        _fail("metadata graph lacks required distributions", absent)
    if any(n in by for n in ("triton", "triton-windows", "flash-attn", "xformers")):
        _fail("metadata graph contains an optional accelerated backend; policy is triton absent")
    return arts


def check_local_record(rec: dict, art: dict, gap: dict) -> None:
    want = {"name": art["name"], "version": art["version"], "filename": art["filename"], "url": art["url"],
            "size": art["size"], "hash_kind": TOFU, "metadata_sha256": gap["published_metadata_sha256"]}
    got = {k: rec.get(k) for k in want}
    if got != want or not is_hex(rec.get("sha256"), 64):
        _fail(f"local digest record for {art['name']} does not match its artifact/gap", {"got": got, "want": want})
    r = rec.get("receipt") or {}
    if not (is_hex(r.get("commit"), 40) and is_hex(r.get("git_blob"), 40) and r.get("path") and r.get("author")):
        _fail("local digest record lacks an exact published receipt pin (commit, path, git_blob, author)")


def effective_artifacts(lock: dict, arts: list[dict]) -> dict[str, dict]:
    gaps = {canonical(g["name"]): g for g in lock.get("hash_gaps", [])}
    recs = {}
    for rec in lock.get("local_hash_records", []):
        n = canonical(rec["name"])
        if n in recs:
            _fail(f"duplicate local digest record {n}")
        recs[n] = rec
    out = {}
    for a in arts:
        n = canonical(a["name"])
        e = dict(a)
        if a.get("sha256"):
            if n in recs:
                _fail(f"local record supplied for {n}, which has a publisher hash")
            e.update(effective_sha256=a["sha256"], effective_kind=PUBLISHER)
        elif n in recs:
            if n not in gaps:
                _fail(f"local record for {n} without a declared hash gap")
            check_local_record(recs[n], a, gaps[n])
            e.update(effective_sha256=recs[n]["sha256"], effective_kind=TOFU, local_record=recs[n])
        else:
            if n not in gaps:
                _fail(f"{n} has no hash and no declared gap")
            e.update(effective_sha256=None, effective_kind="missing")
        out[n] = e
    extra = sorted(set(recs) - set(out))
    if extra:
        _fail("local records for unknown artifacts", extra)
    return out


def validate_lock(lock: dict, reader) -> dict[str, dict]:
    if lock.get("schema") != SCHEMA:
        _fail("lock schema unknown")
    if "review_003" in json.dumps(lock.get("lineage", {})) or "accepted_review" in lock:
        _fail("lock must not embed the accepting review identity (bound by the release record instead)")
    plat = lock.get("platform") or {}
    if plat.get("os") != "Windows" or plat.get("machine") != "AMD64" or plat.get("python") != "3.12.10":
        _fail("lock platform must be Windows/AMD64/CPython 3.12.10")
    if lock.get("triton_policy") != "absent":
        _fail("triton_policy must be 'absent' for the strict non-Triton baseline")
    cuda = lock.get("cuda") or {}
    if cuda.get("device_capability") != [12, 0] or cuda.get("required_arch") != "sm_120":
        _fail("lock must require capability 12.0 / sm_120")
    return effective_artifacts(lock, bound_artifacts(lock, reader))


def readiness(pkgs: dict[str, dict]) -> dict:
    missing = sorted(n for n, a in pkgs.items() if not a["effective_sha256"])
    tofu = sorted(n for n, a in pkgs.items() if a["effective_kind"] == TOFU)
    return {"installable": not missing, "missing_wheel_sha256": missing,
            "required_exceptions": [f"{n}-{TOFU}" for n in tofu],
            "counts": {k: sum(1 for a in pkgs.values() if a["effective_kind"] == k) for k in (PUBLISHER, TOFU, "missing")}}


def require_installable(pkgs: dict[str, dict], release: dict | None) -> dict:
    r = readiness(pkgs)
    if not r["installable"]:
        raise Q0Failure("ACQUISITION_PROVENANCE_PENDING", "artifacts without an effective wheel SHA-256",
                        r["missing_wheel_sha256"])
    accepted = set((release or {}).get("accepted_provenance_exceptions") or [])
    lacking = [x for x in r["required_exceptions"] if x not in accepted]
    if lacking:
        raise Q0Failure("ACQUISITION_PROVENANCE_PENDING", "local-digest exceptions not accepted by the release record", lacking)
    return r


def requirements_text(pkgs: dict[str, dict]) -> str:
    """One exact pin + one sha256 per wheel for
    pip install --no-index --no-deps --only-binary=:all: --require-hashes --find-links <wheelhouse> -r <file>."""
    if not readiness(pkgs)["installable"]:
        raise Q0Failure("ACQUISITION_PROVENANCE_PENDING", "cannot write hash requirements with a missing wheel digest")
    return "".join(f"{a['name']}=={a['version']} --hash=sha256:{a['effective_sha256']}\n" for _, a in sorted(pkgs.items()))


def _req_norm(req: str) -> str:
    """'torch (==2.13.0)' and 'torch==2.13.0' compare equal; markers are kept."""
    return re.sub(r"[\s()]", "", req).lower()


def inspect_wheel_metadata(wheel: Path, name: str, version: str) -> dict:
    """Read only <dist>-<version>.dist-info/METADATA from the ZIP (no extraction, no import)."""
    with zipfile.ZipFile(wheel) as z:
        hits = [i for i in z.namelist() if i.endswith(".dist-info/METADATA") and i.count("/") == 1]
        if len(hits) != 1:
            raise Q0Failure("HASH_MISMATCH", f"{wheel.name}: expected one top-level dist-info/METADATA", hits)
        data = z.read(hits[0])
    text = data.decode("utf-8")
    fields = {}
    requires = []
    for line in io.StringIO(text):
        if not line.strip():
            break
        k, _, v = line.partition(":")
        if k == "Requires-Dist":
            requires.append(v.strip())
        else:
            fields.setdefault(k, v.strip())
    if canonical(fields.get("Name", "")) != canonical(name) or fields.get("Version") != version:
        raise Q0Failure("HASH_MISMATCH", f"{wheel.name}: METADATA name/version differ", fields)
    return {"member": hits[0], "sha256": sha256_bytes(data), "size": len(data), "requires_dist": requires}


def verify_wheelhouse(pkgs: dict[str, dict], wheelhouse: Path, lock: dict) -> dict:
    """Exactly the locked wheel files, each matching size and effective SHA-256; TOFU wheels
    additionally re-check their METADATA against the published PEP 658 digest."""
    if not readiness(pkgs)["installable"]:
        raise Q0Failure("ACQUISITION_PROVENANCE_PENDING", "wheelhouse cannot be verified with a missing wheel digest")
    want = {a["filename"]: a for a in pkgs.values()}
    present = sorted(p.name for p in Path(wheelhouse).iterdir() if p.is_file())
    extra = [n for n in present if n not in want and n != "requirements.lock.txt"]
    missing = sorted(set(want) - set(present))
    if missing or extra:
        raise Q0Failure("HASH_MISMATCH", "wheelhouse differs from the lock", {"missing": missing, "extra": extra})
    gaps = {canonical(g["name"]): g for g in lock.get("hash_gaps", [])}
    rows = []
    for name, a in sorted(want.items()):
        d = file_digests(Path(wheelhouse) / name, git_blob=False)
        row = {"wheel": name, "size": d["size"], "sha256": d["sha256"], "kind": a["effective_kind"],
               "ok": d["sha256"] == a["effective_sha256"] and d["size"] == a["size"]}
        if row["ok"] and a["effective_kind"] == TOFU:
            gap = gaps[canonical(a["name"])]
            meta = inspect_wheel_metadata(Path(wheelhouse) / name, a["name"], a["version"])
            row["metadata"] = meta
            row["ok"] = meta["sha256"] == gap["published_metadata_sha256"] and \
                _req_norm(gap["required_requires_dist"]) in {_req_norm(r) for r in meta["requires_dist"]}
        rows.append(row)
        if not row["ok"]:
            raise Q0Failure("HASH_MISMATCH", f"wheel differs from the lock: {name}", row)
    return {"wheels": rows}


def verify_installed(pkgs: dict[str, dict], lock: dict, installed: dict[str, str], importable) -> dict:
    """installed: distribution name -> version for the whole venv.
    importable: callable(module_name) -> bool (find_spec based; does not import)."""
    allowed_tooling = {canonical(n) for n in lock.get("allowed_unlocked_tooling", ["pip"])}
    want = {n: a["version"] for n, a in pkgs.items()}
    have = {canonical(k): v for k, v in installed.items()}
    wrong = {n: {"locked": v, "installed": have.get(n)} for n, v in want.items() if have.get(n) != v}
    extra = sorted(n for n in have if n not in want and n not in allowed_tooling)
    if wrong or extra:
        raise Q0Failure("DEPENDENCY_MISMATCH", "installed distributions differ from the lock", {"wrong": wrong, "extra": extra})
    present = [m for m in ALWAYS_FORBIDDEN_IMPORTABLE if importable(m)]
    if present:
        raise Q0Failure("DEPENDENCY_MISMATCH", "forbidden optional backends are importable", present)
    return {"distributions": len(have), "triton_policy": lock["triton_policy"],
            "forbidden_absent_find_spec_none": list(ALWAYS_FORBIDDEN_IMPORTABLE)}
