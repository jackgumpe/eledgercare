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
import zipfile
from pathlib import Path

from .environment import run_git
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


def git_blob_reader(repo_root: Path, *, environ: dict | None = None):
    def read(oid: str) -> bytes:
        try:
            cp = run_git(("cat-file", "blob", oid), cwd=repo_root, environ=environ, text=False)
        except Q0Failure as exc:
            raise Q0Failure("DEPENDENCY_LOCK_PENDING",
                            f"Git unavailable while reading pinned object {oid}: {exc.detail}") from exc
        if cp.returncode != 0:
            raise Q0Failure("DEPENDENCY_LOCK_PENDING", f"pinned Git object {oid} unavailable: {cp.stderr[:200]!r}")
        return cp.stdout
    return read


def _fail(msg, evidence=None):
    raise Q0Failure("DEPENDENCY_LOCK_PENDING", msg, evidence)


def bound_artifacts(lock: dict, reader) -> list[dict]:
    """Read the pinned metadata graph by exact Git blob and check it against the lock's expectations."""
    src = lock["source"]
    meta = json.loads(_read_pinned(reader, src).decode("utf-8"))
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
    # Frozen dependency graph (N-02): every artifact's complete published Requires-Dist list,
    # active and inactive, as recorded edges. Each acquired wheel's own METADATA must match it.
    graph = {}
    for e in meta.get("edges", []):
        p = canonical(e["parent"])
        if p not in by:
            _fail(f"graph edge from unknown parent {e['parent']}")
        graph.setdefault(p, []).append(e["requirement"])
    if meta.get("unresolved_edges"):
        _fail("metadata graph has unresolved edges", meta["unresolved_edges"])
    for a in arts:
        a["graph_requires"] = graph.get(canonical(a["name"]), [])
    _attach_published_metadata(lock, reader, by)
    return arts


def _read_pinned(reader, src: dict) -> bytes:
    data = reader(src["git_blob"])
    if git_blob_sha1_bytes(data) != src["git_blob"] or len(data) != src["size"]:
        _fail(f"pinned source {src.get('path')} bytes do not match its Git blob/size")
    return data


def _attach_published_metadata(lock: dict, reader, by: dict) -> None:
    """PEP 658 METADATA digests published by the official PyTorch index (Astra /007
    cuda-metadata.json); acquired CUDA wheels must carry exactly that METADATA."""
    src = lock["metadata_digest_source"]
    recs = json.loads(_read_pinned(reader, src).decode("utf-8"))
    seen = []
    for r in recs:
        n = canonical(r["name"])
        a = by.get(n)
        if a is None or (a["version"], a["filename"], a["url"], a["size"]) != (r["version"], r["filename"], r["url"], r["size"]):
            _fail(f"metadata digest source disagrees with the graph for {r['name']}")
        if a.get("sha256") != r.get("sha256") or not is_hex(r.get("metadata_published_sha256"), 64):
            _fail(f"metadata digest source wheel/metadata hash inconsistent for {r['name']}")
        if sha256_bytes(r["metadata_text"].encode("utf-8")) != r["metadata_published_sha256"]:
            _fail(f"recorded METADATA body does not hash to its published digest for {r['name']}")
        a["published_metadata_sha256"] = r["metadata_published_sha256"]
        seen.append(n)
    if sorted(seen) != sorted(src["names"]):
        _fail("metadata digest source covers unexpected artifacts", seen)


RECEIPT_LABEL = "local-sha256-TOFU; publisher wheel digest unavailable"


