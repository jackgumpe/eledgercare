"""Reconciled independent reviewer rehearsal & guard helper v4 for WP-0012 (`eld-f4-reviewer`).

Preserves `v3` (`docs/reviews/WP-0012/eld-f4-reviewer/author-001-review/helpers/run_wp0012_reviewer_rehearsal_v3.py`,
frozen at `0cabb137e71454d13342148a5652a5034df018ba`) untouched while reconciling the two additional
sequence & failed-cleanup requirements in `docs/kickoffs/WP-0012-eld-f4-reviewer-correction-review.md`
(`bf14c91b2b1e0b282018f36702ea41c45bba1045`):

  1. `RG-04` — Accepting `WP-0012 / 007` Sequence Binding & `WP-0012 / 002` `changes-requested` Exclusion:
     - `WP-0012 / 002` (`379d8c5d607fd248d7f272e412b4ed4a97bc64f6`, source `0cabb137...`, evidence `8eec97ce...`)
       is immutable `changes-requested` history and is explicitly rejected if supplied as the accepting
       preparation review commit (along with any ancestor of `379d8c5d607fd248d7f272e412b4ed4a97bc64f6`).
     - Requires the `/004` release JSON to bind the actual accepting `WP-0012 / 007` review commit via
       `accepted_preparation_review` (or `accepted_review_007`, `independent_preparation_review_007_sha`,
       `independent_review_007`, `accepted_007`), verifies `- Status: accepted` if `007_*_review_eld-f4-reviewer.md`
       is present in that commit, and records the result under `accepting_preparation_review_007` without
       relabeling `/002` as accepted.
     - Parses the referenced `author_lease_return` JSON blob and fails closed unless the author receipt
       explicitly attests verified clean return (`clean_return_verified is True`, `lease_returned` not `False`,
       `ocr_worker_processes_running == 0` when present, `lingering_attempt_processes == []` when present,
       and `status` not indicating failed cleanup) — never inferring author lease release from file existence
       or low VRAM alone.
  2. `RG-05` — Explicit Failed-Cleanup Unreturned Semantics (`build_reviewer_lease_return_receipt`):
     - Separates clean stop-on-failure (`status: "failed_stopped_lease_returned"`, `lease_returned: True`,
       `clean_return_verified: True`, `returned_utc: <iso>`) from failed cleanup
       (`status: "cleanup_failed_lease_unreturned"`, `lease_returned: False`, `clean_return_verified: False`,
       `returned_utc: None`) whenever any child process fails to stop, any reviewer port (`5690/4710/55439`)
       remains bound, `pg_ctl status != 3`, post-run competing/lingering model ownership check fails, or
       Q0 model immutability check fails, raising `ReviewerLeaseGuardError` even if `run_error` also occurred.
     - Protects `docs/reviews/WP-0012/eld-f4-reviewer/correction-006-review/**` in addition to `preparation/**`
       and `author-001-review/**` from `/004` live-mode writes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

API_PORT = 5690
UI_PORT = 4710
PG_PORT = 55439
REVIEWER_PORTS = (API_PORT, UI_PORT, PG_PORT)
EXPECTED_PORTS_MAP = {"api": API_PORT, "ui": UI_PORT, "postgres": PG_PORT}

DEMO_DATABASE = "eledgercare_demo_wp0012_reviewer"
HISTORICAL_SEED_DB = "eledgercare_f4_reviewer_seed_f3"
HISTORICAL_MIGRATED_DB = "eledgercare_f4_reviewer_migrated"
FORBIDDEN_DATABASES = frozenset({
    HISTORICAL_SEED_DB,
    HISTORICAL_MIGRATED_DB,
    "eledgercare_demo_wp0012_author",
    "eledgercare_f4_author_seed_f3",
    "eledgercare_f4_author_migrated",
    "eledgercare_product_dev",
})

EXPECTED_PACKET = "WP-0012"
EXPECTED_OWNER = "eld-f4-reviewer"
EXPECTED_CONVERSATION_ID = "61105d43-7706-45f2-9176-69d3256248e0"
EXPECTED_MODEL = "gemini-4-carbon-high"
EXPECTED_EFFORT = "high"
EXPECTED_BRANCH = "review/wp-0012-product-rehearsal"
EXPECTED_GPU_UUID = "GPU-9d2642d1-db40-49ad-1a0e-0fb10f9c857d"

ACCEPTED_PRODUCT_BASE_SHA = "73c8d3c4f0a00312e3444328331b6cbd6406e882"
ACCEPTED_F4_FINAL_SOURCE_SHA = "c1fed68020ae67e8b4763bc6ea5473adaa86de2b"
AUTHORITY_WP0012_SHA = "47fbc7612e4a08cf1960ad7ac01bd2843ae645e5"
AUTHORITY_002_DISPATCH_SHA = "7af4cd0e2e8ffbcb9176fc78508b6cd601c16fc0"
AUTHORITY_006_DISPATCH_SHA = "598b9e80c317a9fe3d8288732fc19d3a05219cbc"
AUTHORITY_007_OVERLAP_SHA = "bf14c91b2b1e0b282018f36702ea41c45bba1045"
PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA = "379d8c5d607fd248d7f272e412b4ed4a97bc64f6"

ALLOWED_SOURCE_COMMITS = frozenset({
    ACCEPTED_F4_FINAL_SOURCE_SHA,
    ACCEPTED_PRODUCT_BASE_SHA,
})

# Historical, preparation, dispatch, or changes-requested /002 commits that can NEVER authorize a lease or satisfy /007
REJECTED_NON_ACCEPTING_SHAS = frozenset({
    ACCEPTED_PRODUCT_BASE_SHA,
    ACCEPTED_F4_FINAL_SOURCE_SHA,
    AUTHORITY_WP0012_SHA,
    AUTHORITY_002_DISPATCH_SHA,
    AUTHORITY_006_DISPATCH_SHA,
    AUTHORITY_007_OVERLAP_SHA,
    "dec2d6476b770b9b5ee1774100d3df391c8c53d5",
    "ad5202a029a7a86bea5fa3e3d97760d0a9cc673a",
    "32465da577237827c3ac9d8ed5ee608c8e5668cf",
    "165b2421b297bf49181c91af8d05a449ad69e9b5",
    "234878326696800a16cb901913dbf732268578ea",
    "c09cf1aa8282e440e364c6020152dd257355643b",
    "7f3f8626489e898a50d275e93ee904660e97fd59",
    "cb4189aced6f38b269d8a90fa362b92058852bd0",
    "d4bbfec29c201a1c1d3dda7881afc6029cbf88cb",
    "d437fbf69e4ae2246f4e170f90bf5a5df2ef1a02",
    "0cabb137e71454d13342148a5652a5034df018ba",
    "8eec97ce301059f81ffacb04fc0144b3c33a248e",
    PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
    "0" * 40,
    "a" * 40,
    "b" * 40,
    "c" * 40,
    "d" * 40,
    "e" * 40,
    "f" * 40,
})

REJECTED_LEASE_PREFIXES = (
    "WP-0005-",
    "WP-0006-",
    "WP-0007-",
    "WP-0008-",
    "WP-0009-",
    "WP-0010-",
    "WP-0011-",
    "WP-0013-",
)

ALLOWED_RELEASE_SCHEMAS = frozenset({
    "eledgercare.wp0012-rehearsal-release/1",
    "eledgercare.wp0012-runtime-release/1",
    "eledgercare.demo-runtime-release/1",
})

EXPECTED_PRODUCT_TREES: dict[str, str] = {
    "src": "9760402fa88dcb343c28b14ad4de1bcb2fbafb2e",
    "web": "50fbbee1f58aace4e6ec36bd64203146d23aa96f",
    "tests": "25c21310699086acb818549b2a4c0b99469208f1",
    "deploy": "86e0c73d4b4c07bbdf92ebcd65a0903fc9c039f1",
    "workers/local_ocr": "dc9b69e480f93db1e73ebdd65719efaa9aeab298",
}
EXPECTED_SLNX_BLOB = "c00c2bc5ef46019fb4452fdf0bba7ca2271fc976"

EXPECTED_PINNED_DIGESTS: dict[str, str] = {
    "model_manifest_sha256": "0df07bc60abf6937c917040bced32afabd7e4d11bafc0bd99902abca610a81be",
    "dependency_lock_sha256": "582071bf20eaca1836c3d1cef21d31cbdaa1e1407184033a918a40612c128111",
    "worker_source_sha256": "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54",
    "worker_config_1p_sha256": "579aad63a9893a58466baf005ea63f87e92540d4c1f71f6b3c399e8b1e6b35ff",
    "worker_config_2p_sha256": "e4df504ddb51dcc8fb137e97f5af97c735252374738b1a1754a88b16a05de5df",
    "worker_config_3p_sha256": "ac90459ca4011b5859cfdd0b224d5ea247489b7c01775118736df7c1c9819e86",
    "f1_swo_001_sha256": "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb",
    "syn_wo_01_sha256": "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd",
    "syn_mp_01_sha256": "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3",
}

REQUIRED_PINNED_DIGEST_KEYS = (
    "model_manifest_sha256",
    "dependency_lock_sha256",
    "worker_source_sha256",
    "worker_config_1p_sha256",
    "worker_config_3p_sha256",
    "syn_wo_01_sha256",
    "syn_mp_01_sha256",
)

READONLY_Q0_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Q0\WP-0005")
WRITABLE_DEMO_ROOT = Path(r"C:\Users\jackg\eLedgerCare-Demo\WP-0012\reviewer")

STORAGE_CAP_BYTES = 4_294_967_296
MIN_FREE_DISK_BYTES = 21_474_836_480
MAX_LEASE_SECONDS = 21_600
MIN_LEASE_REMAINING_SECONDS = 300

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
REPORT_STATUS_RE = re.compile(r"^-\s*Status:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)

FORBIDDEN_PATH_TOKENS = (
    "eld-f4-implementer",
    "rehearsal/wp-0012-product",
    "wp-0012\\author",
    "wp-0012/author",
    "wp-0013",
    "eld-vocab-",
    "eledgercare-mapping",
    "eledgercare-coverage",
    "eledgercare-f2",
)

PROTECTED_RETAINED_PREFIXES = (
    "docs/reviews/wp-0012/eld-f4-reviewer/preparation",
    "docs/reviews/wp-0012/eld-f4-reviewer/author-001-review",
    "docs/reviews/wp-0012/eld-f4-reviewer/correction-006-review",
    "docs/reviews/wp-0010",
    "docs/reviews/wp-0008",
    "docs/reviews/wp-0006",
)

BENIGN_WDDM_DESKTOP_BASENAMES = frozenset({
    "dwm.exe",
    "csrss.exe",
    "explorer.exe",
    "msedge.exe",
    "msedgewebview2.exe",
    "chrome.exe",
    "firefox.exe",
    "searchhost.exe",
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
    "textinputhost.exe",
    "applicationframehost.exe",
    "systemsettings.exe",
    "widgets.exe",
    "widgetservice.exe",
    "lockapp.exe",
    "snippingtool.exe",
    "code.exe",
    "windowsterminal.exe",
    "openconsole.exe",
    "nvcontainer.exe",
    "nvidia overlay.exe",
    "nvidia share.exe",
})

MODEL_SERVER_BASENAME_RE = re.compile(
    r"^(ollama|llama(-server|-cli)?|vllm|lm[-_ ]?studio|koboldcpp)(\.exe)?$",
    re.IGNORECASE,
)
PYTHON_BASENAME_RE = re.compile(r"^python(w|[0-9.]*)?(\.exe)?$", re.IGNORECASE)
MODEL_WORKLOAD_TOKEN_RE = re.compile(
    r"(local_ocr|run_worker|q0harness|unlimited[_-]?ocr|qualification[/\\.](coverage_v1|mapping_v1|mapping_v2|baseline|q0)|"
    r"eLedgerCare-Q0[/\\]WP-0005[/\\]venv)",
    re.IGNORECASE,
)

REPARSE_ATTR = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class ReviewerLeaseGuardError(RuntimeError):
    """Raised when any fail-closed reviewer release, path, cleanup, or ceiling check fails."""


class CompetingModelOwnershipError(ReviewerLeaseGuardError):
    """Raised when an unaccounted competing model/inference process is observed."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256_hex(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def parse_utc_iso(ts: object, field_name: str) -> datetime:
    if not isinstance(ts, str) or not ts.strip():
        raise ReviewerLeaseGuardError(f"Missing or non-string UTC timestamp in {field_name!r}.")
    norm = ts.strip()
    if norm.endswith("Z"):
        norm = norm[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(norm)
    except ValueError as exc:
        raise ReviewerLeaseGuardError(f"Invalid ISO-8601 UTC timestamp in {field_name!r}: {ts!r}") from exc
    if dt.tzinfo is None:
        raise ReviewerLeaseGuardError(f"Timestamp {field_name!r} must include explicit UTC offset: {ts!r}")
    return dt.astimezone(timezone.utc)


def is_reparse_or_link(path: Path) -> bool:
    st = os.lstat(path)
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & REPARSE_ATTR)


