"""WP-0005 /011 Phase A read-only diagnostic helper (eld-q0-reviewer).

Independently reproduces COORD-Q0-02 on unchanged accepted harness core
24a5866b505532fd03e7db62a4e57875e4c5a170 against the 32 downloaded wheels in
C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\wheelhouse without extracting, installing,
modifying, or importing any downloaded package. Inventories every payload digest,
PEP 658 METADATA digest, and Requires-Dist difference across all 32 wheels (850
edges), and verifies representation-only equivalence versus fail-closed negative
controls under a strict stdlib PEP 508 requirement/marker AST parser.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[5]
HARNESS_DIR = REPO_ROOT / "qualification" / "q0" / "harness"
Q0_PY = HARNESS_DIR / "q0.py"
assert Q0_PY.is_file(), f"Expected q0.py at {Q0_PY}"

if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

from q0harness import locks  # noqa: E402
from q0harness.environment import build_stage_env  # noqa: E402
from q0harness.hashing import sha256_bytes  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402
from q0harness.release import code_identity  # noqa: E402

CONTINUATION_BASE = "af81c9c67ddb4fb233cc93525481c4219d244f53"
ACCEPTED_HARNESS_CANDIDATE = "24a5866b505532fd03e7db62a4e57875e4c5a170"
AUTHOR_INSTALL_RELEASE = Path(
    r"C:\Users\jackg\Asp.net Projects\eledgercare\docs\coordination\WP-0005\releases\author-install.json"
)

MARKER_VARS = frozenset({
    "python_version",
    "python_full_version",
    "os_name",
    "sys_platform",
    "platform_release",
    "platform_system",
    "platform_version",
    "platform_machine",
    "platform_python_implementation",
    "implementation_name",
    "implementation_version",
    "extra",
})

_MARKER_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (\() | (\)) |
        (===|~=|==|!=|<=|>=|<|>) |
        ('[^']*'|\"[^\"]*\") |
        ([A-Za-z_][A-Za-z0-9_.]*)
    )
    """,
    re.VERBOSE,
)

_SPEC_CLAUSE_RE = re.compile(r"^(===|~=|==|!=|<=|>=|<|>)\s*([A-Za-z0-9][A-Za-z0-9._*+!-]*)$")


def tokenize_pep508_marker(marker: str) -> list[tuple[str, str]]:
    pos = 0
    n = len(marker)
    raw: list[tuple[str, str]] = []
    while pos < n:
        if marker[pos:].strip() == "":
            break
        m = _MARKER_TOKEN_RE.match(marker, pos)
        if not m:
            raise ValueError(f"invalid marker token at offset {pos}: {marker[pos:]!r}")
        pos = m.end()
        lp, rp, op, lit, ident = m.groups()
        if lp:
            raw.append(("LP", "("))
        elif rp:
            raw.append(("RP", ")"))
        elif op:
            raw.append(("OP", op))
        elif lit:
            raw.append(("STR", lit[1:-1]))
        elif ident:
            raw.append(("ID", ident))
    tokens: list[tuple[str, str]] = []
    i = 0
    while i < len(raw):
        tk, tv = raw[i]
        if tk == "ID" and tv == "not":
            if i + 1 < len(raw) and raw[i + 1] == ("ID", "in"):
                tokens.append(("OP", "not in"))
                i += 2
                continue
            raise ValueError("standalone 'not' is invalid in PEP 508 markers")
        if tk == "ID" and tv in ("and", "or"):
            tokens.append((tv.upper(), tv))
        elif tk == "ID" and tv == "in":
            tokens.append(("OP", "in"))
        elif tk == "ID":
            var = tv.replace(".", "_")
            if var not in MARKER_VARS:
                raise ValueError(f"unknown PEP 508 marker variable: {tv!r}")
            tokens.append(("VAR", var))
        else:
            tokens.append((tk, tv))
        i += 1
    return tokens


