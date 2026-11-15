"""WP-0005 /011 Phase B independent read-only verification helper for COORD-Q0-02 (/010).

Author: eld-q0-reviewer (Gemini 4 Carbon High, session 0815536f-045a-4112-8a89-ebf0e0cc782f)
Target candidate: 41d6204648e4115ab197507d1a22f6d5c7f3e784 (parent 68855420b2dece941eb90c42c69de3c80b47aa06)

Read-only verification only:
- Never modifies, extracts, installs, or imports any downloaded package.
- Never writes to C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005 (verified by pre/post snapshots).
- Any transient .scratch release JSON used to probe q0.py verify-wheelhouse is an explicitly
  labeled READ-ONLY TEST FIXTURE ONLY, never coordinator installation or execution authority.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REVIEWER_WT = Path(__file__).resolve().parents[6]
HARNESS_DIR = REVIEWER_WT / "qualification" / "q0" / "harness"
MAIN_REPO = Path(r"C:\Users\jackg\Asp.net Projects\eledgercare")
TASK_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
WHEELHOUSE = TASK_ROOT / "wheelhouse"
AUTHOR_INSTALL_REL = MAIN_REPO / "docs" / "coordination" / "WP-0005" / "releases" / "author-install.json"

CANDIDATE_SHA = "41d6204648e4115ab197507d1a22f6d5c7f3e784"
AUTHOR_010_EVIDENCE_SHA = "6dc2d01c84da99d751994cce00a2c82df053c215"
AUTHOR_010_REPORT_SHA = "099a2fa74cdc2df6068c437edf3971eb37e9f07d"
PARENT_STOP_SHA = "68855420b2dece941eb90c42c69de3c80b47aa06"
ACCEPTED_008_SHA = "24a5866b505532fd03e7db62a4e57875e4c5a170"
PHASE_A_HELPER_SHA = "60a5e381703a0a723d8bc11b21fd2ed57807c87f"
PHASE_A_EVIDENCE_SHA = "d211741bce3a341df70402679b4342b6aadb0ab3"

EXPECTED_IMMUTABLE_SHA256 = {
    "qualification/q0/harness/protocol.json": "dd8a7dc38c2a0c46103f6667f522656a2dddf5882727c18bf7b6b5426c5e2309",
    "qualification/q0/harness/locks/dependency-lock.json": "d8eeaf0fe838d9df5728f17fcbacc8b504d98b79644a524b4faa705d97c49e6e",
    "qualification/q0/harness/manifests/model-files.json": "085ac7ba1e25a7300846de18bdac19c7f9612bf417041643beff6a9cab6b8ea8",
    "docs/reviews/WP-0005/eld-q0-reviewer/metadata-correction/diagnose_wheel_metadata_phase_a.py":
        "d7cf9f4f4d197291232fa0b20427d794bff050e2292f20bd775e8b3b2a4aa4a1",
}

if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

from q0harness import locks  # noqa: E402
from q0harness.environment import build_stage_env  # noqa: E402
from q0harness.hashing import sha256_bytes  # noqa: E402
from q0harness.outcome import Q0Failure  # noqa: E402
from q0harness.protocol import load_protocol  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_out(*args: str) -> str:
    cp = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(REVIEWER_WT), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
    )
    return cp.stdout.strip()


def snapshot_task_root(root: Path) -> dict:
    subdirs = {}
    all_entries = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        files = []
        total = 0
        reparse = 0
        for dirpath, dirnames, filenames in os.walk(child):
            dp = Path(dirpath)
            if dp.is_symlink() or (hasattr(os.stat_result, "st_reparse_tag") and dp.lstat().st_reparse_tag != 0):
                reparse += 1
            for fn in sorted(filenames):
                fp = dp / fn
                st = fp.lstat()
                if getattr(st, "st_reparse_tag", 0) != 0:
                    reparse += 1
                rel = fp.relative_to(root).as_posix()
                files.append(f"{rel}|{st.st_size}|{st.st_mtime_ns}")
                total += st.st_size
                all_entries.append(f"{rel}|{st.st_size}|{st.st_mtime_ns}")
        subdirs[child.name] = {
            "file_count": len(files),
            "total_bytes": total,
            "reparse_points": reparse,
            "stat_sha256": sha256_bytes("\n".join(files).encode("utf-8")),
        }
    wh_entries = [
        f"{p.name}|{p.stat().st_size}|{p.stat().st_mtime_ns}"
        for p in sorted(WHEELHOUSE.iterdir(), key=lambda x: x.name)
        if p.is_file()
    ]
    site_pkgs = root / "venv" / "Lib" / "site-packages"
    dist_infos = sorted(p.name for p in site_pkgs.glob("*.dist-info")) if site_pkgs.is_dir() else []
    return {
        "root": str(root),
        "wheelhouse_whl_stat_fingerprint_sha256": sha256_bytes("\n".join(wh_entries).encode("utf-8")),
        "venv_dist_info": dist_infos,
        "subdirs": subdirs,
        "overall_stat_sha256": sha256_bytes("\n".join(all_entries).encode("utf-8")),
    }


def make_wheel_bytes(dist_info_dir: str, metadata_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{dist_info_dir}/METADATA", metadata_bytes)
    return buf.getvalue()


def read_real_wheel_metadata_bytes(wheel_path: Path) -> tuple[str, bytes]:
    with zipfile.ZipFile(wheel_path, "r") as zf:
        hits = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA") and n.count("/") == 1]
        assert len(hits) == 1, f"Expected 1 METADATA in {wheel_path.name}, got {hits}"
        dist_dir = hits[0].split("/", 1)[0]
        return dist_dir, zf.read(hits[0])


def run_comparator_and_negative_battery(pkgs: dict[str, dict], scratch_dir: Path) -> dict:
    n = locks._req_norm
    mn = locks._marker_norm

    positive_pairs = [
        ("coord_q0_02_fsspec",
         "zstandard; (python_version < '3.14') and extra == 'test-full'",
         'zstandard; python_version < "3.14" and extra == "test-full"'),
        ("coord_q0_02_psutil_colorama",
         'colorama ; (os_name == "nt") and extra == \'dev\'',
         'colorama; os_name == "nt" and extra == "dev"'),
        ("coord_q0_02_psutil_pyreadline",
         'pyreadline ; (os_name == "nt") and extra == \'dev\'',
         'pyreadline; os_name == "nt" and extra == "dev"'),
        ("coord_q0_02_urllib3_brotli",
         "brotli>=1.0.9; (platform_python_implementation == 'CPython') and extra == 'brotli'",
         'brotli>=1.0.9; platform_python_implementation == "CPython" and extra == "brotli"'),
        ("coord_q0_02_urllib3_brotlicffi",
         "brotlicffi>=0.8.0; (platform_python_implementation != 'CPython') and extra == 'brotli'",
         'brotlicffi>=0.8.0; platform_python_implementation != "CPython" and extra == "brotli"'),
        ("psutil_compound_paren_in_and",
         'pywin32; (os_name == "nt" and platform_python_implementation != "PyPy") and extra == "dev"',
         "pywin32; os_name == 'nt' and platform_python_implementation != 'PyPy' and extra == 'dev'"),
        ("nested_singleton_marker_parens",
         "pkg; (((python_version >= '3.12')))",
         'pkg; python_version >= "3.12"'),
        ("outer_compound_marker_parens",
         "pkg; (os_name == 'nt' and extra == 'dev')",
         'pkg; os_name == "nt" and extra == "dev"'),
        ("precedence_or_of_and",
         "pkg; a == '1' or (b == '2' and c == '3')",
         "pkg; a == '1' or b == '2' and c == '3'"),
        ("associative_and",
         "pkg; (a == '1' and b == '2') and c == '3'",
         "pkg; a == '1' and (b == '2' and c == '3')"),
        ("associative_or",
         "pkg; (a == '1' or b == '2') or c == '3'",
         "pkg; a == '1' or (b == '2' or c == '3')"),
        ("not_in_whitespace_collapse",
         "pkg; 'linux' not   in sys_platform",
         'pkg; "linux" not in sys_platform'),
        ("quoted_spaces_and_semicolon",
         "pkg; platform_system == 'Windows NT' and extra == 'a;b'",
         'pkg; platform_system == "Windows NT" and extra == "a;b"'),
        ("legacy_version_parens_and_sort",
         "Pillow ( !=8.3.* , >=5.3.0 )",
         "pillow>=5.3.0,!=8.3.*"),
        ("extras_case_and_sort",
         "Requests[Security, Socks] (>=2.30)",
         "requests[security,socks]>=2.30"),
        ("empty_brackets_vs_no_extras",
         "pkg[]>=1.0",
         "pkg>=1.0"),
    ]
    pos_results = []
    for label, lhs, rhs in positive_pairs:
        nl, nr = n(lhs), n(rhs)
        ok = (not nl.startswith("!unparsed:")) and nl == nr
        assert ok, f"Positive case {label} failed: {nl!r} vs {nr!r}"
        pos_results.append({"case": label, "normalized": nl, "equal": ok})

    negative_pairs = [
        ("or_inside_and_vs_unparenthesized",
         "pkg; (a == '1' or b == '2') and c == '3'",
         "pkg; a == '1' or b == '2' and c == '3'"),
        ("or_inside_and_vs_right_grouped",
         "pkg; (a == '1' or b == '2') and c == '3'",
         "pkg; a == '1' or (b == '2' and c == '3')"),
        ("right_or_inside_and_vs_unparenthesized",
         "pkg; a == '1' and (b == '2' or c == '3')",
         "pkg; a == '1' and b == '2' or c == '3'"),
        ("right_or_inside_and_vs_left_and",
         "pkg; a == '1' and (b == '2' or c == '3')",
         "pkg; (a == '1' and b == '2') or c == '3'"),
        ("two_or_groups_in_and_vs_flat",
         "pkg; (a == '1' or b == '2') and (c == '3' or d == '4')",
         "pkg; a == '1' or b == '2' and c == '3' or d == '4'"),
        ("quoted_internal_space_preserved",
         "pkg; platform_system == 'Windows NT'",
         "pkg; platform_system == 'WindowsNT'"),
        ("quoted_leading_space_preserved",
         "pkg; extra == ' dev'",
         "pkg; extra == 'dev'"),
        ("quoted_parens_preserved",
         "pkg; extra == '(dev)'",
         "pkg; extra == 'dev'"),
        ("quoted_boolean_words_not_parsed",
         "pkg; extra == 'a or b'",
         "pkg; extra == 'a' or extra == 'b'"),
        ("embedded_single_vs_double_quote",
         "pkg; extra == \"'a'\"",
         'pkg; extra == \'"a"\''),
        ("embedded_backslash_preserved",
         r"pkg; extra == 'a\b'",
         "pkg; extra == 'ab'"),
        ("quoted_case_preserved",
         "pkg; platform_python_implementation == 'CPython'",
         "pkg; platform_python_implementation == 'cpython'"),
        ("quoted_string_vs_ident_disjoint",
         "pkg; 'os_name' == 'nt'",
         "pkg; os_name == 'nt'"),
        ("op_lt_vs_le",
         "pkg; python_version < '3.14'",
         "pkg; python_version <= '3.14'"),
        ("op_gt_vs_ge",
         "pkg; python_version > '3.12'",
         "pkg; python_version >= '3.12'"),
        ("op_eq_vs_arbitrary_eq",
         "pkg; python_version == '3.12'",
         "pkg; python_version === '3.12'"),
        ("op_eq_vs_ne",
         "pkg; os_name == 'nt'",
         "pkg; os_name != 'nt'"),
        ("op_compat_vs_ge",
         "pkg; python_version ~= '3.12'",
         "pkg; python_version >= '3.12'"),
        ("op_in_vs_not_in",
         "pkg; 'linux' in sys_platform",
         "pkg; 'linux' not in sys_platform"),
        ("operand_var_change",
         "pkg; python_version < '3.14'",
         "pkg; python_full_version < '3.14'"),
        ("operand_value_change",
         "pkg; python_version < '3.14'",
         "pkg; python_version < '3.13'"),
        ("operand_lhs_rhs_swap",
         "pkg; 'nt' == os_name",
         "pkg; os_name == 'nt'"),
        ("clause_order_and",
         "pkg; a == '1' and b == '2'",
         "pkg; b == '2' and a == '1'"),
        ("duplicate_clause_not_collapsed",
         "pkg; a == '1' and a == '1'",
         "pkg; a == '1'"),
        ("specifier_version_change",
         "torch==2.13.0+cu130",
         "torch==2.13.0"),
        ("extra_present_vs_absent",
         "pkg[dev]>=1.0",
         "pkg>=1.0"),
        ("extra_duplicate_preserved",
         "pkg[dev,dev]>=1.0",
         "pkg[dev]>=1.0"),
        ("extra_marker_value_change",
         "pkg; extra == 'dev'",
         "pkg; extra == 'test'"),
    ]
    neg_results = []
    for label, lhs, rhs in negative_pairs:
        nl, nr = n(lhs), n(rhs)
        distinct = nl != nr
        assert distinct, f"Negative case {label} falsely collapsed: {nl!r}"
        neg_results.append({"case": label, "lhs_norm": nl, "rhs_norm": nr, "distinct": distinct})

    malformed_inputs = [
        "my pkg>=1.0",
        "pkg_>=1.0",
        "pkg.[a]>=1.0",
        "pkg[a][b]>=1.0",
        "pkg[a b]>=1.0",
        "pkg[a,]>=1.0",
        "pkg>=1. 0",
        "pkg>=1.0,",
        "pkg @ https://example.com/pkg-1.0.whl",
        "pkg ()",
        "pkg (==1.0",
        "pkg ==1.0)",
        "pkg (==1.0)(==2.0)",
        "pkg (==1.0), (>=2.0)",
        "pkg;",
        "pkg;   ",
        "pkg; ()",
        "pkg; (os_name == 'nt'",
        "pkg; os_name == 'nt')",
        "pkg; os_name == 'nt",
        "pkg; os_name == 'nt\n'",
        "pkg; not os_name == 'nt'",
        "pkg; 'a' not('b')",
        "pkg; 'a' notin 'b'",
        "pkg; os_name = 'nt'",
        "pkg; python_version < 3.14",
        "pkg; True",
        "pkg; os_name == 'nt' trailing",
        "pkg; " + "(" * 70 + "os_name == 'nt'" + ")" * 70,
    ]
    malformed_results = []
    for bad in malformed_inputs:
        res = n(bad)
        assert res.startswith("!unparsed:"), f"Malformed input did not fail closed: {bad!r} -> {res!r}"
        malformed_results.append({"input": bad[:80], "unparsed": True})

    # Verify idempotence & zero-unparsed across all 850 graph edges and all 850 real wheel lines.
    graph_edge_count = 0
    wheel_edge_count = 0
    marker_idempotent_count = 0
    for _, art in sorted(pkgs.items()):
        for r in art["graph_requires"]:
            nr = n(r)
            assert not nr.startswith("!unparsed:"), f"Graph edge unparsed: {r}"
            graph_edge_count += 1
            _, sep, mk = r.partition(";")
            if sep:
                c1 = mn(mk)
                c2 = mn(c1)
                assert c1 == c2, f"_marker_norm not idempotent: {c1!r} != {c2!r}"
                marker_idempotent_count += 1
        wp = WHEELHOUSE / art["filename"]
        meta = locks.inspect_wheel_metadata(wp, art["name"], art["version"])
        for r in meta["requires_dist"]:
            nr = n(r)
            assert not nr.startswith("!unparsed:"), f"Wheel edge unparsed in {wp.name}: {r}"
            wheel_edge_count += 1
            _, sep, mk = r.partition(";")
            if sep:
                c1 = mn(mk)
                c2 = mn(c1)
                assert c1 == c2, f"_marker_norm not idempotent on wheel marker: {c1!r} != {c2!r}"
                marker_idempotent_count += 1

    # Wheel-level negative controls using real wheel METADATA bytes mutated in memory -> .scratch ZIP.
    wheel_neg_dir = scratch_dir / "wheel-negatives"
    wheel_neg_dir.mkdir(parents=True, exist_ok=True)
    wheel_negatives = []
    try:
        # 1. Drop 1 inactive extra-gated requirement from real fsspec METADATA.
        fs_art = pkgs["fsspec"]
        fs_dist, fs_bytes = read_real_wheel_metadata_bytes(WHEELHOUSE / fs_art["filename"])
        fs_dropped = b"\n".join(
            ln for ln in fs_bytes.splitlines()
            if not ln.startswith(b"Requires-Dist: zstandard;")
        ) + b"\n"
        w1 = wheel_neg_dir / "fsspec-drop-zstandard.whl"
        w1.write_bytes(make_wheel_bytes(fs_dist, fs_dropped))
        try:
            locks.verify_wheel_metadata(w1, fs_art)
            raise AssertionError("Expected Q0Failure on dropped inactive requirement")
        except Q0Failure as exc:
            assert exc.failure_class == "HASH_MISMATCH"
            wheel_negatives.append({"case": "drop_inactive_fsspec_zstandard", "failure_class": exc.failure_class,
                                    "only_in_graph": exc.evidence.get("only_in_graph")})

        # 2. Duplicate 1 requirement in real urllib3 METADATA (multiset check).
        u3_art = pkgs["urllib3"]
        u3_dist, u3_bytes = read_real_wheel_metadata_bytes(WHEELHOUSE / u3_art["filename"])
        u3_dup = u3_bytes.replace(
            b"Requires-Dist: brotli>=1.0.9;",
            b"Requires-Dist: brotli>=1.0.9; (platform_python_implementation == 'CPython') and extra == 'brotli'\r\n"
            b"Requires-Dist: brotli>=1.0.9;",
            1,
        )
        w2 = wheel_neg_dir / "urllib3-duplicate-edge.whl"
        w2.write_bytes(make_wheel_bytes(u3_dist, u3_dup))
        try:
            locks.verify_wheel_metadata(w2, u3_art)
            raise AssertionError("Expected Q0Failure on duplicate requirement")
        except Q0Failure as exc:
            assert exc.failure_class == "HASH_MISMATCH"
            wheel_negatives.append({"case": "duplicate_urllib3_brotli_edge", "failure_class": exc.failure_class,
                                    "only_in_wheel": exc.evidence.get("only_in_wheel")})

        # 3. Strip meaningful OR-inside-AND parentheses in real pillow METADATA.
        pil_art = pkgs["pillow"]
        pil_dist, pil_bytes = read_real_wheel_metadata_bytes(WHEELHOUSE / pil_art["filename"])
        target_pil = b'Requires-Dist: psutil; (sys_platform == "linux" or sys_platform == "darwin") and extra == "tests"'
        assert target_pil in pil_bytes, "Expected psutil OR-inside-AND marker in pillow METADATA"
        pil_bad = pil_bytes.replace(
            target_pil,
            b'Requires-Dist: psutil; sys_platform == "linux" or sys_platform == "darwin" and extra == "tests"',
            1,
        )
        w3 = wheel_neg_dir / "pillow-stripped-or-parens.whl"
        w3.write_bytes(make_wheel_bytes(pil_dist, pil_bad))
        try:
            locks.verify_wheel_metadata(w3, pil_art)
            raise AssertionError("Expected Q0Failure on stripped OR-inside-AND parentheses in pillow")
        except Q0Failure as exc:
            assert exc.failure_class == "HASH_MISMATCH"
            wheel_negatives.append({"case": "strip_meaningful_or_parens_pillow", "failure_class": exc.failure_class,
                                    "only_in_wheel": exc.evidence.get("only_in_wheel"),
                                    "only_in_graph": exc.evidence.get("only_in_graph")})

        # 4. Alter quoted literal content in real urllib3 METADATA ('CPython' -> 'cpython').
        u3_case = u3_bytes.replace(b"'CPython'", b"'cpython'", 1)
        w4 = wheel_neg_dir / "urllib3-altered-quote-case.whl"
        w4.write_bytes(make_wheel_bytes(u3_dist, u3_case))
        try:
            locks.verify_wheel_metadata(w4, u3_art)
            raise AssertionError("Expected Q0Failure on altered quoted literal case")
        except Q0Failure as exc:
            assert exc.failure_class == "HASH_MISMATCH"
            wheel_negatives.append({"case": "altered_quoted_literal_case_urllib3", "failure_class": exc.failure_class,
                                    "only_in_wheel": exc.evidence.get("only_in_wheel")})

        # 5. Append trailing newline to real torch METADATA (PEP 658 digest mismatch despite identical headers).
        tc_art = pkgs["torch"]
        tc_dist, tc_bytes = read_real_wheel_metadata_bytes(WHEELHOUSE / tc_art["filename"])
        w5 = wheel_neg_dir / "torch-pep658-byte-tamper.whl"
        w5.write_bytes(make_wheel_bytes(tc_dist, tc_bytes + b"\n"))
        try:
            locks.verify_wheel_metadata(w5, tc_art)
            raise AssertionError("Expected Q0Failure on PEP 658 byte tamper")
        except Q0Failure as exc:
            assert exc.failure_class == "HASH_MISMATCH"
            assert exc.evidence.get("requires_match") is True
            assert exc.evidence.get("published_metadata_sha256_match") is False
            wheel_negatives.append({"case": "torch_pep658_byte_tamper", "failure_class": exc.failure_class,
                                    "requires_match": exc.evidence.get("requires_match"),
                                    "published_metadata_sha256_match": exc.evidence.get("published_metadata_sha256_match")})

        # 6. Identical unparseable Requires-Dist on BOTH wheel and graph sides MUST still fail closed.
        bad_art = {"name": "badpkg", "version": "1.0", "graph_requires": ["dep; (os_name == 'nt'"]}
        bad_meta = b"Metadata-Version: 2.1\nName: badpkg\nVersion: 1.0\nRequires-Dist: dep; (os_name == 'nt'\n\n"
        w6 = wheel_neg_dir / "badpkg-unparsed-both-sides.whl"
        w6.write_bytes(make_wheel_bytes("badpkg-1.0.dist-info", bad_meta))
        try:
            locks.verify_wheel_metadata(w6, bad_art)
            raise AssertionError("Expected Q0Failure on identical unparseable Requires-Dist")
        except Q0Failure as exc:
            assert exc.failure_class == "HASH_MISMATCH"
            assert "unparsed_requires" in exc.evidence
            wheel_negatives.append({"case": "unparsed_identical_both_sides", "failure_class": exc.failure_class,
                                    "unparsed_requires_count": len(exc.evidence["unparsed_requires"])})
    finally:
        shutil.rmtree(wheel_neg_dir, ignore_errors=True)

    return {
        "positive_cases_passed": len(pos_results),
        "positive_cases": pos_results,
        "negative_cases_rejected": len(neg_results),
        "negative_cases": neg_results,
        "malformed_cases_unparsed": len(malformed_results),
        "malformed_cases": malformed_results,
        "graph_edges_parsed_cleanly": graph_edge_count,
        "wheel_edges_parsed_cleanly": wheel_edge_count,
        "marker_idempotence_verified": marker_idempotent_count,
        "wheel_negative_controls_rejected": len(wheel_negatives),
        "wheel_negative_controls": wheel_negatives,
    }


def run_isolated_stage_checks(protocol: dict, protocol_sha: str, lock_sha: str, head_sha: str,
                              scratch_dir: Path) -> tuple[str, dict]:
    # 1. Targeted unit/regression suites under scratch stage_offline environment.
    scratch_stage_root = scratch_dir / "stage-offline-unit-root"
    for sub in protocol["storage"]["subdirs"].values():
        if isinstance(sub, str):
            (scratch_stage_root / sub).mkdir(parents=True, exist_ok=True)
    unit_env = build_stage_env(os.environ, root=scratch_stage_root, protocol=protocol, network=False)
    outside_cwd = scratch_dir / "outside-cwd"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    unit_cmds = [
        [sys.executable, "-I", "-B", "-m", "unittest", "discover",
         "-s", str(HARNESS_DIR / "tests"), "-t", str(HARNESS_DIR / "tests"),
         "-p", "test_locks_preflight.py", "-v"],
        [sys.executable, "-I", "-B", "-m", "unittest", "discover",
         "-s", str(HARNESS_DIR / "tests"), "-t", str(HARNESS_DIR / "tests"),
         "-p", "test_isolated_git_subprocess.py", "-v"],
    ]
    unit_log_parts = []
    for cmd in unit_cmds:
        cp = subprocess.run(cmd, cwd=str(outside_cwd), env=unit_env,
                            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        unit_log_parts.append(f"$ {' '.join(cmd)}\nexit_code={cp.returncode}\n{cp.stdout}{cp.stderr}\n")
        if cp.returncode != 0:
            raise RuntimeError(f"Targeted unittest failed ({cp.returncode}):\n{cp.stdout}\n{cp.stderr}")
    unit_text = "".join(unit_log_parts)

    # 2. Real all-32-wheel verification in separate child processes:
    #    (a) task venv python (-s -B -P -X utf8) under build_stage_env(root=TASK_ROOT, network=False)
    #    (b) host stdlib python (-I -B)
    real_stage_env = build_stage_env(os.environ, root=TASK_ROOT, protocol=protocol, network=False)
    venv_py = TASK_ROOT / "venv" / "Scripts" / "python.exe"
    child_code = """