def redact_secrets(text: str, secrets: list[str]) -> str:
    out = text
    for s in secrets:
        if s:
            out = out.replace(s, "[REDACTED-LOCAL-SECRET]")
    out = re.sub(r"(?i)(Password\s*=\s*)([^\s;\"']+)", r"\1[REDACTED-LOCAL-SECRET]", out)
    return out


def run_cmd(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout_s: int = 300,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )


def run_git(repo_root: Path, *args: str) -> str:
    cp = run_cmd(["git", *args], cwd=repo_root)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout.strip()


def git_bytes(repo_root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=str(repo_root))


def git_object_exists(repo_root: Path, spec: str) -> bool:
    return run_cmd(["git", "cat-file", "-e", spec], cwd=repo_root).returncode == 0


def git_is_ancestor(repo_root: Path, anc: str, desc: str) -> bool:
    return run_cmd(["git", "merge-base", "--is-ancestor", anc, desc], cwd=repo_root).returncode == 0


def compute_worker_source_sha256(worker_root: Path) -> str:
    py_files = [worker_root / "run_worker.py"]
    py_files.extend(sorted((worker_root / "local_ocr").glob("*.py"), key=lambda p: p.name))
    h = hashlib.sha256()
    for f in py_files:
        rel = f.relative_to(worker_root).as_posix()
        norm = f.read_bytes().replace(b"\r\n", b"\n")
        h.update(f"{rel}:{len(norm)}:{sha256_hex(norm)}\n".encode("utf-8"))
    return h.hexdigest()


def compute_worker_config_sha256(page_count: int) -> str:
    max_new_tokens = 8000 * page_count
    ngram_window = 1024 if page_count > 1 else 128
    raw_json = (
        '{"call_kwargs":{'
        '"base_size":1024,'
        '"crop_mode":false,'
        '"dash_topm":16,'
        '"eval_mode":false,'
        '"image_size":640,'
        '"max_crops":16,'
        '"max_length":131072,'
        f'"max_new_tokens":{max_new_tokens},'
        '"max_page_tokens":20000,'
        '"ngram_whitelist_token_ids":null,'
        f'"ngram_window":{ngram_window},'
        '"no_repeat_ngram_size":35,'
        '"output_path":"",'
        '"page_count_guard":true,'
        '"save_results":false,'
        '"temperature":0.0,'
        '"test_compress":false,'
        '"tps_interval":0'
        '},'
        '"envelope_schema":"eledgercare.local-extraction/1",'
        '"model_repo_id":"baidu/Unlimited-OCR-2",'
        '"model_revision":"0480966938291445591f69f08a13b041c073a96a",'
        '"prompt":"Multi page parsing.",'
        '"render_dpi":300,'
        '"request_schema":"eledgercare.local-extraction-request/1",'
        '"worker_id":"eledgercare.local-ocr-worker/1"}'
    )
    return sha256_hex(raw_json.encode("utf-8"))


def compute_local_pinned_digests(repo_root: Path) -> dict[str, str]:
    w_root = repo_root / "workers" / "local_ocr"
    fx = repo_root / "tests" / "fixtures"
    return {
        "model_manifest_sha256": file_sha256_hex(w_root / "manifests" / "model-files.json"),
        "dependency_lock_sha256": file_sha256_hex(w_root / "manifests" / "dependency-lock.json"),
        "worker_source_sha256": compute_worker_source_sha256(w_root),
        "worker_config_1p_sha256": compute_worker_config_sha256(1),
        "worker_config_2p_sha256": compute_worker_config_sha256(2),
        "worker_config_3p_sha256": compute_worker_config_sha256(3),
        "f1_swo_001_sha256": file_sha256_hex(fx / "F1-SWO-001.pdf"),
        "syn_wo_01_sha256": file_sha256_hex(fx / "SYN-WO-01-v1-raster300.pdf"),
        "syn_mp_01_sha256": file_sha256_hex(fx / "SYN-MP-01-v0-clean.pdf"),
    }


def guard_new_non_overwriting_output_targets(
    repo_root: Path,
    *,
    file_targets: list[Path],
    dir_targets: list[Path],
) -> None:
    """RG-03/05: Refuses writing into retained preparation/author-001-review/correction-006-review or existing paths."""
    repo_res = repo_root.resolve()
    demo_res = WRITABLE_DEMO_ROOT.resolve()

    for p in [*file_targets, *dir_targets]:
        cur_check = p
        while True:
            if cur_check.exists() and is_reparse_or_link(cur_check):
                raise ReviewerLeaseGuardError(f"Reparse point / symlink forbidden in output path: {cur_check}")
            if cur_check.parent == cur_check:
                break
            cur_check = cur_check.parent
        resolved = p.resolve()
        norm_lower = str(resolved).replace("\\", "/").lower()
        for bad in FORBIDDEN_PATH_TOKENS:
            if bad in norm_lower:
                raise ReviewerLeaseGuardError(f"Forbidden output path token {bad!r} in {resolved}")

        in_owned_review = False
        try:
            rel_repo = resolved.relative_to(repo_res).as_posix()
            rel_lower = rel_repo.lower()
            for protected in PROTECTED_RETAINED_PREFIXES:
                if rel_lower == protected or rel_lower.startswith(protected + "/"):
                    raise ReviewerLeaseGuardError(
                        f"Refusing to write or overwrite retained evidence path: {rel_repo}"
                    )
            if rel_repo.startswith("docs/reviews/WP-0012/eld-f4-reviewer/"):
                in_owned_review = True
        except ValueError:
            pass

        in_demo_root = False
        try:
            resolved.relative_to(demo_res)
            in_demo_root = True
        except ValueError:
            pass

        if not (in_owned_review or in_demo_root):
            raise ReviewerLeaseGuardError(
                f"Output path {resolved} must reside under a new docs/reviews/WP-0012/eld-f4-reviewer/<subdir> "
                f"or {demo_res}."
            )

    for ft in file_targets:
        if ft.exists():
            raise FileExistsError(f"Refusing to overwrite existing output file: {ft}")

    for dt in dir_targets:
        if dt.exists() and any(dt.iterdir()):
            raise FileExistsError(f"Refusing to reuse non-empty output directory: {dt}")


