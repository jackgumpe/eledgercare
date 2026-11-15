"""Frozen Q0 protocol: loading, structural validation, dev-only fixture policy, call freeze."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

from .hashing import is_hex, sha256_bytes
from .outcome import Q0Failure

HARNESS_DIR = Path(__file__).resolve().parent.parent          # qualification/q0/harness
REPO_ROOT = HARNESS_DIR.parent.parent.parent                    # repository/worktree root
PROTOCOL_PATH = HARNESS_DIR / "protocol.json"

MODEL_REVISION = "0480966938291445591f69f08a13b041c073a96a"
POSTPROCESSOR_COMMIT = "3de5de31a7e5c925e84af68ef12b1b8d7db9e24a"
HOLDOUT_FAMILIES = frozenset({"F03", "F05", "F06", "F08"})
DEV_FIXTURE_PATHS = {
    "SYN-WO-01-v0-clean": "evaluation/synthetic/pdfs/F01/SYN-WO-01-v0-clean.pdf",
    "SYN-MP-01-v0-clean": "evaluation/synthetic/pdfs/F07/SYN-MP-01-v0-clean.pdf",
}
FORBIDDEN_PREFIXES = ("evaluation/synthetic/expected/", "evaluation/synthetic/sources/")

# Exact key set passed to infer_multi besides tokenizer/prompt/image_files. Values for
# the fixed keys are checked exactly; per-fixture keys are derived by documented rules.
FROZEN_FIXED_KWARGS = {
    "crop_mode": False,
    "save_results": False,
    "output_path": "",
    "temperature": 0.0,
    "max_length": 131072,
    "max_page_tokens": 20000,
    "page_count_guard": True,
    "image_size": 640,
    "base_size": 1024,
    "max_crops": 16,
    "no_repeat_ngram_size": 35,
    "ngram_whitelist_token_ids": None,
    "dash_topm": 16,
    "tps_interval": 0,
    "test_compress": False,
    "eval_mode": False,
}
PER_FIXTURE_KWARGS = ("max_new_tokens", "ngram_window")
TOKENS_PER_PAGE = 8000


def load_protocol(path: Path = PROTOCOL_PATH) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    protocol = json.loads(raw.decode("utf-8"))
    validate_protocol(protocol)
    return protocol, sha256_bytes(raw)


def check_repo_path_allowed(rel: str) -> str:
    """Normalize a repository-relative path and refuse holdout/expected/source access."""
    p = PurePosixPath(rel.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or re.match(r"^[A-Za-z]:", rel) or rel.startswith(("/", "\\")):
        raise Q0Failure("HOLDOUT_ACCESS_REFUSED", f"non-relative or escaping path refused: {rel!r}")
    norm = str(p)
    for prefix in FORBIDDEN_PREFIXES:
        if norm.startswith(prefix) or (norm + "/").startswith(prefix):
            raise Q0Failure("HOLDOUT_ACCESS_REFUSED", f"expected-value/source path refused: {norm}")
    m = re.match(r"^evaluation/synthetic/pdfs/(F\d\d)/", norm)
    if m and m.group(1) in HOLDOUT_FAMILIES:
        raise Q0Failure("HOLDOUT_ACCESS_REFUSED", f"holdout family {m.group(1)} refused: {norm}")
    return norm


def ngram_window_for(page_count: int) -> int:
    # Upstream README evaluation setup: window_size = 1024 if len(pages) > 1 else 128.
    return 1024 if page_count > 1 else 128


def max_new_tokens_for(page_count: int) -> int:
    return TOKENS_PER_PAGE * page_count


def build_call_kwargs(protocol: dict, fixture: dict) -> dict:
    kwargs = dict(protocol["call"]["fixed_kwargs"])
    kwargs["max_new_tokens"] = fixture["max_new_tokens"]
    kwargs["ngram_window"] = fixture["ngram_window"]
    validate_call_kwargs(kwargs, fixture["page_count"])
    return kwargs


def validate_call_kwargs(kwargs: dict, page_count: int) -> None:
    expected_keys = set(FROZEN_FIXED_KWARGS) | set(PER_FIXTURE_KWARGS)
    if set(kwargs) != expected_keys:
        raise Q0Failure("SAFETY_VIOLATION", "infer_multi kwargs differ from the frozen key set",
                        {"missing": sorted(expected_keys - set(kwargs)), "extra": sorted(set(kwargs) - expected_keys)})
    for key, value in FROZEN_FIXED_KWARGS.items():
        got = kwargs[key]
        if type(got) is not type(value) or got != value:
            raise Q0Failure("SAFETY_VIOLATION", f"frozen kwarg {key} must be {value!r}, got {got!r}")
    if kwargs["max_new_tokens"] != max_new_tokens_for(page_count):
        raise Q0Failure("SAFETY_VIOLATION", "max_new_tokens differs from 8000 * page_count")
    if kwargs["ngram_window"] != ngram_window_for(page_count):
        raise Q0Failure("SAFETY_VIOLATION", "ngram_window differs from the frozen page-count rule")


def check_context_budget(prompt_len: int, max_new_tokens: int, max_length: int) -> None:
    if prompt_len <= 0 or prompt_len + max_new_tokens > max_length:
        raise Q0Failure("CONTEXT_BUDGET_EXCEEDED",
                        f"prompt_len {prompt_len} + max_new_tokens {max_new_tokens} > max_length {max_length}")


def schedule(protocol: dict) -> list[dict]:
    """Cold load is separate; then one excluded warmup per fixture, then exactly two
    interleaved warm repeats per fixture: W(F01) W(F07) R1(F01) R1(F07) R2(F01) R2(F07)."""
    seq = protocol["sequence"]
    order = seq["fixture_order"]
    plan = [{"fixture_id": fid, "kind": "warmup", "repeat": 0, "excluded": True} for fid in order]
    for r in range(1, seq["warm_repeats_per_fixture"] + 1):
        plan += [{"fixture_id": fid, "kind": "warm", "repeat": r, "excluded": False} for fid in order]
    return plan


def validate_protocol(protocol: dict) -> None:
    def fail(msg, evidence=None):
        raise Q0Failure("SAFETY_VIOLATION", f"protocol invalid: {msg}", evidence)

    if protocol.get("schema") != "eldq0-protocol/1":
        fail("schema")
    model = protocol["model"]
    if model["repo_id"] != "baidu/Unlimited-OCR-2" or model["revision"] != MODEL_REVISION:
        fail("model pin")
    if model["torch_dtype"] != "bfloat16":
        fail("dtype")
    load = model["load"]
    if load != {"trust_remote_code": True, "use_safetensors": True, "local_files_only": True,
                "then": ["eval", "cuda"]}:
        fail("load recipe", load)
    if protocol["postprocessor"]["commit"] != POSTPROCESSOR_COMMIT or protocol["postprocessor"]["executed_in_q0"]:
        fail("postprocessor pin / not executed in Q0")
    r = protocol["renderer"]
    if (r["distribution"], r["version"], r["pdfium_version"]) != ("pypdfium2", "5.15.2", "159.0.8149.0"):
        fail("renderer pin")
    if (r["scale_numerator"], r["scale_denominator"]) != (300.0, 72.0) or r["input"] != "verified_pdf_bytes":
        fail("render scale/input")
    if set(protocol["holdout_families"]) != HOLDOUT_FAMILIES:
        fail("holdout families")

    call = protocol["call"]
    if call["entry"] != "infer_multi" or call["prompt"] != "Multi page parsing.":
        fail("entry/prompt")
    if call["fixed_kwargs"] != FROZEN_FIXED_KWARGS:
        fail("fixed kwargs", call["fixed_kwargs"])
    for k, v in FROZEN_FIXED_KWARGS.items():
        if type(call["fixed_kwargs"][k]) is not type(v):
            fail(f"fixed kwarg type {k}")
    if tuple(call["per_fixture_kwargs"]) != PER_FIXTURE_KWARGS or call["tokens_per_page"] != TOKENS_PER_PAGE:
        fail("per-fixture rules")

    fixtures = protocol["fixtures"]
    ids = [f["fixture_id"] for f in fixtures]
    if ids != list(DEV_FIXTURE_PATHS):
        fail("fixture set must be exactly F01 and F07 v0-clean", ids)
    for f in fixtures:
        if f["split"] != "dev" or f["family_id"] in HOLDOUT_FAMILIES or f["variant_kind"] != "v0_clean":
            fail(f"fixture policy {f['fixture_id']}")
        if check_repo_path_allowed(f["path"]) != DEV_FIXTURE_PATHS[f["fixture_id"]]:
            fail(f"fixture path {f['fixture_id']}")
        if not (is_hex(f["sha256"], 64) and is_hex(f["git_blob_oid"], 40)):
            fail(f"fixture digests {f['fixture_id']}")
        if f["max_new_tokens"] != max_new_tokens_for(f["page_count"]) or f["ngram_window"] != ngram_window_for(f["page_count"]):
            fail(f"fixture budget rule {f['fixture_id']}")
        rasters = f["raster"]
        if [p["page"] for p in rasters] != list(range(1, f["page_count"] + 1)):
            fail(f"raster pages {f['fixture_id']}")
        for p in rasters:
            if (p["width"], p["height"]) != (2550, 3301) or not is_hex(p["rgb_sha256"], 64):
                fail(f"raster contract {f['fixture_id']} p{p['page']}")
        src = f["raster_derivation"]
        check_repo_path_allowed(src["v1_raster300_path"])
        if not is_hex(src["v1_raster300_sha256"], 64):
            fail("raster derivation source digest")

    seq = protocol["sequence"]
    if (seq["cold_load"], seq["warmup_per_fixture"], seq["warm_repeats_per_fixture"], seq["order"]) != (1, 1, 2, "interleaved"):
        fail("sequence must be one cold load, one excluded warmup and exactly two warm repeats per fixture")
    if seq["fixture_order"] != ids:
        fail("fixture order")

    g = protocol["guards"]
    for key in ("preflight", "load", "call_pages_1", "call_pages_3", "session"):
        if not (isinstance(g["timeouts_s"][key], int) and g["timeouts_s"][key] > 0):
            fail(f"timeout {key}")
    for key in ("stall_s", "max_log_bytes", "max_raw_output_bytes", "heartbeat_interval_s"):
        if not (isinstance(g[key], int) and g[key] > 0):
            fail(f"guard {key}")
    if g["heartbeat_interval_s"] * 4 > g["stall_s"]:
        fail("stall window must cover several heartbeats")

    gpu = protocol["gpu"]
    if not re.fullmatch(r"GPU-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", gpu["uuid"]):
        fail("gpu uuid")
    if gpu["concurrency"] != 1:
        fail("concurrency must be 1")
    obs = gpu["observer"]
    if len(obs["commands"]) != 2 or any(c[0] != "nvidia-smi" or f"--id={gpu['uuid']}" not in c for c in obs["commands"]):
        fail("observer must be two read-only nvidia-smi queries bound to the leased GPU uuid")
    if any(sum(a.startswith(("--query-gpu", "--query-compute-apps")) for a in c) != 1 for c in obs["commands"]):
        fail("each observer command must contain exactly one query mode")
    if not any(a == "--query-gpu=" + ",".join(obs["gpu_fields"]) for a in obs["commands"][0]):
        fail("observer gpu_fields must match the gpu query")

    st = protocol["storage"]
    leaf = PurePosixPath(st["subdirs"]["models"].replace("\\", "/")).name
    if not leaf.isidentifier():
        fail("model directory basename must be a Python identifier")
    fs = st["free_space"]
    if not (isinstance(fs["initial_min_bytes"], int) and isinstance(fs["during_min_bytes"], int)
            and fs["initial_min_bytes"] > fs["during_min_bytes"] > 0):
        fail("free-space floors")
    if protocol.get("baseline_label") != "unmodified model on non-Triton fallback path":
        fail("baseline label")


def storage_path(protocol: dict, key: str):
    import os
    return os.path.join(protocol["storage"]["root"], protocol["storage"]["subdirs"][key])


def fixture_by_id(protocol: dict, fixture_id: str) -> dict:
    for f in protocol["fixtures"]:
        if f["fixture_id"] == fixture_id:
            return f
    raise Q0Failure("HOLDOUT_ACCESS_REFUSED", f"fixture not in the frozen dev allowlist: {fixture_id}")


def call_timeout_s(protocol: dict, page_count: int) -> int:
    key = f"call_pages_{page_count}"
    if key not in protocol["guards"]["timeouts_s"]:
        raise Q0Failure("SAFETY_VIOLATION", f"no frozen call timeout for {page_count} pages")
    return protocol["guards"]["timeouts_s"][key]