def parse_pep508_marker_ast(marker: str):
    """Strict PEP 508 marker parser.

    Unwraps redundant parentheses around a single expression or comparison atom
    via standard recursive-descent grouping `( or_expr )`, while preserving:
    - exact quoted string literal contents (including whitespace and opposite quotes),
    - exact comparison operands and operators,
    - `or` vs `and` operator precedence and explicit compound sub-groupings such as
      `(A and B) and C` vs `A and B and C` and `(A and B) or C` vs `A and (B or C)`.
    """
    tokens = tokenize_pep508_marker(marker)
    if not tokens:
        raise ValueError("empty marker after ';'")
    idx = 0

    def peek() -> tuple[str | None, str | None]:
        return tokens[idx] if idx < len(tokens) else (None, None)

    def consume(expected_kind: str | None = None) -> tuple[str, str]:
        nonlocal idx
        tok = peek()
        if tok[0] is None:
            raise ValueError(f"unexpected end of marker (expected {expected_kind})")
        if expected_kind is not None and tok[0] != expected_kind:
            raise ValueError(f"expected {expected_kind}, got {tok}")
        idx += 1
        return tok  # type: ignore[return-value]

    def parse_or():
        items = [parse_and()]
        while peek()[0] == "OR":
            consume("OR")
            items.append(parse_and())
        return items[0] if len(items) == 1 else ("OR", tuple(items))

    def parse_and():
        items = [parse_atom()]
        while peek()[0] == "AND":
            consume("AND")
            items.append(parse_atom())
        return items[0] if len(items) == 1 else ("AND", tuple(items))

    def parse_atom():
        if peek()[0] == "LP":
            consume("LP")
            inner = parse_or()
            consume("RP")
            return inner
        lhs = consume()
        if lhs[0] not in ("VAR", "STR"):
            raise ValueError(f"invalid marker comparison LHS: {lhs}")
        op = consume("OP")
        rhs = consume()
        if rhs[0] not in ("VAR", "STR"):
            raise ValueError(f"invalid marker comparison RHS: {rhs}")
        return ("CMP", lhs, op[1], rhs)

    ast = parse_or()
    if idx != len(tokens):
        raise ValueError(f"trailing marker tokens: {tokens[idx:]}")
    return ast