def _extract_required_commit_binding(release_doc: dict, candidate_keys: tuple[str, ...], label: str) -> tuple[str, str]:
    for k in candidate_keys:
        v = release_doc.get(k)
        if isinstance(v, str) and v.strip():
            return k, v.strip().lower()
        if isinstance(v, dict):
            disp = v.get("disposition") or v.get("status")
            if disp is not None and str(disp).strip().lower() != "accepted":
                raise ReviewerLeaseGuardError(f"{label} binding {k!r} has non-accepting disposition: {disp!r}")
            for sub in ("commit", "sha", "publication", "report"):
                sv = v.get(sub)
                if isinstance(sv, str) and sv.strip():
                    return f"{k}.{sub}", sv.strip().lower()
    raise ReviewerLeaseGuardError(f"Missing required {label} commit binding ({candidate_keys[0]}) in release JSON.")


def _verify_commit_has_no_non_accepting_007_report(repo_root: Path, commit_sha: str) -> None:
    if not git_object_exists(repo_root, f"{commit_sha}^{{commit}}"):
        return
    cp = run_cmd(
        ["git", "ls-tree", "-r", "--name-only", commit_sha, "docs/agent-reports/eld-f4-reviewer/WP-0012"],
        cwd=repo_root,
    )
    if cp.returncode != 0:
        return
    for ln in cp.stdout.splitlines():
        rp = ln.strip()
        if Path(rp).name.startswith("007_") and rp.endswith("_review_eld-f4-reviewer.md"):
            txt = git_bytes(repo_root, "cat-file", "-p", f"{commit_sha}:{rp}").decode("utf-8", errors="replace")
            m = REPORT_STATUS_RE.search(txt)
            st_val = m.group(1).strip().lower() if m else "missing"
            if st_val != "accepted":
                raise ReviewerLeaseGuardError(
                    f"WP-0012 / 007 report {rp} in {commit_sha} has Status: {st_val!r} (expected 'accepted')."
                )


def _validate_author_lease_return_payload(payload: dict, source_desc: str) -> None:
    """RG-04/05: Refuses treating an author receipt file as a returned lease if cleanup failed."""
    if payload.get("lease_returned") is False or payload.get("clean_return_verified") is False:
        raise ReviewerLeaseGuardError(
            f"Author lease-return blob {source_desc} explicitly reports unreturned/failed cleanup!"
        )
    status_val = str(payload.get("status") or "").strip().lower()
    if "unreturned" in status_val or "cleanup_failed" in status_val:
        raise ReviewerLeaseGuardError(
            f"Author lease-return blob {source_desc} has unreturned status {status_val!r}!"
        )
    if "clean_return_verified" in payload and payload.get("clean_return_verified") is not True:
        raise ReviewerLeaseGuardError(
            f"Author lease-return blob {source_desc} lacks clean_return_verified === true!"
        )
    if "ocr_worker_processes_running" in payload and payload.get("ocr_worker_processes_running") != 0:
        raise ReviewerLeaseGuardError(
            f"Author lease-return blob {source_desc} reports running OCR workers: {payload.get('ocr_worker_processes_running')}"
        )
    if payload.get("lingering_attempt_processes"):
        raise ReviewerLeaseGuardError(
            f"Author lease-return blob {source_desc} reports lingering attempt processes!"
        )
    if payload.get("cleanup_errors"):
        raise ReviewerLeaseGuardError(
            f"Author lease-return blob {source_desc} reports cleanup_errors: {payload.get('cleanup_errors')}"
        )


def _extract_author_lease_return_binding(
    release_doc: dict,
    blob_loader,
    commit_exists_fn,
) -> dict:
    """Verifies that author's prior WP-0012 GPU lease return is explicitly bound AND verified clean before /004."""
    for key in ("author_lease_return", "returned_author_lease", "prior_author_lease_return"):
        val = release_doc.get(key)
        if isinstance(val, str) and HEX40_RE.match(val.strip().lower()):
            sha = val.strip().lower()
            if sha in REJECTED_NON_ACCEPTING_SHAS or not commit_exists_fn(sha):
                raise ReviewerLeaseGuardError(f"Invalid or unknown commit in {key}: {sha!r}")
            return {"key": key, "commit": sha}
        if isinstance(val, dict):
            if val.get("clean_return_verified") is False or val.get("lease_returned") is False:
                raise ReviewerLeaseGuardError(f"{key} dictionary explicitly marks author lease unreturned: {val!r}")
            commit_val = str(val.get("commit") or val.get("audit_commit") or "").strip().lower()
            path_val = str(val.get("path") or "").strip().replace("\\", "/")
            sha256_val = str(val.get("sha256") or "").strip().lower()
            if commit_val:
                if not HEX40_RE.match(commit_val) or commit_val in REJECTED_NON_ACCEPTING_SHAS or not commit_exists_fn(commit_val):
                    raise ReviewerLeaseGuardError(f"Invalid commit in {key}: {commit_val!r}")
            if path_val and sha256_val:
                if (
                    not (
                        path_val.startswith("docs/coordination/WP-0012/")
                        or path_val.startswith("docs/coordination/WP-0012-0013/")
                    )
                    or not HEX64_RE.match(sha256_val)
                ):
                    raise ReviewerLeaseGuardError(f"Invalid path/sha256 in {key}: {val!r}")
                raw_b = blob_loader(path_val)
                if sha256_val not in (sha256_hex(raw_b), sha256_hex(raw_b.replace(b"\r\n", b"\n"))):
                    raise ReviewerLeaseGuardError(f"Author lease-return blob SHA-256 mismatch on {path_val}")
                parsed_ret = json.loads(raw_b.decode("utf-8"))
                if isinstance(parsed_ret, dict):
                    _validate_author_lease_return_payload(parsed_ret, path_val)
                return {"key": key, "path": path_val, "sha256": sha256_val, "commit": commit_val or None}
            if commit_val:
                return {"key": key, "commit": commit_val}
    raise ReviewerLeaseGuardError(
        "Missing required author_lease_return binding in reviewer /004 release JSON."
    )