def check_local_record(rec: dict, art: dict, gap: dict, reader) -> dict:
    want = {"name": art["name"], "version": art["version"], "filename": art["filename"], "url": art["url"],
            "size": art["size"], "hash_kind": TOFU, "metadata_sha256": gap["published_metadata_sha256"],
            "provenance_label": RECEIPT_LABEL}
    got = {k: rec.get(k) for k in want}
    if got != want or not is_hex(rec.get("sha256"), 64):
        _fail(f"local digest record for {art['name']} does not match its artifact/gap", {"got": got, "want": want})
    if art.get("published_metadata_sha256") not in (None, gap["published_metadata_sha256"]):
        _fail("hash gap METADATA digest differs from the published index digest")
    r = rec.get("receipt") or {}
    if not (is_hex(r.get("commit"), 40) and is_hex(r.get("git_blob"), 40) and r.get("path") and r.get("author")
            and isinstance(r.get("size"), int)):
        _fail("local digest record lacks an exact published receipt pin (commit, path, git_blob, size, author)")
    # The receipt itself is read from its exact Git blob and must state the same facts.
    d = json.loads(_read_pinned(reader, r).decode("utf-8"))
    req_target = _req_norm(gap["required_requires_dist"])
    checks = {
        "label": d.get("label") == RECEIPT_LABEL,
        "pass": d.get("pass") is True and bool(d.get("checks")) and all(v is True for v in d["checks"].values()),
        "url": d.get("requested_url") == art["url"] and d.get("final_url") == art["url"],
        "no_redirects": d.get("redirects") == [],
        "http_200": d.get("http_status") == 200,
        "size": d.get("actual_size") == art["size"] == d.get("expected_size"),
        "local_sha256": d.get("local_sha256") == rec["sha256"],
        "metadata_sha256": d.get("metadata_sha256") == gap["published_metadata_sha256"],
        "name_version": (d.get("metadata_fields") or {}).get("Name") == art["name"]
                        and (d.get("metadata_fields") or {}).get("Version") == art["version"],
        "torch_requirement": (not req_target.startswith("!unparsed:")) and req_target in
                             {_req_norm(x) for x in (d.get("metadata_fields") or {}).get("Requires-Dist", [])},
    }
    if not all(checks.values()):
        _fail(f"receipt {r['path']} does not support the local digest record", checks)
    # Deliberately ignored: 'etag_matches_recorded_head' (reviewer-disclosed header-case reporting
    # defect N-03; the ETag strings are identical and an ETag is not a content digest).
    return checks


def effective_artifacts(lock: dict, arts: list[dict], reader) -> dict[str, dict]:
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
            receipt_checks = check_local_record(recs[n], a, gaps[n], reader)
            e.update(effective_sha256=recs[n]["sha256"], effective_kind=TOFU, local_record=recs[n],
                     receipt_checks=receipt_checks)
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
    return effective_artifacts(lock, bound_artifacts(lock, reader), reader)


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


_REQ = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?(.*)$")
_SPEC_RE = re.compile(
    r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"\s*(\[[^\]]*\])?"
    r"\s*(.*?)\s*$",
    re.DOTALL,
)
_EXTRA_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
_VER_CLAUSE = re.compile(r"^\s*(===|==|~=|!=|<=|>=|<|>)\s*([A-Za-z0-9][A-Za-z0-9._*+!-]*)\s*$")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_CMP_OPS = ("===", "==", "!=", "<=", ">=", "~=", "<", ">")
_MAX_MARKER_DEPTH = 64


class _MarkerSyntaxError(ValueError):
    pass