import json, os, shutil, sys
from pathlib import Path
harness_dir = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
wheelhouse = Path(sys.argv[3])
sys.path.insert(0, str(harness_dir))
from q0harness import locks
lock = json.loads((harness_dir / "locks" / "dependency-lock.json").read_text(encoding="utf-8"))
pkgs = locks.validate_lock(lock, locks.git_blob_reader(repo_root))
rep = locks.verify_wheelhouse(pkgs, wheelhouse, lock)
heavy = [m for m in ("torch", "transformers", "pypdfium2", "PIL", "fsspec", "psutil", "urllib3") if m in sys.modules]
out = {
    "executable": sys.executable,
    "cwd": os.getcwd(),
    "git_on_path": shutil.which("git", path=os.environ.get("PATH", "")),
    "q0_git_executable": os.environ.get("Q0_GIT_EXECUTABLE"),
    "pip_no_index": os.environ.get("PIP_NO_INDEX"),
    "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
    "transformers_offline": os.environ.get("TRANSFORMERS_OFFLINE"),
    "heavy_or_wheel_modules_imported": heavy,
    "metadata_checked": rep["metadata_checked"],
    "total_payload_bytes": sum(w["size"] for w in rep["wheels"]),
    "total_requires_dist": sum(w["metadata"]["requires_dist"] for w in rep["wheels"]),
    "total_graph_requires": sum(w["metadata"]["graph_requires"] for w in rep["wheels"]),
    "all_payload_ok": all(w["payload_ok"] for w in rep["wheels"]),
    "all_metadata_ok": all(w["metadata"]["ok"] for w in rep["wheels"]),
    "any_unparsed": any("unparsed_requires" in w["metadata"] for w in rep["wheels"]),
    "pep658_matches": {
        w["wheel"]: w["metadata"]["published_metadata_sha256_match"]
        for w in rep["wheels"]
        if w["metadata"]["published_metadata_sha256_match"] is not None
    },
    "previously_failing_coord_q0_02_wheels": [
        w for w in rep["wheels"]
        if w["wheel"].startswith(("fsspec-", "psutil-", "urllib3-"))
    ],
    "wheels": rep["wheels"],
}
print(json.dumps(out))
"""
    cp_wh = subprocess.run(
        [str(venv_py), "-s", "-B", "-P", "-X", "utf8", "-c", child_code,
         str(HARNESS_DIR), str(REVIEWER_WT), str(WHEELHOUSE)],
        cwd=str(outside_cwd),
        env=real_stage_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if cp_wh.returncode != 0:
        raise RuntimeError(f"Child stage_offline verify_wheelhouse failed ({cp_wh.returncode}):\n{cp_wh.stdout}\n{cp_wh.stderr}")
    direct_wh_result = json.loads(cp_wh.stdout)
    assert direct_wh_result["git_on_path"] is None
    assert direct_wh_result["metadata_checked"] == 32
    assert direct_wh_result["total_payload_bytes"] == 1974477651
    assert direct_wh_result["total_requires_dist"] == 850
    assert direct_wh_result["total_graph_requires"] == 850
    assert direct_wh_result["all_payload_ok"] is True
    assert direct_wh_result["all_metadata_ok"] is True
    assert direct_wh_result["any_unparsed"] is False
    assert direct_wh_result["heavy_or_wheel_modules_imported"] == []
    assert all(v is True for v in direct_wh_result["pep658_matches"].values())
    assert len(direct_wh_result["pep658_matches"]) == 2

    cp_wh_host = subprocess.run(
        [sys.executable, "-I", "-B", "-c", child_code,
         str(HARNESS_DIR), str(REVIEWER_WT), str(WHEELHOUSE)],
        cwd=str(outside_cwd),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if cp_wh_host.returncode != 0:
        raise RuntimeError(f"Host stdlib verify_wheelhouse failed ({cp_wh_host.returncode}):\n{cp_wh_host.stdout}\n{cp_wh_host.stderr}")
    host_wh_result = json.loads(cp_wh_host.stdout)
    assert host_wh_result["metadata_checked"] == 32
    assert host_wh_result["all_payload_ok"] is True
    assert host_wh_result["all_metadata_ok"] is True
    assert host_wh_result["wheels"] == direct_wh_result["wheels"]

    # 3. CLI probes under real_stage_env:
    #    (a) lock-check (exit 0)
    #    (b) verify-wheelhouse with main author-install.json (must fail closed on reviewer HEAD: exit 2)
    #    (c) verify-wheelhouse with transient .scratch TEST FIXTURE ONLY release JSON (must pass: exit 0)
    q0_py = HARNESS_DIR / "q0.py"
    cp_lc = subprocess.run(
        [str(venv_py), "-s", "-B", str(q0_py), "lock-check"],
        cwd=str(outside_cwd),
        env=real_stage_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp_lc.returncode == 0, cp_lc.stderr
    lc_json = json.loads(cp_lc.stdout)
    assert lc_json["readiness"]["installable"] is True

    cp_refuse = subprocess.run(
        [str(venv_py), "-s", "-B", str(q0_py), "verify-wheelhouse", str(WHEELHOUSE),
         "--release", str(AUTHOR_INSTALL_REL)],
        cwd=str(outside_cwd),
        env=real_stage_env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp_refuse.returncode == 2, f"Expected exit 2 refusing author release on reviewer HEAD, got {cp_refuse.returncode}"
    refuse_json = json.loads(cp_refuse.stdout)
    assert refuse_json["failures"][0]["failure_class"] == "EXECUTION_NOT_RELEASED"

    fixture_rel_path = scratch_dir / "readonly-cli-probe-test-fixture-release.json"
    cli_probe_summary = None
    try:
        fixture_rel = {
            "_test_fixture_only": True,
            "_test_fixture_disclaimer": (
                "SYNTHETIC READ-ONLY REVIEWER CLI PROBE TEST FIXTURE ONLY — "
                "NEVER COORDINATOR INSTALLATION OR EXECUTION RELEASE AUTHORITY"
            ),
            "schema": "eldq0-release/2",
            "packet": "WP-0005",
            "stage": "install",
            "released_by": "eld-coordinator",
            "release_commit": "136200bc60e11f50ab0fc3961401aa1eb63a40f7",
            "accepted_review": {
                "reviewer": "eld-q0-reviewer",
                "evidence_commit": "6e12e55ce53827f7386889c945c33d524c92658f",
                "report_commit": "af81c9c67ddb4fb233cc93525481c4219d244f53",
            },
            "harness_commit": head_sha,
            "protocol_sha256": protocol_sha,
            "lock_sha256": lock_sha,
            "accepted_provenance_exceptions": ["torchvision-local-sha256-TOFU"],
            "storage_root": str(TASK_ROOT),
        }
        fixture_rel_path.write_text(json.dumps(fixture_rel, indent=2), encoding="utf-8")
        cp_cli_ok = subprocess.run(
            [str(venv_py), "-s", "-B", str(q0_py), "verify-wheelhouse", str(WHEELHOUSE),
             "--release", str(fixture_rel_path)],
            cwd=str(outside_cwd),
            env=real_stage_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if cp_cli_ok.returncode != 0:
            raise RuntimeError(f"CLI verify-wheelhouse test-fixture probe failed ({cp_cli_ok.returncode}):\n{cp_cli_ok.stdout}\n{cp_cli_ok.stderr}")
        cli_wh_json = json.loads(cp_cli_ok.stdout)
        assert cli_wh_json["metadata_checked"] == 32
        cli_probe_summary = {
            "test_fixture_only": True,
            "disclaimer": fixture_rel["_test_fixture_disclaimer"],
            "fixture_deleted_after_probe": True,
            "exit_code": cp_cli_ok.returncode,
            "output_bytes": len(cp_cli_ok.stdout.encode("utf-8")),
            "output_sha256": sha256_bytes(cp_cli_ok.stdout.encode("utf-8")),
            "metadata_checked": cli_wh_json["metadata_checked"],
            "all_32_payload_and_metadata_ok": all(
                w["payload_ok"] and w["metadata"]["ok"] for w in cli_wh_json["wheels"]
            ),
        }
    finally:
        fixture_rel_path.unlink(missing_ok=True)
    assert not fixture_rel_path.exists()

    return unit_text, {
        "direct_verify_wheelhouse_stage_offline": direct_wh_result,
        "direct_verify_wheelhouse_stdlib_host_matches_stage_offline": {
            "executable": host_wh_result["executable"],
            "metadata_checked": host_wh_result["metadata_checked"],
            "identical_32_wheel_rows": host_wh_result["wheels"] == direct_wh_result["wheels"],
        },
        "cli_lock_check": {
            "exit_code": cp_lc.returncode,
            "artifacts": lc_json["artifacts"],
            "readiness": lc_json["readiness"],
        },
        "cli_author_release_refusal_on_reviewer_head": {
            "exit_code": cp_refuse.returncode,
            "status": refuse_json["status"],
            "failure": refuse_json["failures"][0],
        },
        "cli_verify_wheelhouse_with_transient_scratch_test_fixture": cli_probe_summary,
    }


def verify_published_author_evidence() -> dict:
    ev_diff = git_out("diff", "--name-only", f"{CANDIDATE_SHA}..{AUTHOR_010_EVIDENCE_SHA}").splitlines()
    assert len(ev_diff) == 12 and all(
        p.startswith("qualification/q0/harness/evidence/010-metadata-normalization/") for p in ev_diff
    ), f"Unexpected /010 evidence diff: {ev_diff}"
    rep_diff = git_out("diff", "--name-only", f"{AUTHOR_010_EVIDENCE_SHA}..{AUTHOR_010_REPORT_SHA}").splitlines()
    assert rep_diff == ["docs/agent-reports/eld-q0-harness/WP-0005/010_2026-11-15_implementation_eld-q0-harness.md"], rep_diff

    ev010_dir = HARNESS_DIR / "evidence" / "010-metadata-normalization"
    sum010 = json.loads((ev010_dir / "41d62046" / "summary.json").read_bytes())
    assert sum010["candidate"] == CANDIDATE_SHA
    assert sum010["status"] == "pass"
    for key in ("runner_script", "wheel_verifier_script"):
        rec = sum010[key]
        fp = ev010_dir / rec["name"]
        raw = fp.read_bytes()
        assert len(raw) == rec["size"], f"{rec['name']} size mismatch"
        assert sha256_bytes(raw) == rec["sha256"], f"{rec['name']} sha256 mismatch"
    for step in sum010["steps"]:
        fp = ev010_dir / "41d62046" / step["output"]
        raw = fp.read_bytes()
        assert len(raw) == step["output_bytes"], f"{step['output']} size mismatch"
        assert sha256_bytes(raw) == step["output_sha256"], f"{step['output']} sha256 mismatch"
        assert step["exit_code"] == step["expected_exit_code"]

    ev004_dir = HARNESS_DIR / "evidence" / "004-stage-b-stop"
    sum004 = json.loads((ev004_dir / "460e1d81" / "summary.json").read_bytes())
    for key in ("wrapper_script", "wheel_worker_script"):
        rec = sum004[key]
        fp = ev004_dir / rec["name"]
        raw = fp.read_bytes()
        assert len(raw) == rec["size"] and sha256_bytes(raw) == rec["sha256"]
    for step in sum004["steps"]:
        fp = ev004_dir / "460e1d81" / step["output"]
        raw = fp.read_bytes()
        assert len(raw) == step["output_bytes"] and sha256_bytes(raw) == step["output_sha256"]

    return {
        "author_010_evidence_sha": AUTHOR_010_EVIDENCE_SHA,
        "author_010_report_sha": AUTHOR_010_REPORT_SHA,
        "evidence_010_files_added": len(ev_diff),
        "report_010_files_added": len(rep_diff),
        "verified_010_scripts": 2,
        "verified_010_step_outputs": len(sum010["steps"]),
        "verified_004_stop_scripts": 2,
        "verified_004_stop_step_outputs": len(sum004["steps"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    started_utc = datetime.now(timezone.utc).isoformat()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    head_sha = git_out("rev-parse", "HEAD")
    branch = git_out("rev-parse", "--abbrev-ref", "HEAD")
    status_porcelain = git_out("status", "--porcelain=v1")
    if not args.smoke and status_porcelain != "":
        raise RuntimeError(f"Decisive run requires clean reviewer worktree, got:\n{status_porcelain}")

    # Verify candidate diff scope and exact merge equivalence of core source/tests/docs.
    cand_diff = git_out("diff", "--name-status", f"{PARENT_STOP_SHA}..{CANDIDATE_SHA}").splitlines()
    expected_cand_diff = [
        "M\tqualification/q0/harness/README.md",
        "M\tqualification/q0/harness/q0harness/locks.py",
        "M\tqualification/q0/harness/tests/test_locks_preflight.py",
    ]
    assert sorted(cand_diff) == sorted(expected_cand_diff), f"Unexpected candidate diff: {cand_diff}"
    core_drift = git_out(
        "diff", "--name-only", f"{CANDIDATE_SHA}..HEAD", "--",
        "qualification/q0/harness/q0harness",
        "qualification/q0/harness/q0.py",
        "qualification/q0/harness/protocol.json",
        "qualification/q0/harness/locks",
        "qualification/q0/harness/manifests",
        "qualification/q0/harness/tests",
        "qualification/q0/harness/README.md",
        "research",
        "evaluation",
    )
    assert core_drift == "", f"Reviewer branch differs from candidate in core paths: {core_drift}"
    post_author_drift = git_out(
        "diff", "--name-only", f"{AUTHOR_010_REPORT_SHA}..HEAD", "--",
        "qualification/q0/harness", "research", "evaluation",
    )
    assert post_author_drift == "", f"Harness/research/evaluation drifted after /010 merge: {post_author_drift}"
    preflight_drift = git_out("diff", "--name-only", f"{PHASE_A_EVIDENCE_SHA}..HEAD", "--",
                              "qualification/q0/preflight", "research", "evaluation")
    assert preflight_drift == "", f"Preflight/research/evaluation drifted since Phase A: {preflight_drift}"

    author_pub_audit = verify_published_author_evidence()

    immutable_checks = {}
    for rel, want_sha in EXPECTED_IMMUTABLE_SHA256.items():
        got_sha = sha256_file(REVIEWER_WT / rel)
        assert got_sha == want_sha, f"Immutable file {rel} changed: {got_sha} != {want_sha}"
        immutable_checks[rel] = {"sha256": got_sha, "matches_expected": True}

    snap_before = snapshot_task_root(TASK_ROOT)
    assert snap_before["subdirs"]["wheelhouse"]["file_count"] == 32
    assert snap_before["subdirs"]["wheelhouse"]["total_bytes"] == 1974477651
    assert snap_before["venv_dist_info"] == ["pip-25.0.1.dist-info"]

    protocol, protocol_sha = load_protocol()
    lock_raw = (HARNESS_DIR / "locks" / "dependency-lock.json").read_bytes()
    lock_sha = sha256_bytes(lock_raw)
    lock = json.loads(lock_raw)
    pkgs = locks.validate_lock(lock, locks.git_blob_reader(REVIEWER_WT))

    scratch_run = REVIEWER_WT / ".scratch" / "phase-b-verify-work"
    shutil.rmtree(scratch_run, ignore_errors=True)
    scratch_run.mkdir(parents=True, exist_ok=True)
    try:
        battery = run_comparator_and_negative_battery(pkgs, scratch_run)
        unit_text, stage_checks = run_isolated_stage_checks(
            protocol, protocol_sha, lock_sha, head_sha, scratch_run
        )
    finally:
        shutil.rmtree(scratch_run, ignore_errors=True)

    snap_after = snapshot_task_root(TASK_ROOT)
    assert snap_before == snap_after, "Task runtime root mutated during read-only Phase B checks!"

    f1 = out_dir / "01-targeted-lock-unittests.txt"
    f2 = out_dir / "02-comparator-and-negative-battery.json"
    f3 = out_dir / "03-isolated-all-32-wheel-verification.json"
    f1.write_bytes(unit_text.encode("utf-8"))
    f2.write_bytes((json.dumps(battery, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    f3.write_bytes((json.dumps(stage_checks, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    outputs_meta = {}
    for fp in (f1, f2, f3):
        raw = fp.read_bytes()
        outputs_meta[fp.name] = {"bytes": len(raw), "sha256": sha256_bytes(raw)}

    summary = {
        "schema": "eld-q0-reviewer-011-phase-b/1",
        "smoke_mode": args.smoke,
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer_role": "eld-q0-reviewer",
        "reviewer_session_id": "0815536f-045a-4112-8a89-ebf0e0cc782f",
        "reviewer_model": "gemini-4-carbon-high",
        "reviewer_branch": branch,
        "reviewer_head": head_sha,
        "reviewer_worktree_clean": status_porcelain == "",
        "reviewed_candidate_sha": CANDIDATE_SHA,
        "reviewed_author_010_evidence_sha": AUTHOR_010_EVIDENCE_SHA,
        "reviewed_author_010_report_sha": AUTHOR_010_REPORT_SHA,
        "reviewed_candidate_parent_sha": PARENT_STOP_SHA,
        "accepted_008_baseline_sha": ACCEPTED_008_SHA,
        "phase_a_helper_sha": PHASE_A_HELPER_SHA,
        "phase_a_checkpoint_sha": PHASE_A_EVIDENCE_SHA,
        "candidate_diff_name_status": cand_diff,
        "author_publication_audit": author_pub_audit,
        "helper_path": str(Path(__file__).relative_to(REVIEWER_WT).as_posix()),
        "helper_bytes": Path(__file__).stat().st_size,
        "helper_sha256": sha256_file(Path(__file__)),
        "immutable_pins": immutable_checks,
        "task_root_before": snap_before,
        "task_root_after": snap_after,
        "task_root_unchanged": snap_before == snap_after,
        "all_32_wheels_verified": True,
        "total_wheel_bytes": 1974477651,
        "total_edges_verified": 850,
        "positive_cases_passed": battery["positive_cases_passed"],
        "negative_cases_rejected": battery["negative_cases_rejected"],
        "malformed_cases_unparsed": battery["malformed_cases_unparsed"],
        "wheel_negative_controls_rejected": battery["wheel_negative_controls_rejected"],
        "outputs": outputs_meta,
    }
    (out_dir / "summary.json").write_bytes((json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