def validate_reviewer_release_contract(
    release_doc: dict,
    *,
    repo_root: Path,
    release_commit: str,
    release_path: str,
    now_utc: datetime,
    blob_loader,
    commit_exists_fn,
    helper_paths_to_bind: tuple[Path, ...],
    require_clean_worktree: bool = True,
    allow_synthetic_test_only: bool = False,
) -> dict:
    """RG-01 & RG-04: Fail-closed coordinator Git release + accepting `/007` + `/003` + clean author lease return validator."""
    if release_doc.get("synthetic_test_only") is True and not allow_synthetic_test_only:
        raise ReviewerLeaseGuardError(
            "Release JSON is marked synthetic_test_only=True and can NEVER authorize live execution."
        )

    rc = release_commit.strip().lower()
    if not HEX40_RE.match(rc):
        raise ReviewerLeaseGuardError(f"release_commit must be 40 lowercase hex chars, got {release_commit!r}")
    if rc in REJECTED_NON_ACCEPTING_SHAS and not allow_synthetic_test_only:
        raise ReviewerLeaseGuardError(
            f"Commit {rc} is historical/preparation/changes-requested and cannot authorize live /004 execution."
        )
    if rc in {
        ACCEPTED_PRODUCT_BASE_SHA,
        ACCEPTED_F4_FINAL_SOURCE_SHA,
        AUTHORITY_WP0012_SHA,
        AUTHORITY_002_DISPATCH_SHA,
        AUTHORITY_006_DISPATCH_SHA,
        AUTHORITY_007_OVERLAP_SHA,
        PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
    }:
        raise ReviewerLeaseGuardError(
            f"Authority/base/002 commit {rc} cannot authorize live /004 execution."
        )

    rel_norm = release_path.strip().replace("\\", "/")
    if (
        not (
            rel_norm.startswith("docs/coordination/WP-0012/")
            or rel_norm.startswith("docs/coordination/WP-0012-0013/")
        )
        or not rel_norm.endswith(".json")
        or ".." in rel_norm.split("/")
    ):
        raise ReviewerLeaseGuardError(
            f"release_path must be under docs/coordination/WP-0012*/*.json, got {release_path!r}"
        )

    schema = release_doc.get("schema")
    if schema not in ALLOWED_RELEASE_SCHEMAS:
        raise ReviewerLeaseGuardError(f"Unsupported release schema: {schema!r}")

    if release_doc.get("packet", EXPECTED_PACKET) != EXPECTED_PACKET:
        raise ReviewerLeaseGuardError(f"packet {release_doc.get('packet')!r} != {EXPECTED_PACKET!r}")
    owner = release_doc.get("owner") or release_doc.get("owner_agent")
    if owner != EXPECTED_OWNER:
        raise ReviewerLeaseGuardError(f"owner {owner!r} != {EXPECTED_OWNER!r}")
    if release_doc.get("conversation_id") != EXPECTED_CONVERSATION_ID:
        raise ReviewerLeaseGuardError(
            f"conversation_id {release_doc.get('conversation_id')!r} != {EXPECTED_CONVERSATION_ID!r}"
        )
    if release_doc.get("model") != EXPECTED_MODEL or release_doc.get("effort") != EXPECTED_EFFORT:
        raise ReviewerLeaseGuardError(
            f"model/effort ({release_doc.get('model')!r}/{release_doc.get('effort')!r}) "
            f"!= ({EXPECTED_MODEL!r}/{EXPECTED_EFFORT!r})"
        )

    db_name = str(release_doc.get("database") or release_doc.get("database_name") or "").strip()
    if db_name in FORBIDDEN_DATABASES or db_name != DEMO_DATABASE:
        raise ReviewerLeaseGuardError(f"database must equal {DEMO_DATABASE!r}, got {db_name!r}")

    source_commit = str(release_doc.get("source_commit") or "").strip().lower()
    if source_commit not in ALLOWED_SOURCE_COMMITS:
        raise ReviewerLeaseGuardError(
            f"source_commit {source_commit!r} must match {ACCEPTED_F4_FINAL_SOURCE_SHA!r} or {ACCEPTED_PRODUCT_BASE_SHA!r}"
        )

    executing_head = str(release_doc.get("executing_head") or "").strip().lower()
    if not HEX40_RE.match(executing_head) or executing_head in REJECTED_NON_ACCEPTING_SHAS:
        raise ReviewerLeaseGuardError(f"Invalid or pre-007 executing_head: {executing_head!r}")

    actual_head = run_git(repo_root, "rev-parse", "HEAD").lower()
    branch_name = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    porcelain = run_git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if branch_name != EXPECTED_BRANCH:
        raise ReviewerLeaseGuardError(f"Owned branch must be {EXPECTED_BRANCH!r}, got {branch_name!r}")
    if require_clean_worktree and porcelain != "":
        raise ReviewerLeaseGuardError(f"Worktree must be clean before live /004 execution:\n{porcelain}")
    if actual_head != executing_head:
        raise ReviewerLeaseGuardError(f"Local HEAD {actual_head} != release executing_head {executing_head}")
    if not git_is_ancestor(repo_root, PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA, actual_head):
        raise ReviewerLeaseGuardError(
            f"Immutable WP-0012 / 002 ({PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA}) must be an ancestor of {actual_head}"
        )

    if require_clean_worktree:
        for hp in helper_paths_to_bind:
            rel_hp = hp.resolve().relative_to(repo_root.resolve()).as_posix()
            if not git_object_exists(repo_root, f"{actual_head}:{rel_hp}"):
                raise ReviewerLeaseGuardError(f"Helper {rel_hp} is not committed in HEAD {actual_head}")
            committed = git_bytes(repo_root, "cat-file", "-p", f"{actual_head}:{rel_hp}")
            if hp.read_bytes() != committed:
                raise ReviewerLeaseGuardError(f"Working copy of {rel_hp} differs from committed HEAD blob")

    if "prior_changes_requested_review_002" in release_doc:
        p002 = str(release_doc.get("prior_changes_requested_review_002") or "").strip().lower()
        if p002 != PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA:
            raise ReviewerLeaseGuardError(
                f"prior_changes_requested_review_002 {p002!r} != {PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA!r}"
            )

    # RG-04: Must bind accepting WP-0012 / 007 review; NEVER accept changes-requested /002 (379d8c5d...) or ancestors
    r007_key, r007_sha = _extract_required_commit_binding(
        release_doc,
        (
            "accepted_preparation_review",
            "accepted_review_007",
            "independent_preparation_review_007_sha",
            "independent_review_007",
            "accepted_007",
            "accepted_preparation_review_sha",
        ),
        "accepting WP-0012 / 007 preparation review",
    )
    if (
        not HEX40_RE.match(r007_sha)
        or r007_sha in REJECTED_NON_ACCEPTING_SHAS
        or not commit_exists_fn(r007_sha)
    ):
        raise ReviewerLeaseGuardError(
            f"Invalid, unknown, or non-accepting (/002 changes-requested) review commit in {r007_key}: {r007_sha!r}"
        )
    if git_object_exists(repo_root, f"{r007_sha}^{{commit}}") and git_is_ancestor(
        repo_root, r007_sha, PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA
    ):
        raise ReviewerLeaseGuardError(
            f"Review commit {r007_sha} in {r007_key} is WP-0012 / 002 (changes-requested) or an earlier ancestor; "
            f"/004 requires accepting WP-0012 / 007."
        )
    _verify_commit_has_no_non_accepting_007_report(repo_root, r007_sha)

    a003_key, a003_sha = _extract_required_commit_binding(
        release_doc,
        (
            "accepted_author_003",
            "author_verification_003",
            "author_runtime_003",
            "author_003",
        ),
        "author WP-0012 / 003 verification",
    )
    if (
        not HEX40_RE.match(a003_sha)
        or a003_sha in REJECTED_NON_ACCEPTING_SHAS
        or not commit_exists_fn(a003_sha)
    ):
        raise ReviewerLeaseGuardError(f"Invalid or unverified author /003 commit in {a003_key}: {a003_sha!r}")

    author_return_info = _extract_author_lease_return_binding(
        release_doc,
        blob_loader=blob_loader,
        commit_exists_fn=lambda sha: sha not in REJECTED_NON_ACCEPTING_SHAS and commit_exists_fn(sha),
    )

    rel_trees = release_doc.get("product_tree_objects")
    if not isinstance(rel_trees, dict):
        raise ReviewerLeaseGuardError("Missing product_tree_objects dict in release JSON.")
    for tpath, exp_oid in EXPECTED_PRODUCT_TREES.items():
        loc_oid = run_git(repo_root, "rev-parse", f"HEAD:{tpath}").lower()
        if loc_oid != exp_oid:
            raise ReviewerLeaseGuardError(f"Local tree {tpath} ({loc_oid}) != expected {exp_oid}")
        if str(rel_trees.get(tpath) or "").lower() != exp_oid:
            raise ReviewerLeaseGuardError(f"Release product_tree_objects[{tpath!r}] != expected {exp_oid}")
    if run_git(repo_root, "rev-parse", "HEAD:ELedgerCare.slnx").lower() != EXPECTED_SLNX_BLOB:
        raise ReviewerLeaseGuardError("Local ELedgerCare.slnx blob drifted from accepted base.")

    local_digests = compute_local_pinned_digests(repo_root)
    for dk, dv in EXPECTED_PINNED_DIGESTS.items():
        if local_digests[dk] != dv:
            raise ReviewerLeaseGuardError(f"Local artifact digest {dk} ({local_digests[dk]}) != {dv}")

    rel_digests = release_doc.get("pinned_digests")
    if not isinstance(rel_digests, dict):
        raise ReviewerLeaseGuardError("Missing pinned_digests dict in release JSON.")
    for dk in REQUIRED_PINNED_DIGEST_KEYS:
        if str(rel_digests.get(dk) or "").lower() != EXPECTED_PINNED_DIGESTS[dk]:
            raise ReviewerLeaseGuardError(f"Release pinned_digests[{dk!r}] != {EXPECTED_PINNED_DIGESTS[dk]}")

    lease_id = str(release_doc.get("lease_id") or "").strip()
    if not lease_id or lease_id.startswith(REJECTED_LEASE_PREFIXES) or "WP-0012" not in lease_id:
        raise ReviewerLeaseGuardError(f"Invalid or non-WP-0012 lease_id: {lease_id!r}")

    if release_doc.get("gpu_uuid") != EXPECTED_GPU_UUID:
        raise ReviewerLeaseGuardError(f"gpu_uuid {release_doc.get('gpu_uuid')!r} != exact {EXPECTED_GPU_UUID!r}")

    released_dt = parse_utc_iso(release_doc.get("released_utc"), "released_utc")
    expires_dt = parse_utc_iso(release_doc.get("expires_utc"), "expires_utc")
    window_s = (expires_dt - released_dt).total_seconds()
    if window_s <= 0 or window_s > MAX_LEASE_SECONDS:
        raise ReviewerLeaseGuardError(f"Lease window ({window_s}s) must be within (0, {MAX_LEASE_SECONDS}s].")
    if now_utc < released_dt:
        raise ReviewerLeaseGuardError(f"Lease released_utc {released_dt.isoformat()} is in the future.")
    remaining_s = (expires_dt - now_utc).total_seconds()
    if remaining_s < MIN_LEASE_REMAINING_SECONDS:
        raise ReviewerLeaseGuardError(
            f"Lease expired or under {MIN_LEASE_REMAINING_SECONDS}s remaining ({remaining_s:.1f}s)."
        )

    max_attempts = release_doc.get("max_model_attempts", release_doc.get("max_attempts"))
    if max_attempts != 2:
        raise ReviewerLeaseGuardError(f"Reviewer max_model_attempts must equal 2, got {max_attempts!r}")

    if release_doc.get("ports") != EXPECTED_PORTS_MAP:
        raise ReviewerLeaseGuardError(f"ports {release_doc.get('ports')!r} != {EXPECTED_PORTS_MAP!r}")
    if Path(str(release_doc.get("readonly_q0_root") or "")) != READONLY_Q0_ROOT:
        raise ReviewerLeaseGuardError(f"readonly_q0_root != {READONLY_Q0_ROOT}")
    rt_raw = release_doc.get("runtime_root") or release_doc.get("writable_runtime_root") or ""
    if Path(str(rt_raw)) != WRITABLE_DEMO_ROOT:
        raise ReviewerLeaseGuardError(f"runtime_root {rt_raw!r} != {WRITABLE_DEMO_ROOT}")
    if release_doc.get("storage_cap_bytes") != STORAGE_CAP_BYTES:
        raise ReviewerLeaseGuardError(f"storage_cap_bytes != {STORAGE_CAP_BYTES}")
    if release_doc.get("free_floor_bytes") != MIN_FREE_DISK_BYTES:
        raise ReviewerLeaseGuardError(f"free_floor_bytes != {MIN_FREE_DISK_BYTES}")
    if release_doc.get("allow_test_content", False) is not False:
        raise ReviewerLeaseGuardError("allow_test_content must be false.")
    if release_doc.get("torchvision_local_sha256_TOFU_accepted") is not True:
        raise ReviewerLeaseGuardError("torchvision_local_sha256_TOFU_accepted must be true.")

    obs = release_doc.get("observation_files")
    if not isinstance(obs, dict) or not obs:
        raise ReviewerLeaseGuardError("Missing observation_files dict in release JSON.")

    has_three_file = all(k in obs for k in ("host-before.json", "processes-before.json", "model-before.json"))
    has_combined = "ownership-before.json" in obs and "model-before.json" in obs
    if not (has_three_file or has_combined):
        raise ReviewerLeaseGuardError(
            "observation_files must bind ('host-before.json', 'processes-before.json', 'model-before.json') "
            "or ('ownership-before.json', 'model-before.json')."
        )

    verified_obs: dict[str, dict] = {}
    parsed_pre_lease_blobs: dict[str, dict] = {}
    for obs_key, entry in obs.items():
        if not isinstance(entry, dict):
            raise ReviewerLeaseGuardError(f"Invalid observation_files[{obs_key!r}] entry: {entry!r}")
        obs_path = str(entry.get("path") or "").strip().replace("\\", "/")
        obs_sha = str(entry.get("sha256") or "").strip().lower()
        if (
            not (
                obs_path.startswith("docs/coordination/WP-0012/")
                or obs_path.startswith("docs/coordination/WP-0012-0013/")
            )
            or not HEX64_RE.match(obs_sha)
        ):
            raise ReviewerLeaseGuardError(f"Invalid observation path/sha256 for {obs_key!r}: {entry!r}")
        raw_b = blob_loader(obs_path)
        raw_sha = sha256_hex(raw_b)
        lf_sha = sha256_hex(raw_b.replace(b"\r\n", b"\n"))
        if obs_sha not in (raw_sha, lf_sha):
            raise ReviewerLeaseGuardError(
                f"Observation blob {obs_path} SHA-256 mismatch: expected {obs_sha}, got raw={raw_sha} / lf={lf_sha}"
            )
        verified_obs[obs_key] = {"path": obs_path, "sha256": obs_sha}
        try:
            parsed_pre_lease_blobs[obs_key] = json.loads(raw_b.decode("utf-8"))
        except Exception:
            parsed_pre_lease_blobs[obs_key] = {}

    return {
        "release_commit": rc,
        "release_path": rel_norm,
        "schema": schema,
        "lease_id": lease_id,
        "gpu_uuid": EXPECTED_GPU_UUID,
        "executing_head": actual_head,
        "source_commit": source_commit,
        "prior_changes_requested_review_002": PRIOR_CHANGES_REQUESTED_REVIEW_002_SHA,
        "accepting_preparation_review_007": {r007_key: r007_sha},
        "accepted_author_003": {a003_key: a003_sha},
        "author_lease_return": author_return_info,
        "lease_remaining_seconds": round(remaining_s, 2),
        "verified_observation_files": verified_obs,
        "parsed_pre_lease_blobs": parsed_pre_lease_blobs,
    }