def _tokenize_marker(marker: str) -> list[tuple[str, str]]:
    """PEP 508 environment-marker tokenizer preserving exact quoted string contents."""
    tokens: list[tuple[str, str]] = []
    n = len(marker)
    i = 0
    while i < n:
        ch = marker[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "(":
            tokens.append(("LPAREN", "("))
            i += 1
            continue
        if ch == ")":
            tokens.append(("RPAREN", ")"))
            i += 1
            continue
        if ch in ("'", '"'):
            end = marker.find(ch, i + 1)
            if end < 0 or "\n" in marker[i + 1:end] or "\r" in marker[i + 1:end]:
                raise _MarkerSyntaxError("unterminated string literal")
            tokens.append(("STR", marker[i + 1:end]))
            i = end + 1
            continue
        matched_op = next((op for op in _CMP_OPS if marker.startswith(op, i)), None)
        if matched_op is not None:
            tokens.append(("OP", matched_op))
            i += len(matched_op)
            continue
        m = _IDENT_RE.match(marker, i)
        if m:
            word = m.group(0)
            i = m.end()
            if word == "and":
                tokens.append(("AND", "and"))
            elif word == "or":
                tokens.append(("OR", "or"))
            elif word == "in":
                tokens.append(("OP", "in"))
            elif word == "not":
                j = i
                while j < n and marker[j] in " \t\r\n":
                    j += 1
                m2 = _IDENT_RE.match(marker, j) if j > i else None
                if not m2 or m2.group(0) != "in":
                    raise _MarkerSyntaxError("expected 'in' after 'not'")
                tokens.append(("OP", "not in"))
                i = m2.end()
            else:
                tokens.append(("IDENT", word))
            continue
        raise _MarkerSyntaxError(f"unexpected character at {i}")
    return tokens


def _marker_norm(marker: str) -> str:
    """PEP 508 boolean-marker AST canonicalizer (COORD-Q0-02).

    Unwraps semantically redundant parentheses (such as singleton comparison parentheses
    '(python_version < "3.14")' that PyPI's JSON serializer strips) while preserving real
    AND/OR precedence grouping ('(a or b) and c' != 'a or (b and c)'), left-to-right operand
    order, exact operators, and exact quoted string contents via injective JSON string encoding.
    """
    tokens = _tokenize_marker(marker)
    if not tokens:
        raise _MarkerSyntaxError("empty marker")
    pos = 0

    def peek() -> tuple[str, str]:
        return tokens[pos] if pos < len(tokens) else ("EOF", "")

    def take(kind: str | None = None) -> tuple[str, str]:
        nonlocal pos
        tok = peek()
        if kind is not None and tok[0] != kind:
            raise _MarkerSyntaxError(f"expected {kind}, got {tok[0]}")
        pos += 1
        return tok

    def parse_var() -> tuple[str, str]:
        if peek()[0] in ("IDENT", "STR"):
            return take()
        raise _MarkerSyntaxError(f"expected marker operand, got {peek()[0]}")

    def parse_expr(depth: int):
        if depth > _MAX_MARKER_DEPTH:
            raise _MarkerSyntaxError("excessive marker parenthesis nesting")
        if peek()[0] == "LPAREN":
            take("LPAREN")
            node = parse_or(depth + 1)
            take("RPAREN")
            return node
        lhs = parse_var()
        op = take("OP")[1]
        rhs = parse_var()
        return ("cmp", lhs, op, rhs)

    def parse_and(depth: int):
        items = [parse_expr(depth)]
        while peek()[0] == "AND":
            take("AND")
            items.append(parse_expr(depth))
        flat = []
        for it in items:
            if it[0] == "and":
                flat.extend(it[1])
            else:
                flat.append(it)
        return flat[0] if len(flat) == 1 else ("and", tuple(flat))

    def parse_or(depth: int):
        items = [parse_and(depth)]
        while peek()[0] == "OR":
            take("OR")
            items.append(parse_and(depth))
        flat = []
        for it in items:
            if it[0] == "or":
                flat.extend(it[1])
            else:
                flat.append(it)
        return flat[0] if len(flat) == 1 else ("or", tuple(flat))

    ast = parse_or(0)
    if pos != len(tokens):
        raise _MarkerSyntaxError("trailing marker tokens")

    def fmt_var(tok: tuple[str, str]) -> str:
        return tok[1] if tok[0] == "IDENT" else json.dumps(tok[1], ensure_ascii=False)

    def fmt(node) -> str:
        if node[0] == "cmp":
            return f"{fmt_var(node[1])} {node[2]} {fmt_var(node[3])}"
        if node[0] == "and":
            return " and ".join(f"({fmt(c)})" if c[0] == "or" else fmt(c) for c in node[1])
        return " or ".join(fmt(c) for c in node[1])

    return fmt(ast)


def _req_norm(req: str) -> str:
    """Formatting-insensitive form of one PEP 508 Requires-Dist entry, so the raw wheel METADATA
    form ('torch (==2.13.0)', "zstandard; (python_version < '3.14') and extra == 'test-full'")
    and the published index form ('torch==2.13.0',
    'zstandard; python_version < "3.14" and extra == "test-full"') compare equal without relaxing
    AND/OR grouping, quoted strings, operands/operators, specifiers/extras, or syntax validity."""
    spec, sep, marker = req.partition(";")
    m = _SPEC_RE.match(spec)
    if not m:
        return "!unparsed:" + req
    name, ext_raw, ver_raw = m.group(1), m.group(2), m.group(3)
    if ext_raw is not None:
        inner = ext_raw[1:-1].strip()
        if inner == "":
            ext_items = []
        else:
            ext_items = [x.strip() for x in inner.split(",")]
            if not all(_EXTRA_NAME.match(x) for x in ext_items):
                return "!unparsed:" + req
        extras = ",".join(sorted(x.lower() for x in ext_items))
    else:
        extras = ""
    had_ver_parens = False
    while ver_raw.startswith("(") and ver_raw.endswith(")"):
        had_ver_parens = True
        ver_raw = ver_raw[1:-1].strip()
    if (had_ver_parens and not ver_raw) or "(" in ver_raw or ")" in ver_raw:
        return "!unparsed:" + req
    if ver_raw:
        clauses = []
        for raw_c in ver_raw.split(","):
            cm = _VER_CLAUSE.match(raw_c)
            if not cm:
                return "!unparsed:" + req
            clauses.append(cm.group(1) + cm.group(2))
        specs = ",".join(sorted(clauses))
    else:
        specs = ""
    if sep:
        try:
            mk = _marker_norm(marker)
        except _MarkerSyntaxError:
            return "!unparsed:" + req
    else:
        mk = ""
    return f"{canonical(name)}[{extras}]{specs};{mk}"


def verify_wheel_metadata(wheel: Path, art: dict) -> dict:
    """N-02: the wheel's own dist-info METADATA must name the locked distribution/version and
    declare exactly the frozen graph's Requires-Dist multiset; where the index published a
    PEP 658 digest, the METADATA bytes must hash to it."""
    from collections import Counter
    meta = inspect_wheel_metadata(wheel, art["name"], art["version"])
    got_norm = [_req_norm(r) for r in meta["requires_dist"]]
    want_norm = [_req_norm(r) for r in art.get("graph_requires", [])]
    unparsed = [r for r in (*got_norm, *want_norm) if r.startswith("!unparsed:")]
    got = Counter(got_norm)
    want = Counter(want_norm)
    row = {"wheel": wheel.name, "metadata_sha256": meta["sha256"], "requires_dist": len(meta["requires_dist"]),
           "graph_requires": sum(want.values()), "requires_match": got == want and not unparsed}
    if unparsed:
        row["unparsed_requires"] = unparsed
    if got != want:
        row["only_in_wheel"] = sorted((got - want).elements())
        row["only_in_graph"] = sorted((want - got).elements())
    pub = art.get("published_metadata_sha256")
    row["published_metadata_sha256_match"] = None if pub is None else meta["sha256"] == pub
    row["ok"] = row["requires_match"] and row["published_metadata_sha256_match"] is not False
    if not row["ok"]:
        raise Q0Failure("HASH_MISMATCH", f"{wheel.name}: METADATA differs from the frozen dependency graph", row)
    return row


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
    """Before any install: exactly the 32 locked wheel files; each matches its locked size and
    effective SHA-256 (publisher-declared or the bound local-sha256-TOFU receipt), AND each
    wheel's own METADATA matches the frozen dependency graph (verify_wheel_metadata, N-02)."""
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
               "payload_ok": d["sha256"] == a["effective_sha256"] and d["size"] == a["size"]}
        if not row["payload_ok"]:
            raise Q0Failure("HASH_MISMATCH", f"wheel payload differs from the lock: {name}", row)
        row["metadata"] = verify_wheel_metadata(Path(wheelhouse) / name, a)
        if a["effective_kind"] == TOFU:
            gap = gaps[canonical(a["name"])]
            if row["metadata"]["metadata_sha256"] != gap["published_metadata_sha256"]:
                raise Q0Failure("HASH_MISMATCH", f"{name}: METADATA differs from the published PEP 658 digest", row)
        rows.append(row)
    return {"wheels": rows, "metadata_checked": len(rows)}


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