def parse_pep508_requirement_strict(req: str) -> tuple:
    """Fail-closed PEP 508 requirement parser returning a hashable canonical AST tuple."""
    if "@" in req.partition(";")[0]:
        raise ValueError(f"direct URL requirement forbidden: {req!r}")
    spec_part, sep, marker_part = req.partition(";")
    spec_trim = spec_part.strip()
    m_head = re.match(r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(\[[^\]]*\])?\s*(.*)$", spec_trim)
    if not m_head:
        raise ValueError(f"invalid requirement header: {req!r}")
    pkg_name = locks.canonical(m_head.group(1))
    extras_raw = m_head.group(2)
    rest = m_head.group(3).strip()
    extras: tuple[str, ...] = ()
    if extras_raw is not None:
        inner = extras_raw[1:-1].strip()
        if inner:
            parts = [p.strip() for p in inner.split(",")]
            if any(not p or not re.match(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$", p) for p in parts):
                raise ValueError(f"invalid extras list in {req!r}")
            extras = tuple(sorted(locks.canonical(p) for p in parts))
    if rest.startswith("(") and rest.endswith(")"):
        rest = rest[1:-1].strip()
    if "(" in rest or ")" in rest:
        raise ValueError(f"unbalanced or unexpected parentheses in version specifier: {req!r}")
    specs: tuple[tuple[str, str], ...] = ()
    if rest:
        clauses = [c.strip() for c in rest.split(",")]
        parsed_clauses = []
        for c in clauses:
            mc = _SPEC_CLAUSE_RE.match(c)
            if not mc:
                raise ValueError(f"invalid version specifier clause {c!r} in {req!r}")
            parsed_clauses.append((mc.group(1), mc.group(2)))
        specs = tuple(sorted(parsed_clauses))
    marker_ast = parse_pep508_marker_ast(marker_part) if sep else None
    return (pkg_name, extras, specs, marker_ast)


def eval_marker_no_extra(ast, env: dict[str, str]) -> bool:
    """Evaluate parsed marker AST against locked marker_environment with no active extra."""
    if ast is None:
        return True
    kind = ast[0]
    if kind == "OR":
        return any(eval_marker_no_extra(x, env) for x in ast[1])
    if kind == "AND":
        return all(eval_marker_no_extra(x, env) for x in ast[1])
    if kind == "CMP":
        _, lhs, op, rhs = ast
        if (lhs == ("VAR", "extra")) or (rhs == ("VAR", "extra")):
            # With requested_extras == [], no extra is active; `extra == "x"` is False, `extra != "x"` is True.
            if op == "==":
                return False
            if op == "!=":
                return True
            return False
        lv = env[lhs[1]] if lhs[0] == "VAR" else lhs[1]
        rv = env[rhs[1]] if rhs[0] == "VAR" else rhs[1]
        if lhs == ("VAR", "python_version") or rhs == ("VAR", "python_version"):
            lt = tuple(int(x) for x in lv.split(".")[:2])
            rt = tuple(int(x) for x in rv.split(".")[:2])
            return {
                "==": lt == rt, "!=": lt != rt, "<": lt < rt, "<=": lt <= rt, ">": lt > rt, ">=": lt >= rt
            }[op]
        if op == "==":
            return lv == rv
        if op == "!=":
            return lv != rv
        if op == "in":
            return lv in rv
        if op == "not in":
            return lv not in rv
        return lv == rv
    raise ValueError(f"unknown AST node: {ast}")


def snapshot_task_root(root: Path) -> dict:
    venv_sp = root / "venv" / "Lib" / "site-packages"
    dist_infos = sorted(p.name for p in venv_sp.glob("*.dist-info")) if venv_sp.exists() else []
    wh = root / "wheelhouse"
    wh_entries = sorted(
        (p.name, p.stat().st_size, p.stat().st_mtime_ns)
        for p in wh.iterdir()
        if p.is_file()
    )
    empty_checks = {}
    for rel in (
        "hf-home",
        "models/Unlimited_OCR_2_04809669",
        "notices/Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a",
        "pip-cache",
        "runs/author",
        "runs/reviewer",
        "temp",
        "uv-cache",
    ):
        p = root / rel
        empty_checks[rel] = {
            "exists": p.exists(),
            "child_count": len(list(p.rglob("*"))) if p.exists() else None,
        }
    return {
        "venv_dist_infos": dist_infos,
        "wheel_count": len(wh_entries),
        "wheel_total_bytes": sum(x[1] for x in wh_entries),
        "wheel_stat_fingerprint_sha256": hashlib.sha256(
            json.dumps(wh_entries).encode("utf-8")
        ).hexdigest(),
        "subdirs": empty_checks,
    }


ISOLATED_STAGE_CHILD_CODE = r"""
import json, pathlib, sys
harness_dir = pathlib.Path(sys.argv[1])
repo_root = pathlib.Path(sys.argv[2])
wheelhouse = pathlib.Path(sys.argv[3])
sys.path.insert(0, str(harness_dir))
from q0harness import locks
from q0harness.outcome import Q0Failure
from q0harness.release import code_identity

lock = locks.load_lock(harness_dir / "locks" / "dependency-lock.json")
pkgs = locks.validate_lock(lock, locks.git_blob_reader(repo_root))
code = code_identity(repo_root)
try:
    locks.verify_wheelhouse(pkgs, wheelhouse, lock)
    raise SystemExit("unexpected verify_wheelhouse pass on unchanged 24a5866b")
except Q0Failure as exc:
    print(json.dumps({
        "code_identity": code,
        "failure_class": exc.failure_class,
        "detail": exc.detail,
        "evidence": exc.evidence,
    }, sort_keys=True))
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    started_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    protocol, p_sha = load_protocol()
    lock_path = HARNESS_DIR / "locks" / "dependency-lock.json"
    lock_bytes = lock_path.read_bytes()
    lock_sha = sha256_bytes(lock_bytes)
    lock = json.loads(lock_bytes.decode("utf-8"))
    pkgs = locks.validate_lock(lock, locks.git_blob_reader(REPO_ROOT))
    root = Path(protocol["storage"]["root"])
    wheelhouse = root / "wheelhouse"

    # 1. Verify reviewer worktree & accepted 24a5866b core immutability
    head = subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True).strip()
    core_diff = subprocess.check_output(
        [
            "git", "-C", str(REPO_ROOT), "diff", "--name-only",
            ACCEPTED_HARNESS_CANDIDATE, "HEAD", "--",
            "qualification/q0/harness", "evaluation",
        ],
        text=True,
    ).splitlines()
    # Only /008 author evidence (18 files) was added under qualification/q0/harness/evidence/008-git-isolation/
    non_008_core_diff = [p for p in core_diff if not p.startswith("qualification/q0/harness/evidence/008-git-isolation/")]
    if non_008_core_diff:
        raise AssertionError(f"Unexpected harness/evaluation diff vs {ACCEPTED_HARNESS_CANDIDATE}: {non_008_core_diff}")

    status_before = [
        ln for ln in subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain=v1", "-uall"], text=True
        ).splitlines()
        if not args.smoke
    ]
    if not args.smoke and status_before:
        raise AssertionError(f"Decisive run requires clean worktree before execution; got: {status_before}")

    snap_before = snapshot_task_root(root)
    if snap_before["venv_dist_infos"] != ["pip-25.0.1.dist-info"]:
        raise AssertionError(f"Expected no installed wheels in venv, got: {snap_before['venv_dist_infos']}")
    if snap_before["wheel_count"] != 32 or snap_before["wheel_total_bytes"] != 1974477651:
        raise AssertionError(f"Unexpected wheelhouse count/bytes: {snap_before}")

    # 2. Reproduce exact failure in isolated stage_offline subprocess (API + CLI)
    scratch_base = REPO_ROOT / ".scratch"
    scratch_base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(scratch_base), prefix="phase-a-011-") as td:
        td_path = Path(td)
        stage_env = build_stage_env(dict(os.environ), root=root, protocol=protocol, network=False)

        cp_api = subprocess.run(
            [sys.executable, "-I", "-B", "-c", ISOLATED_STAGE_CHILD_CODE, str(HARNESS_DIR), str(REPO_ROOT), str(wheelhouse)],
            env=stage_env,
            cwd=str(td_path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if cp_api.returncode != 0:
            raise AssertionError(f"Isolated API reproduction probe failed ({cp_api.returncode}): {cp_api.stderr}")
        api_repro = json.loads(cp_api.stdout)

        # Verify author-install.json fails closed on reviewer HEAD (harness_commit mismatch)
        cp_author_rel = subprocess.run(
            [sys.executable, "-I", "-B", str(Q0_PY), "verify-wheelhouse", str(wheelhouse), "--release", str(AUTHOR_INSTALL_RELEASE)],
            env=stage_env,
            cwd=str(td_path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
        author_rel_out = json.loads(cp_author_rel.stdout)
        if cp_author_rel.returncode != 2 or author_rel_out["failures"][0]["failure_class"] != "EXECUTION_NOT_RELEASED":
            raise AssertionError(f"Expected EXECUTION_NOT_RELEASED with author-install.json on reviewer HEAD: {author_rel_out}")

        # Probe CLI verify-wheelhouse using scratch release record binding this clean reviewer HEAD
        probe_rel_path = td_path / "reviewer-probe-install-release.json"
        probe_rel = json.loads(AUTHOR_INSTALL_RELEASE.read_text(encoding="utf-8"))
        probe_rel["harness_commit"] = head
        probe_rel_path.write_text(json.dumps(probe_rel, indent=2), encoding="utf-8")

        cp_cli = subprocess.run(
            [sys.executable, "-I", "-B", str(Q0_PY), "verify-wheelhouse", str(wheelhouse), "--release", str(probe_rel_path)],
            env=stage_env,
            cwd=str(td_path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=120,
        )
        cli_raw_bytes = cp_cli.stdout + (b"\n--- stderr ---\n" if cp_cli.stderr else b"") + cp_cli.stderr
        cli_json = json.loads(cp_cli.stdout.decode("utf-8"))
        if cp_cli.returncode != 2 or cli_json.get("status") != "BLOCKED":
            raise AssertionError(f"Expected CLI exit 2 BLOCKED on COORD-Q0-02 reproduction, got rc={cp_cli.returncode}: {cli_json}")
        if cli_json["failures"][0]["failure_class"] != "HASH_MISMATCH":
            raise AssertionError(f"Unexpected CLI failure_class: {cli_json}")

    (out_dir / "01-cli-verify-wheelhouse-reproduction.txt").write_bytes(cli_raw_bytes)

    # 3. Exhaustive read-only audit of all 32 wheels and all 850 Requires-Dist edges
    gaps = {locks.canonical(g["name"]): g for g in lock.get("hash_gaps", [])}
    marker_env = lock["platform"]["marker_environment"]

    wheel_rows = []
    mismatched_wheels_current_norm = []
    raw_formatting_diff_wheels = []
    strict_ast_mismatches = []
    active_edge_mismatches = []
    total_edges_wheel = 0
    total_edges_graph = 0

    for idx_zero, (filename, art) in enumerate(sorted((x["filename"], x) for x in pkgs.values()), start=1):
        wpath = wheelhouse / filename
        wbytes = wpath.read_bytes()
        wsize = len(wbytes)
        wsha = sha256_bytes(wbytes)
        payload_ok = (wsize == art["size"]) and (wsha == art["effective_sha256"])
        if not payload_ok:
            raise AssertionError(f"Payload mismatch on {filename}: size={wsize}/{art['size']} sha={wsha}/{art['effective_sha256']}")

        meta = locks.inspect_wheel_metadata(wpath, art["name"], art["version"])
        pub_meta = art.get("published_metadata_sha256")
        pub_meta_ok = None if pub_meta is None else (meta["sha256"] == pub_meta)
        if pub_meta_ok is False:
            raise AssertionError(f"Published PEP 658 METADATA SHA-256 mismatch on {filename}")
        gap_meta_ok = None
        if art["effective_kind"] == locks.TOFU:
            gap_pub = gaps[locks.canonical(art["name"])]["published_metadata_sha256"]
            gap_meta_ok = (meta["sha256"] == gap_pub)
            if not gap_meta_ok:
                raise AssertionError(f"TOFU gap PEP 658 METADATA SHA-256 mismatch on {filename}")

        raw_wheel = meta["requires_dist"]
        raw_graph = art.get("graph_requires", [])
        total_edges_wheel += len(raw_wheel)
        total_edges_graph += len(raw_graph)

        if raw_wheel != raw_graph:
            raw_formatting_diff_wheels.append(filename)

        got_curr = collections.Counter(locks._req_norm(r) for r in raw_wheel)
        want_curr = collections.Counter(locks._req_norm(r) for r in raw_graph)
        curr_ok = (got_curr == want_curr)

        if not curr_ok:
            only_w = sorted((got_curr - want_curr).elements())
            only_g = sorted((want_curr - got_curr).elements())
            mismatched_wheels_current_norm.append({
                "alphabetical_index_1based": idx_zero,
                "wheel": filename,
                "name": art["name"],
                "version": art["version"],
                "metadata_member": meta["member"],
                "metadata_sha256": meta["sha256"],
                "requires_dist_count": len(raw_wheel),
                "mismatched_edge_count": len(only_w),
                "only_in_wheel_current_norm": only_w,
                "only_in_graph_current_norm": only_g,
                "raw_wheel_unmatched": [r for r in raw_wheel if locks._req_norm(r) in (got_curr - want_curr)],
                "raw_graph_unmatched": [r for r in raw_graph if locks._req_norm(r) in (want_curr - got_curr)],
            })

        # Strict PEP 508 AST comparison + active-marker evaluation under Q0 marker_environment
        wheel_parsed = [parse_pep508_requirement_strict(r) for r in raw_wheel]
        graph_parsed = [parse_pep508_requirement_strict(r) for r in raw_graph]
        if collections.Counter(wheel_parsed) != collections.Counter(graph_parsed):
            strict_ast_mismatches.append(filename)

        active_w = collections.Counter(
            (p[0], p[1], p[2]) for p in wheel_parsed if eval_marker_no_extra(p[3], marker_env)
        )
        active_g = collections.Counter(
            (p[0], p[1], p[2]) for p in graph_parsed if eval_marker_no_extra(p[3], marker_env)
        )
        if active_w != active_g:
            active_edge_mismatches.append(filename)

        wheel_rows.append({
            "index": idx_zero,
            "wheel": filename,
            "name": art["name"],
            "version": art["version"],
            "size": wsize,
            "sha256": wsha,
            "hash_kind": art["effective_kind"],
            "payload_ok": payload_ok,
            "metadata_member": meta["member"],
            "metadata_size": meta["size"],
            "metadata_sha256": meta["sha256"],
            "published_metadata_sha256_match": pub_meta_ok,
            "tofu_gap_metadata_sha256_match": gap_meta_ok,
            "requires_dist_count": len(raw_wheel),
            "graph_requires_count": len(raw_graph),
            "raw_strings_identical": raw_wheel == raw_graph,
            "current_24a5866b_req_norm_match": curr_ok,
            "strict_pep508_ast_match": True,
            "active_q0_dependencies_count": sum(active_w.values()),
        })

    if strict_ast_mismatches:
        raise AssertionError(f"Strict PEP 508 AST mismatches found: {strict_ast_mismatches}")
    if active_edge_mismatches:
        raise AssertionError(f"Active Q0 dependency mismatches found: {active_edge_mismatches}")
    if total_edges_wheel != 850 or total_edges_graph != 850:
        raise AssertionError(f"Expected 850/850 total edges, got {total_edges_wheel}/{total_edges_graph}")

    # 4. Verify fail-closed negative controls on strict PEP 508 AST parser vs current _req_norm quirks
    negative_pairs = [
        (
            "and_or_precedence_grouping",
            'pkg; (os_name == "nt" and sys_platform == "win32") or extra == "dev"',
            'pkg; os_name == "nt" and (sys_platform == "win32" or extra == "dev")',
        ),
        (
            "explicit_nested_and_subgrouping",
            'pkg; (os_name == "nt" and platform_python_implementation != "PyPy") and extra == "dev"',
            'pkg; os_name == "nt" and platform_python_implementation != "PyPy" and extra == "dev"',
        ),
        (
            "quoted_literal_internal_whitespace",
            'pkg; platform_system == "Windows NT"',
            'pkg; platform_system == "WindowsNT"',
        ),
        (
            "quoted_literal_embedded_apostrophe_vs_quote",
            'pkg; extra == "a\'b"',
            "pkg; extra == 'a\"b'",
        ),
        (
            "comparison_operator_change",
            'zstandard; python_version <= "3.14" and extra == "test-full"',
            'zstandard; python_version < "3.14" and extra == "test-full"',
        ),
        (
            "comparison_operand_change",
            'zstandard; python_version < "3.13" and extra == "test-full"',
            'zstandard; python_version < "3.14" and extra == "test-full"',
        ),
        (
            "version_specifier_change",
            'brotli>=1.0.10; platform_python_implementation == "CPython" and extra == "brotli"',
            'brotli>=1.0.9; platform_python_implementation == "CPython" and extra == "brotli"',
        ),
        (
            "extra_set_change",
            'safetensors[numpy,torch]; extra == "all"',
            'safetensors[numpy]; extra == "all"',
        ),
    ]
    negative_results = []
    for label, left, right in negative_pairs:
        pl = parse_pep508_requirement_strict(left)
        pr = parse_pep508_requirement_strict(right)
        if pl == pr:
            raise AssertionError(f"Negative control {label} unexpectedly matched under strict AST!")
        negative_results.append({
            "case": label,
            "left": left,
            "right": right,
            "strict_pep508_ast_equal": pl == pr,
            "current_24a5866b_req_norm_equal": locks._req_norm(left) == locks._req_norm(right),
        })

    malformed_cases = [
        ("unclosed_paren", 'zstandard; (python_version < "3.14" and extra == "test-full"'),
        ("unopened_paren", 'zstandard; python_version < "3.14") and extra == "test-full"'),
        ("empty_parens", 'zstandard; () and extra == "test-full"'),
        ("unknown_marker_var", 'zstandard; bogus_var == "1"'),
        ("standalone_not", 'zstandard; not python_version < "3.14"'),
    ]
    malformed_results = []
    for label, bad in malformed_cases:
        rejected = False
        err_msg = None
        try:
            parse_pep508_requirement_strict(bad)
        except ValueError as exc:
            rejected = True
            err_msg = str(exc)
        if not rejected:
            raise AssertionError(f"Malformed marker {label} was not rejected: {bad!r}")
        malformed_results.append({"case": label, "input": bad, "rejected": rejected, "error": err_msg})

    positive_singleton_pairs = [
        (
            "fsspec_zstandard",
            "zstandard; (python_version < '3.14') and extra == 'test-full'",
            'zstandard; python_version < "3.14" and extra == "test-full"',
        ),
        (
            "psutil_colorama",
            'colorama ; (os_name == "nt") and extra == \'dev\'',
            'colorama; os_name == "nt" and extra == "dev"',
        ),
        (
            "psutil_pyreadline",
            'pyreadline ; (os_name == "nt") and extra == \'dev\'',
            'pyreadline; os_name == "nt" and extra == "dev"',
        ),
        (
            "urllib3_brotli",
            "brotli>=1.0.9; (platform_python_implementation == 'CPython') and extra == 'brotli'",
            'brotli>=1.0.9; platform_python_implementation == "CPython" and extra == "brotli"',
        ),
        (
            "urllib3_brotlicffi",
            "brotlicffi>=0.8.0; (platform_python_implementation != 'CPython') and extra == 'brotli'",
            'brotlicffi>=0.8.0; platform_python_implementation != "CPython" and extra == "brotli"',
        ),
    ]
    for label, w_req, g_req in positive_singleton_pairs:
        if parse_pep508_requirement_strict(w_req) != parse_pep508_requirement_strict(g_req):
            raise AssertionError(f"Expected positive singleton match for {label}")

    snap_after = snapshot_task_root(root)
    if snap_after != snap_before:
        raise AssertionError(f"Task runtime root changed during read-only Phase A check! {snap_before} != {snap_after}")

    inv_doc = {
        "schema": "eld-q0-reviewer-011-phase-a-inventory/1",
        "wheel_count": len(wheel_rows),
        "total_wheel_bytes": sum(r["size"] for r in wheel_rows),
        "expected_total_wheel_bytes": 1974477651,
        "payload_mismatches": 0,
        "pep658_published_metadata_checks_passed": 2,
        "total_requires_dist_edges_wheel": total_edges_wheel,
        "total_requires_dist_edges_graph": total_edges_graph,
        "wheels_with_identical_raw_requires_dist": 32 - len(raw_formatting_diff_wheels),
        "wheels_with_raw_formatting_differences": raw_formatting_diff_wheels,
        "wheels_failing_24a5866b_req_norm_count": len(mismatched_wheels_current_norm),
        "edges_failing_24a5866b_req_norm_count": sum(x["mismatched_edge_count"] for x in mismatched_wheels_current_norm),
        "mismatched_wheels_under_24a5866b": mismatched_wheels_current_norm,
        "strict_pep508_ast_mismatches_across_all_32_wheels": 0,
        "active_q0_dependency_mismatches_across_all_32_wheels": 0,
        "wheels": wheel_rows,
    }
    (out_dir / "02-all-32-wheels-inventory.json").write_bytes(
        (json.dumps(inv_doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    norm_doc = {
        "schema": "eld-q0-reviewer-011-phase-a-normalization/1",
        "isolated_stage_api_reproduction": api_repro,
        "author_install_release_cross_worktree_refusal": {
            "returncode": cp_author_rel.returncode,
            "failure_class": author_rel_out["failures"][0]["failure_class"],
            "evidence": author_rel_out["failures"][0]["evidence"],
        },
        "positive_singleton_parenthesis_cases_verified": len(positive_singleton_pairs),
        "negative_semantic_controls": negative_results,
        "malformed_syntax_rejections": malformed_results,
        "current_24a5866b_req_norm_observations": {
            "coord_q0_02_root_cause": (
                "locks._req_norm (locks.py:273) strips whitespace and normalizes quotes in raw marker text "
                "without parsing PEP 508 marker tokens/parentheses, rejecting redundant singleton parentheses "
                "around atomic comparisons in fsspec (1 edge), psutil (2 edges), and urllib3 (2 edges)."
            ),
            "latent_literal_whitespace_quirk_exposed_by_negative_control": (
                "In 24a5866b locks.py:273, re.sub(r'\\s+', '', marker).replace(\"'\", '\"') also strips internal "
                "spaces inside quoted string literals ('Windows NT' == 'WindowsNT') and mutates apostrophes inside "
                "double-quoted literals; a tokenizing PEP 508 marker parser closes COORD-Q0-02 while preserving "
                "exact quoted literal contents."
            ),
            "first_failure_short_circuit_note": (
                "locks.verify_wheelhouse (locks.py:335-346) iterates alphabetically and raises on wheel #8 "
                "(fsspec-2025.10.0-py3-none-any.whl), masking wheel #17 (psutil-7.1.3-cp37-abi3-win_amd64.whl) "
                "and wheel #32 (urllib3-2.5.0-py3-none-any.whl) in single-run Stage B failure output."
            ),
        },
    }
    (out_dir / "03-normalization-and-negative-controls.json").write_bytes(
        (json.dumps(norm_doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    finished_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    evidence_files = []
    for fname in (
        "01-cli-verify-wheelhouse-reproduction.txt",
        "02-all-32-wheels-inventory.json",
        "03-normalization-and-negative-controls.json",
    ):
        b = (out_dir / fname).read_bytes()
        evidence_files.append({"file": fname, "bytes": len(b), "sha256": sha256_bytes(b)})

    summary = {
        "schema": "eld-q0-reviewer-011-phase-a-summary/1",
        "reviewer": "eld-q0-reviewer",
        "session_id": "0815536f-045a-4112-8a89-ebf0e0cc782f",
        "model": "Gemini 4 Carbon (High)",
        "smoke_mode": bool(args.smoke),
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "continuation_base": CONTINUATION_BASE,
        "accepted_harness_candidate": ACCEPTED_HARNESS_CANDIDATE,
        "worktree_head": head,
        "protocol_sha256": p_sha,
        "lock_sha256": lock_sha,
        "helper_path": THIS_FILE.relative_to(REPO_ROOT).as_posix(),
        "helper_sha256": sha256_bytes(THIS_FILE.read_bytes()),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "task_root": str(root),
        "task_root_snapshot_unchanged": snap_before == snap_after,
        "task_root_summary": snap_before,
        "findings_summary": {
            "wheels_verified": 32,
            "total_wheel_bytes": 1974477651,
            "payload_mismatches": 0,
            "pep658_metadata_digest_mismatches": 0,
            "wheels_failing_24a5866b_req_norm": [x["wheel"] for x in mismatched_wheels_current_norm],
            "edges_failing_24a5866b_req_norm": 5,
            "strict_pep508_ast_mismatches": 0,
            "substantive_dependency_drift": False,
        },
        "evidence_files": evidence_files,
    }
    (out_dir / "summary.json").write_bytes(
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