def evaluate_gpu_and_model_ownership(
    snapshot: dict,
    *,
    pre_lease_blobs: dict[str, dict] | None = None,
    self_pid: int | None = None,
) -> dict:
    """RG-02: Distinguishes benign Windows desktop/WDDM GPU sharing from competing model work."""
    my_pid = self_pid if self_pid is not None else os.getpid()
    accounted_non_model_pids: set[int] = set()
    for blob in (pre_lease_blobs or {}).values():
        if not isinstance(blob, dict):
            continue
        for proc_row in blob.get("candidate_and_gpu_processes") or blob.get("processes") or []:
            if isinstance(proc_row, dict) and "ProcessId" in proc_row:
                p_name = Path(str(proc_row.get("Name") or "")).name.lower()
                p_exe = str(proc_row.get("ExecutablePath") or "")
                p_cmd = str(proc_row.get("CommandLine") or "")
                if (
                    not MODEL_SERVER_BASENAME_RE.match(p_name)
                    and not PYTHON_BASENAME_RE.match(p_name)
                    and not MODEL_WORKLOAD_TOKEN_RE.search(p_exe)
                    and not MODEL_WORKLOAD_TOKEN_RE.search(p_cmd)
                ):
                    accounted_non_model_pids.add(int(proc_row["ProcessId"]))

    wddm_entries: list[dict] = []
    competing_violations: list[dict] = []

    proc_by_pid: dict[int, dict] = {}
    for p in snapshot.get("candidate_and_gpu_processes") or []:
        if isinstance(p, dict) and p.get("ProcessId") is not None:
            proc_by_pid[int(p["ProcessId"])] = p

    for raw_line in snapshot.get("apps") or []:
        line = str(raw_line).strip()
        if not line or line.lower().startswith("no running"):
            continue
        parts = [seg.strip() for seg in line.split(",")]
        if len(parts) < 2 or not parts[0].isdigit():
            competing_violations.append({"source": "nvidia_smi_compute_apps_unparsed", "line": line})
            continue
        pid = int(parts[0])
        if pid == my_pid:
            continue
        proc_path_str = parts[1]
        base = Path(proc_path_str.replace("\\", "/")).name.lower()
        used_mem = parts[2] if len(parts) >= 3 else ""
        proc_detail = proc_by_pid.get(pid, {})
        exe_path = str(proc_detail.get("ExecutablePath") or proc_path_str)
        cmd_line = str(proc_detail.get("CommandLine") or "")

        if (
            MODEL_SERVER_BASENAME_RE.match(base)
            or PYTHON_BASENAME_RE.match(base)
            or MODEL_WORKLOAD_TOKEN_RE.search(exe_path)
            or MODEL_WORKLOAD_TOKEN_RE.search(cmd_line)
        ):
            competing_violations.append({
                "source": "gpu_compute_app",
                "pid": pid,
                "name": base,
                "executable": exe_path,
                "used_memory_mib": used_mem,
            })
        elif base in BENIGN_WDDM_DESKTOP_BASENAMES or pid in accounted_non_model_pids:
            wddm_entries.append({
                "pid": pid,
                "name": base,
                "used_memory_mib": used_mem,
                "classification": "benign_wddm_or_accounted_desktop_process",
            })
        else:
            competing_violations.append({
                "source": "unaccounted_gpu_compute_process",
                "pid": pid,
                "name": base,
                "executable": exe_path,
                "used_memory_mib": used_mem,
            })

    for pid, p in sorted(proc_by_pid.items()):
        if pid == my_pid:
            continue
        name = Path(str(p.get("Name") or "")).name.lower()
        exe_path = str(p.get("ExecutablePath") or "")
        cmd_line = str(p.get("CommandLine") or "")
        if MODEL_SERVER_BASENAME_RE.match(name):
            competing_violations.append({"source": "host_model_server", "pid": pid, "name": name, "executable": exe_path})
        elif MODEL_WORKLOAD_TOKEN_RE.search(exe_path) or MODEL_WORKLOAD_TOKEN_RE.search(cmd_line):
            competing_violations.append({
                "source": "host_ocr_or_qualification_worker",
                "pid": pid,
                "name": name,
                "executable": exe_path,
            })

    ollama_lines = [str(x).strip() for x in (snapshot.get("ollama_ps") or []) if str(x).strip()]
    if len(ollama_lines) >= 2 and ollama_lines[0].upper().startswith("NAME"):
        for active_row in ollama_lines[1:]:
            competing_violations.append({"source": "ollama_ps_active_model", "row": active_row})

    if competing_violations:
        raise CompetingModelOwnershipError(
            f"Unaccounted competing model/GPU workload detected: {json.dumps(competing_violations)}"
        )

    return {
        "sole_model_job_verified": True,
        "hardware_exclusivity_claimed": False,
        "wddm_desktop_sharing_observed": len(wddm_entries) > 0,
        "wddm_desktop_sharing_entries": wddm_entries,
        "competing_model_violations": [],
    }


def build_reviewer_lease_return_receipt(
    *,
    lease_id: str,
    run_error: str | None,
    cleanup_errors: list[str],
    ports_after: dict[str, list[dict]],
    pg_ctl_status_exit_code: int,
    api_stop_receipts: list[dict],
    ui_stop_receipts: list[dict],
    pre_ownership: dict,
    post_ownership: dict,
    q0_model_immutability_verified: bool,
    persisted_counts: dict,
    run_directories: list[str],
    postmaster_recorded: dict | None,
    secrets: list[str],
    now_utc: datetime | None = None,
) -> dict:
    """RG-05: Builds an honest reviewer lease-return receipt that NEVER claims release when cleanup failed."""
    ts_now = (now_utc or datetime.now(timezone.utc)).isoformat()
    derived_cleanup_errors = list(cleanup_errors)

    ports_unbound = all(len(ports_after.get(str(p), [])) == 0 for p in REVIEWER_PORTS)
    if not ports_unbound:
        derived_cleanup_errors.append(f"reviewer_ports_still_bound={ports_after}")
    if pg_ctl_status_exit_code != 3:
        derived_cleanup_errors.append(f"pg_ctl_status_exit_code={pg_ctl_status_exit_code} (expected 3 stopped)")
    if any(r.get("aliveAfter") is True for r in api_stop_receipts):
        derived_cleanup_errors.append("api_child_alive_after_stop")
    if any(r.get("aliveAfter") is True for r in ui_stop_receipts):
        derived_cleanup_errors.append("ui_child_alive_after_stop")
    if post_ownership.get("sole_model_job_verified") is not True:
        derived_cleanup_errors.append(f"post_ownership_unverified={post_ownership.get('error')}")
    if not q0_model_immutability_verified:
        derived_cleanup_errors.append("q0_model_immutability_check_failed")

    clean_return_ok = len(derived_cleanup_errors) == 0
    if not clean_return_ok:
        status = "cleanup_failed_lease_unreturned"
        lease_returned = False
        returned_utc = None
    elif run_error is not None:
        status = "failed_stopped_lease_returned"
        lease_returned = True
        returned_utc = ts_now
    else:
        status = "completed"
        lease_returned = True
        returned_utc = ts_now

    return {
        "schema": "eledgercare.wp-0012.reviewer-lease-return/3",
        "recorded_utc": ts_now,
        "lease_returned": lease_returned,
        "clean_return_verified": clean_return_ok,
        "returned_utc": returned_utc,
        "reviewer": EXPECTED_OWNER,
        "lease_id": lease_id,
        "gpu_uuid": EXPECTED_GPU_UUID,
        "status": status,
        "failure_detail": redact_secrets(run_error, secrets) if run_error else None,
        "cleanup_errors": [redact_secrets(e, secrets) for e in derived_cleanup_errors],
        "persisted_counts": persisted_counts,
        "run_directories": run_directories,
        "ports_after": ports_after,
        "ports_unbound_verified": ports_unbound,
        "pg_ctl_status_exit_code": pg_ctl_status_exit_code,
        "postmaster_recorded": postmaster_recorded,
        "api_stop_receipts": api_stop_receipts,
        "ui_stop_receipts": ui_stop_receipts,
        "pre_ownership": pre_ownership,
        "post_ownership": post_ownership,
        "q0_model_immutability_verified": q0_model_immutability_verified,
    }


def collect_live_ownership_snapshot(repo_root: Path) -> dict:
    """Collects live GPU & candidate-process snapshot during a leased /004 run (NEVER called in CPU mode)."""
    gpu_cp = run_cmd(
        [
            "nvidia-smi",
            f"--id={EXPECTED_GPU_UUID}",
            "--query-gpu=timestamp,uuid,name,driver_version,compute_cap,memory.total,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ],
        cwd=repo_root,
    )
    apps_cp = run_cmd(
        [
            "nvidia-smi",
            f"--id={EXPECTED_GPU_UUID}",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        cwd=repo_root,
    )
    if gpu_cp.returncode != 0 or apps_cp.returncode != 0:
        raise ReviewerLeaseGuardError(f"nvidia-smi query failed on {EXPECTED_GPU_UUID}: {apps_cp.stderr}")

    ps_procs = (
        "@(Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^(python(w)?|ollama|llama(-server|-cli)?|vllm|lm.?studio|koboldcpp)\\.exe$' -or "
        "$_.CommandLine -match '(local_ocr|run_worker|q0harness|qualification[/\\\\.](coverage_v1|mapping_v1|mapping_v2|baseline|q0))' "
        "} | ForEach-Object { @{ ProcessId = [int]$_.ProcessId; Name = $_.Name; ExecutablePath = $_.ExecutablePath; "
        "CommandLine = $_.CommandLine } }) | ConvertTo-Json -Compress -Depth 4"
    )
    procs_cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps_procs], cwd=repo_root)
    raw_procs = json.loads(procs_cp.stdout) if procs_cp.returncode == 0 and procs_cp.stdout.strip() else []
    if isinstance(raw_procs, dict):
        raw_procs = [raw_procs]

    ollama_exe = shutil.which("ollama")
    ollama_lines = None
    if ollama_exe:
        ocp = run_cmd([ollama_exe, "ps"], cwd=repo_root)
        if ocp.returncode == 0:
            ollama_lines = ocp.stdout.splitlines()

    return {
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "gpu": [ln for ln in gpu_cp.stdout.splitlines() if ln.strip()],
        "apps": [ln for ln in apps_cp.stdout.splitlines() if ln.strip()],
        "candidate_and_gpu_processes": raw_procs,
        "ollama_ps": ollama_lines,
    }


def inspect_process(pid: int, cwd: Path) -> dict | None:
    ps = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { 'null' } else { "
        "@{ pid = [int]$p.Id; name = $p.ProcessName; startUtc = $p.StartTime.ToUniversalTime().ToString('o') } | ConvertTo-Json -Compress }"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps], cwd=cwd)
    if cp.returncode != 0 or cp.stdout.strip() == "null":
        return None
    return json.loads(cp.stdout)


def stop_owned_process(proc: subprocess.Popen[bytes] | None, recorded_info: dict | None, cwd: Path) -> dict:
    if proc is None:
        return {"stopped": False, "reason": "not_started"}
    pid = proc.pid
    expected_start = recorded_info["startUtc"] if recorded_info else None
    if proc.poll() is not None:
        return {"pid": pid, "startUtc": expected_start, "alreadyExitedCode": proc.returncode, "aliveAfter": False}
    cur = inspect_process(pid, cwd)
    if cur is None:
        return {"pid": pid, "startUtc": expected_start, "aliveAfter": False}
    if expected_start is not None and cur["startUtc"] != expected_start:
        raise RuntimeError(f"Refusing to terminate PID {pid}: startUtc changed ({cur['startUtc']} != {expected_start})")
    proc.kill()
    proc.wait(timeout=30)
    after = inspect_process(pid, cwd)
    return {
        "pid": pid,
        "name": cur["name"],
        "startUtc": expected_start or cur["startUtc"],
        "exitCode": proc.returncode,
        "aliveAfter": after is not None,
    }


def observe_ports(ports: tuple[int, ...], cwd: Path) -> dict[str, list[dict]]:
    ps_script = (
        "$out = @{}; "
        f"foreach ($p in @({','.join(str(p) for p in ports)})) {{ "
        "$conns = @(Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue | "
        "ForEach-Object { @{ localAddress = $_.LocalAddress; localPort = [int]$_.LocalPort; owningPid = [int]$_.OwningProcess } }); "
        "$out[\"$p\"] = $conns "
        "}; "
        "$out | ConvertTo-Json -Compress -Depth 4"
    )
    cp = run_cmd(["pwsh", "-NoProfile", "-Command", ps_script], cwd=cwd)
    if cp.returncode != 0:
        raise RuntimeError(f"Port observation failed: {cp.stderr}")
    return json.loads(cp.stdout)


def http_get_status(port: int, path_str: str, timeout_s: float = 5.0) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout_s)
    try:
        conn.request("GET", path_str, headers={"Host": f"127.0.0.1:{port}"})
        resp = conn.getresponse()
        resp.read()
        return resp.status
    finally:
        conn.close()


def start_owned_services_atomic(
    *,
    api_cmd: list[str],
    api_cwd: Path,
    api_env: dict[str, str],
    api_log_path: Path,
    ui_cmd: list[str],
    ui_cwd: Path,
    ui_env: dict[str, str],
    ui_log_path: Path,
    repo_root: Path,
    api_ready_fn=None,
    ui_ready_fn=None,
    api_timeout_s: float = 45.0,
    ui_timeout_s: float = 120.0,
) -> tuple[subprocess.Popen[bytes], dict, subprocess.Popen[bytes], dict]:
    """Starts owned API (5690) and UI (4710) atomically; terminates any started child on partial failure."""
    check_api = api_ready_fn or (lambda: http_get_status(API_PORT, "/api/archive?limit=1") == 200)
    check_ui = ui_ready_fn or (lambda: http_get_status(UI_PORT, "/") == 200)

    api_proc: subprocess.Popen[bytes] | None = None
    api_info: dict | None = None
    ui_proc: subprocess.Popen[bytes] | None = None
    ui_info: dict | None = None

    try:
        with api_log_path.open("ab") as afh:
            api_proc = subprocess.Popen(
                api_cmd,
                cwd=str(api_cwd),
                env=api_env,
                stdout=afh,
                stderr=subprocess.STDOUT,
            )
        api_info = inspect_process(api_proc.pid, repo_root)

        api_deadline = time.monotonic() + api_timeout_s
        api_ready = False
        while time.monotonic() < api_deadline:
            if api_proc.poll() is not None:
                raise RuntimeError(f"Owned API exited early with code {api_proc.returncode}")
            try:
                if check_api():
                    api_ready = True
                    break
            except OSError:
                pass
            time.sleep(0.2)
        if not api_ready or api_info is None:
            raise RuntimeError(f"Owned API failed readiness check within {api_timeout_s}s")

        with ui_log_path.open("ab") as ufh:
            ui_proc = subprocess.Popen(
                ui_cmd,
                cwd=str(ui_cwd),
                env=ui_env,
                stdout=ufh,
                stderr=subprocess.STDOUT,
            )
        ui_info = inspect_process(ui_proc.pid, repo_root)

        ui_deadline = time.monotonic() + ui_timeout_s
        ui_ready = False
        while time.monotonic() < ui_deadline:
            if api_proc.poll() is not None:
                raise RuntimeError(f"Owned API exited unexpectedly during UI startup ({api_proc.returncode})")
            if ui_proc.poll() is not None:
                raise RuntimeError(f"Owned UI exited early with code {ui_proc.returncode}")
            try:
                if check_ui():
                    ui_ready = True
                    break
            except OSError:
                pass
            time.sleep(0.25)
        if not ui_ready or ui_info is None:
            raise RuntimeError(f"Owned UI failed readiness check within {ui_timeout_s}s")

        return api_proc, api_info, ui_proc, ui_info
    except BaseException:
        stop_owned_process(ui_proc, ui_info, repo_root)
        stop_owned_process(api_proc, api_info, repo_root)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconciled WP-0012 reviewer helper v4 (CPU contract check & held /004 live mode).")
    parser.add_argument("--mode", choices=("validate-release-cpu", "live-leased-rehearsal"), required=True)
    parser.add_argument("--release-commit", required=True, help="40-hex coordinator Git commit containing the release JSON")
    parser.add_argument("--release-path", required=True, help="Git-relative path under docs/coordination/WP-0012*/*.json")
    parser.add_argument("--summary-output", required=True, help="New non-existing JSON path for summary receipt")
    parser.add_argument("--q0-check-output", default="", help="New non-existing JSON path for Q0 manifest check (required for live mode)")
    parser.add_argument("--resource-return-output", default="", help="New non-existing JSON path for resource-return receipt (required for live mode)")
    parser.add_argument("--logs-dir", default="", help="New empty/non-existing directory for sanitized logs (required for live mode)")
    parser.add_argument("--screenshots-dir", default="", help="New empty/non-existing directory for screenshots (required for live mode)")
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    edge_driver = (
        repo_root / "docs" / "reviews" / "WP-0012" / "eld-f4-reviewer" / "preparation" / "helpers" / "drive_wp0012_edge_workflow.mjs"
    ).resolve()

    def _res_arg(val: str) -> Path:
        pv = Path(val)
        return pv.resolve() if pv.is_absolute() else (repo_root / pv).resolve()

    summary_out = _res_arg(args.summary_output)

    try:
        if args.mode == "live-leased-rehearsal":
            if not (args.q0_check_output and args.resource_return_output and args.logs_dir and args.screenshots_dir):
                raise ReviewerLeaseGuardError(
                    "live-leased-rehearsal requires explicit new --q0-check-output, --resource-return-output, --logs-dir, and --screenshots-dir."
                )
            q0_out = _res_arg(args.q0_check_output)
            rr_out = _res_arg(args.resource_return_output)
            logs_dir = _res_arg(args.logs_dir)
            shots_dir = _res_arg(args.screenshots_dir)
            p1_out = summary_out.parent / "edge-live-phase1.json"
            p2_out = summary_out.parent / "edge-live-phase2-post-restart.json"
            guard_new_non_overwriting_output_targets(
                repo_root,
                file_targets=[summary_out, p1_out, p2_out, q0_out, rr_out],
                dir_targets=[logs_dir, shots_dir],
            )
        else:
            guard_new_non_overwriting_output_targets(repo_root, file_targets=[summary_out], dir_targets=[])

        rc = args.release_commit.strip().lower()
        rel_norm = args.release_path.strip().replace("\\", "/")
        if not HEX40_RE.match(rc) or not git_object_exists(repo_root, f"{rc}:{rel_norm}"):
            raise ReviewerLeaseGuardError(f"Coordinator release Git object not found: {rc}:{rel_norm}")

        rel_doc = json.loads(git_bytes(repo_root, "cat-file", "-p", f"{rc}:{rel_norm}").decode("utf-8"))
        validated = validate_reviewer_release_contract(
            rel_doc,
            repo_root=repo_root,
            release_commit=rc,
            release_path=rel_norm,
            now_utc=datetime.now(timezone.utc),
            blob_loader=lambda p: git_bytes(repo_root, "cat-file", "-p", f"{rc}:{p}"),
            commit_exists_fn=lambda sha: git_object_exists(repo_root, f"{sha}^{{commit}}"),
            helper_paths_to_bind=(script_path, edge_driver),
            require_clean_worktree=True,
            allow_synthetic_test_only=False,
        )

        if args.mode == "validate-release-cpu":
            summary_out.parent.mkdir(parents=True, exist_ok=True)
            out_doc = {k: v for k, v in validated.items() if k != "parsed_pre_lease_blobs"}
            summary_out.write_text(json.dumps(out_doc, indent=2) + "\n", encoding="utf-8", newline="\n")
            return 0

        # HELD `/004` live-leased-rehearsal path (executed ONLY after accepting /007 + author /003 + clean author lease return + reviewer GPU lease)
        sys.path.insert(0, str((repo_root / "docs/reviews/WP-0012/eld-f4-reviewer/preparation/helpers").resolve()))
        import run_wp0012_reviewer_rehearsal as prep_mod  # type: ignore

        for d in (summary_out.parent, q0_out.parent, rr_out.parent, logs_dir, shots_dir):
            d.mkdir(parents=True, exist_ok=True)

        pre_snap = collect_live_ownership_snapshot(repo_root)
        pre_ownership = evaluate_gpu_and_model_ownership(
            pre_snap,
            pre_lease_blobs=validated["parsed_pre_lease_blobs"],
        )

        q0_pre = prep_mod.verify_q0_readonly_pure_stdlib(repo_root)
        q0_out.write_text(json.dumps(q0_pre, indent=2) + "\n", encoding="utf-8", newline="\n")
        if q0_pre["demo_root_bytes"] > STORAGE_CAP_BYTES or q0_pre["demo_drive_free_bytes"] < MIN_FREE_DISK_BYTES:
            raise ReviewerLeaseGuardError(
                f"Demo disk/storage bounds failed: bytes={q0_pre['demo_root_bytes']}, free={q0_pre['demo_drive_free_bytes']}"
            )

        ports_before = observe_ports(REVIEWER_PORTS, repo_root)
        if any(len(ports_before[str(p)]) != 0 for p in REVIEWER_PORTS):
            raise ReviewerLeaseGuardError(f"Owned reviewer ports not idle before start: {ports_before}")

        local_dir = repo_root / ".local"
        settings = json.loads((local_dir / "secrets" / "pg-local.json").read_text(encoding="utf-8"))
        secrets = [
            str(settings["adminPassword"]),
            str(settings["migratorPassword"]),
            str(settings["appPassword"]),
        ]
        psql_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "psql.exe"
        pg_ctl_exe = local_dir / "tools" / "pgsql-18.7-1" / "bin" / "pg_ctl.exe"
        pg_data_dir = local_dir / "postgres-data"
        api_dll = repo_root / "src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll"
        node_exe = Path(shutil.which("node") or "node")
        runs_dir = WRITABLE_DEMO_ROOT / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

        api_proc: subprocess.Popen[bytes] | None = None
        api_info: dict | None = None
        ui_proc: subprocess.Popen[bytes] | None = None
        ui_info: dict | None = None
        pg_started = False
        postmaster_info: dict | None = None
        api_stop_receipts: list[dict] = []
        ui_stop_receipts: list[dict] = []
        persisted_counts: dict = {}
        run_error: BaseException | None = None
        cleanup_errors: list[str] = []
        rr_doc: dict = {}

        api_log = logs_dir / "owned-api-5690.log"
        ui_log = logs_dir / "owned-ui-4710.log"

        try:
            start_pg = run_cmd(
                ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/start-cluster.ps1")],
                cwd=repo_root,
            )
            if start_pg.returncode != 0:
                raise RuntimeError(f"start-cluster.ps1 failed: {start_pg.stderr}")
            pg_started = True
            pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
            postmaster_info = inspect_process(pm_pid, repo_root)

            demo_pre = prep_mod.compute_canonical_8table_snapshot(psql_exe, settings, DEMO_DATABASE, repo_root)
            if any(v != 0 for v in demo_pre["counts"].values()) or list(runs_dir.iterdir()) != []:
                raise ReviewerLeaseGuardError("Refusing live /004 run: demo DB or runs directory is non-empty.")

            app_conn = (
                f"Host={settings['host']};Port={PG_PORT};Database={DEMO_DATABASE};"
                f"Username={settings['appUser']};Password={settings['appPassword']}"
            )
            api_env_leased = {
                **os.environ,
                "ASPNETCORE_ENVIRONMENT": "Production",
                "DOTNET_NOLOGO": "1",
                "Api__Port": str(API_PORT),
                "LocalOcr__Enabled": "true",
                "LocalOcr__MaxExtractionPages": "3",
                "LocalOcr__WorkerRootPath": str(repo_root / "workers" / "local_ocr"),
                "LocalOcr__ReadOnlyQ0Root": str(READONLY_Q0_ROOT),
                "LocalOcr__WritableRuntimeRoot": str(WRITABLE_DEMO_ROOT),
                "LocalOcr__LeasedGpuUuid": EXPECTED_GPU_UUID,
                "ConnectionStrings__Runtime": app_conn,
            }
            ui_env = {**os.environ, "ELEDGERCARE_API_PORT": str(API_PORT), "NG_CLI_ANALYTICS": "false"}

            api_proc, api_info, ui_proc, ui_info = start_owned_services_atomic(
                api_cmd=["dotnet", str(api_dll)],
                api_cwd=api_dll.parent,
                api_env=api_env_leased,
                api_log_path=api_log,
                ui_cmd=[
                    str(node_exe),
                    "node_modules/@angular/cli/bin/ng.js",
                    "serve",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(UI_PORT),
                    "--proxy-config",
                    "proxy.conf.mjs",
                ],
                ui_cwd=repo_root / "web",
                ui_env=ui_env,
                ui_log_path=ui_log,
                repo_root=repo_root,
            )

            p1_cp = run_cmd(
                [
                    str(node_exe),
                    str(edge_driver),
                    "--mode",
                    "live-phase1-leased",
                    "--ui-port",
                    str(UI_PORT),
                    "--api-port",
                    str(API_PORT),
                    "--output",
                    str(p1_out),
                    "--screenshot-dir",
                    str(shots_dir),
                ],
                cwd=repo_root,
                timeout_s=5600,
            )
            (logs_dir / "01-edge-live-phase1.log").write_text(
                redact_secrets(p1_cp.stdout + p1_cp.stderr, secrets), encoding="utf-8", newline="\n"
            )
            if p1_cp.returncode != 0:
                raise RuntimeError(f"Phase 1 live Edge workflow stopped/failed (exit {p1_cp.returncode})")
            p1_data = json.loads(p1_out.read_text(encoding="utf-8"))

            ui_stop_receipts.append(stop_owned_process(ui_proc, ui_info, repo_root))
            ui_proc, ui_info = None, None
            api_stop_receipts.append(stop_owned_process(api_proc, api_info, repo_root))
            api_proc, api_info = None, None

            stop_mid = run_cmd(["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/stop-cluster.ps1")], cwd=repo_root)
            if stop_mid.returncode != 0:
                raise RuntimeError(f"Mid-run stop-cluster.ps1 failed: {stop_mid.stderr}")
            pg_started = False
            start_mid = run_cmd(["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/start-cluster.ps1")], cwd=repo_root)
            if start_mid.returncode != 0:
                raise RuntimeError(f"Mid-run start-cluster.ps1 failed: {start_mid.stderr}")
            pg_started = True
            pm_pid = int((pg_data_dir / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0].strip())
            postmaster_info = inspect_process(pm_pid, repo_root)

            api_env_disabled = {
                **os.environ,
                "ASPNETCORE_ENVIRONMENT": "Production",
                "DOTNET_NOLOGO": "1",
                "Api__Port": str(API_PORT),
                "LocalOcr__Enabled": "false",
                "LocalOcr__MaxExtractionPages": "3",
                "LocalOcr__WorkerRootPath": str(repo_root / "workers" / "local_ocr"),
                "ConnectionStrings__Runtime": app_conn,
            }
            api_proc, api_info, ui_proc, ui_info = start_owned_services_atomic(
                api_cmd=["dotnet", str(api_dll)],
                api_cwd=api_dll.parent,
                api_env=api_env_disabled,
                api_log_path=api_log,
                ui_cmd=[
                    str(node_exe),
                    "node_modules/@angular/cli/bin/ng.js",
                    "serve",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(UI_PORT),
                    "--proxy-config",
                    "proxy.conf.mjs",
                ],
                ui_cwd=repo_root / "web",
                ui_env=ui_env,
                ui_log_path=ui_log,
                repo_root=repo_root,
            )

            p2_cp = run_cmd(
                [
                    str(node_exe),
                    str(edge_driver),
                    "--mode",
                    "live-phase2-post-restart",
                    "--wo-document-id",
                    p1_data["woDocument"]["documentId"],
                    "--mp-document-id",
                    p1_data["mpDocument"]["documentId"],
                    "--ui-port",
                    str(UI_PORT),
                    "--api-port",
                    str(API_PORT),
                    "--output",
                    str(p2_out),
                    "--screenshot-dir",
                    str(shots_dir),
                ],
                cwd=repo_root,
                timeout_s=240,
            )
            (logs_dir / "02-edge-live-phase2-post-restart.log").write_text(
                redact_secrets(p2_cp.stdout + p2_cp.stderr, secrets), encoding="utf-8", newline="\n"
            )
            if p2_cp.returncode != 0:
                raise RuntimeError(f"Phase 2 post-restart Edge workflow failed (exit {p2_cp.returncode})")

        except BaseException as exc:
            run_error = exc
        finally:
            if ui_proc is not None:
                try:
                    ui_stop_receipts.append(stop_owned_process(ui_proc, ui_info, repo_root))
                except Exception as u_exc:
                    cleanup_errors.append(f"ui_stop_failed: {u_exc}")
            if api_proc is not None:
                try:
                    api_stop_receipts.append(stop_owned_process(api_proc, api_info, repo_root))
                except Exception as a_exc:
                    cleanup_errors.append(f"api_stop_failed: {a_exc}")
            if pg_started:
                try:
                    snap_final = prep_mod.compute_canonical_8table_snapshot(psql_exe, settings, DEMO_DATABASE, repo_root)
                    persisted_counts = snap_final["counts"]
                except Exception as q_exc:
                    cleanup_errors.append(f"final_db_snapshot_failed: {q_exc}")
                stop_pg = run_cmd(
                    ["pwsh", "-NoProfile", "-File", str(repo_root / "deploy/dev/postgres/stop-cluster.ps1")],
                    cwd=repo_root,
                )
                (logs_dir / "99-pg-cluster-stop.log").write_text(
                    redact_secrets(stop_pg.stdout + stop_pg.stderr, secrets), encoding="utf-8", newline="\n"
                )
                if stop_pg.returncode != 0:
                    cleanup_errors.append(f"stop_cluster_failed={stop_pg.returncode}")

            for lf in logs_dir.glob("*.log"):
                cleaned = redact_secrets(lf.read_text(encoding="utf-8", errors="replace"), secrets)
                lf.write_text(cleaned.replace("\r\n", "\n"), encoding="utf-8", newline="\n")

            pg_rc = run_cmd([str(pg_ctl_exe), "status", "-D", str(pg_data_dir)], cwd=repo_root).returncode
            ports_after = observe_ports(REVIEWER_PORTS, repo_root)
            try:
                post_snap = collect_live_ownership_snapshot(repo_root)
                post_ownership = evaluate_gpu_and_model_ownership(
                    post_snap,
                    pre_lease_blobs=validated["parsed_pre_lease_blobs"],
                )
            except Exception as exc_own:
                post_ownership = {"sole_model_job_verified": False, "error": str(exc_own)}

            q0_immutable = False
            try:
                q0_post = prep_mod.verify_q0_readonly_pure_stdlib(repo_root)
                q0_immutable = q0_post["verified_model_files"] == q0_pre["verified_model_files"]
            except Exception as q0_exc:
                cleanup_errors.append(f"q0_post_check_failed: {q0_exc}")

            rr_doc = build_reviewer_lease_return_receipt(
                lease_id=validated["lease_id"],
                run_error=str(run_error) if run_error is not None else None,
                cleanup_errors=cleanup_errors,
                ports_after=ports_after,
                pg_ctl_status_exit_code=pg_rc,
                api_stop_receipts=api_stop_receipts,
                ui_stop_receipts=ui_stop_receipts,
                pre_ownership=pre_ownership,
                post_ownership=post_ownership,
                q0_model_immutability_verified=q0_immutable,
                persisted_counts=persisted_counts,
                run_directories=sorted(p.name for p in runs_dir.iterdir()) if runs_dir.is_dir() else [],
                postmaster_recorded=postmaster_info,
                secrets=secrets,
            )
            rr_out.write_text(json.dumps(rr_doc, indent=2) + "\n", encoding="utf-8", newline="\n")

        if not rr_doc.get("clean_return_verified", False):
            msg = f"CLEANUP FAILED — LEASE REMAINS UNRETURNED: {rr_doc.get('cleanup_errors')}"
            if run_error is not None:
                raise ReviewerLeaseGuardError(f"{msg} (after workflow failure: {run_error})") from run_error
            raise ReviewerLeaseGuardError(msg)
        if run_error is not None:
            raise run_error

        summary_doc = {
            "schema": "eledgercare.wp-0012.reviewer-live-summary/3",
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "lease_id": validated["lease_id"],
            "persisted_counts": persisted_counts,
            "pre_ownership": pre_ownership,
        }
        summary_out.write_text(json.dumps(summary_doc, indent=2) + "\n", encoding="utf-8", newline="\n")
        return 0

    except (ReviewerLeaseGuardError, FileExistsError) as exc:
        print(f"Refusing or halting live-leased-rehearsal: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
