"""Deterministic CPU-only verification helper for WP-0008 /002 F3 design and worker README review.

Inspects Git lineage, tree/report preservation, worker README offline-library claims vs. actual
runner/worker source and worker_source_sha256 invariance, genuine F2 seed artifacts, a pure-stdlib
feasibility model of SafeNativeDisplayParser + WorkOrderReviewSuggestions (including raw table-span
rejection and text/ambiguity bounds), optimistic concurrency / idempotent replay ordering (including
at the 128-revision cap), port disjointness, sealed WP-0009 non-access, and local Markdown links.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PACKET_BASE_SHA = "5e1241d6d365d664f12619d415f48ec3d3b7ddca"
AUTHORITY_SHA = "22b88bc32d053231678aef88e6b7f76d3e61910a"
DESIGN_CANDIDATE_SHA = "c5b5db3af96abf155c806082583b8a92c687f54d"
ROOT_REPORT_001_SHA = "30bb49ed56c32bda61a6907d49bd183e7b292268"
ACCEPTED_F2_SOURCE_SHA = "8a73b7a5dab51e3ccf803aceedded4929529dd35"
ACCEPTED_F2_REVIEW_004_SHA = "c854a1d4c306c3b10d78df42a1a2552a06bb4a98"

EXPECTED_WORKER_SOURCE_SHA256 = "c1c324c36e27f57c3c4ac4a1462984fbe586ad43ab82af3a2883bb7eac4c0d54"
F01_PDF_SHA256 = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd"
F01_RAW_SHA256 = "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95"
F07_PDF_SHA256 = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3"
F07_RAW_SHA256 = "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639"
F1_PDF_SHA256 = "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb"

FORBIDDEN_PATH_SUBSTRINGS = (
    "eledgercare-mapping",
    "wp-0009/sealed",
    "wp-0009\\sealed",
    "wp-0009-fresh-families",
    "eld-eval-custodian",
)

EXPECTED_CANDIDATE_DIFF = {
    "AGENTS.md": "M",
    "CURRENT.md": "M",
    "INDEX.md": "M",
    "docs/coordination/WP-0008-0009-authority.md": "A",
    "docs/coordination/WP-0008/initial-native-dispatch.json": "A",
    "docs/design/F3-review-correction.md": "A",
    "docs/kickoffs/WP-0008-eld-f3-reviewer-design.md": "A",
    "docs/kickoffs/WP-0009-eld-eval-custodian.md": "A",
    "docs/kickoffs/WP-0009-eld-mapping-author-diagnosis.md": "A",
    "docs/kickoffs/WP-0009-eld-mapping-reviewer.md": "A",
    "workers/local_ocr/README.md": "M",
}

PRESERVED_TREE_PATHS = (
    "src",
    "tests",
    "web",
    "deploy",
    "ELedgerCare.slnx",
    "workers/ocr",
    "workers/local_ocr/run_worker.py",
    "workers/local_ocr/local_ocr",
    "workers/local_ocr/manifests",
    "workers/local_ocr/tests",
    "evaluation",
    "qualification",
)

FIELD_SPECS = (
    ("work_order_id", "Work Order ID", 64, False),
    ("property_name", "Property", 200, False),
    ("building_unit", "Building / Unit", 120, False),
    ("requested_date", "Requested Date", 64, False),
    ("issue_and_resolution", "REPORTED SYMPTOM & TECHNICIAN RESOLUTION SUMMARY", 4000, True),
)
LABEL_TO_FIELD = {label: (fid, cap, multiline) for fid, label, cap, multiline in FIELD_SPECS}


class SafeRepoReader:
    """Enforces read-only access inside the owned reviewer worktree and blocks WP-0009 sealed paths."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.opened_paths: list[str] = []

    def _guard(self, path: Path) -> Path:
        resolved = path.resolve()
        norm = str(resolved).lower()
        for bad in FORBIDDEN_PATH_SUBSTRINGS:
            if bad in norm:
                raise PermissionError(f"Refusing forbidden sealed/WP-0009 path: {resolved}")
        try:
            rel = resolved.relative_to(self.repo_root).as_posix()
        except ValueError as exc:
            raise PermissionError(f"Refusing path outside owned worktree: {resolved}") from exc
        self.opened_paths.append(rel)
        return resolved

    def read_bytes(self, rel_path: str) -> bytes:
        target = self._guard(self.repo_root / rel_path)
        return target.read_bytes()

    def read_text(self, rel_path: str) -> str:
        return self.read_bytes(rel_path).decode("utf-8")


def run_git(repo_root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.stdout.strip()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utf16_code_units(text: str) -> int:
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def has_valid_review_text(text: str, *, max_utf16: int, multiline: bool) -> bool:
    if utf16_code_units(text) > max_utf16:
        return False
    for ch in text:
        code = ord(ch)
        if 0xD800 <= code <= 0xDFFF or code == 0:
            return False
        if multiline and ch in ("\r", "\n", "\t"):
            continue
        if code < 0x20 or 0x7F <= code <= 0x9F:
            return False
    return True


def decode_basic_entities(value: str) -> str:
    if "&" not in value:
        return value
    return (
        value.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&#x27;", "'")
        .replace("&#X27;", "'")
        .replace("&amp;", "&")
    )


def parse_plain_table_rows_f2(table_markup: str) -> list[list[str]]:
    """Exact mirror of SafeNativeDisplayParser.ParsePlainTableRows in Domain."""
    rows: list[list[str]] = []
    current_row: list[str] | None = None
    current_cell: list[str] | None = None
    i = 0
    n = len(table_markup)
    while i < n:
        lt = table_markup.find("<", i)
        if lt < 0:
            if current_cell is not None:
                current_cell.append(decode_basic_entities(table_markup[i:]))
            break
        if lt > i and current_cell is not None:
            current_cell.append(decode_basic_entities(table_markup[i:lt]))
        gt = table_markup.find(">", lt + 1)
        if gt < 0:
            if current_cell is not None:
                current_cell.append(table_markup[lt:])
            break
        raw_tag = table_markup[lt + 1 : gt].strip()
        is_closing = raw_tag.startswith("/")
        tag_body = (raw_tag[1:] if is_closing else raw_tag).strip()
        name_end = 0
        while name_end < len(tag_body) and tag_body[name_end].isalnum():
            name_end += 1
        tag_name = tag_body[:name_end].lower()
        if tag_name in ("table", "thead", "tbody", "tfoot"):
            pass
        elif tag_name == "tr":
            if not is_closing:
                current_row = []
            elif current_row is not None:
                if current_cell is not None:
                    current_row.append("".join(current_cell).strip())
                    current_cell = None
                rows.append(current_row)
                current_row = None
        elif tag_name in ("td", "th"):
            if not is_closing:
                if current_row is None:
                    current_row = []
                if current_cell is not None:
                    current_row.append("".join(current_cell).strip())
                current_cell = []
            elif current_cell is not None:
                if current_row is None:
                    current_row = []
                current_row.append("".join(current_cell).strip())
                current_cell = None
        elif tag_name == "br":
            if current_cell is not None:
                current_cell.append("\n")
        else:
            if current_cell is not None:
                current_cell.append(table_markup[lt : gt + 1])
        i = gt + 1
    if current_cell is not None:
        if current_row is None:
            current_row = []
        current_row.append("".join(current_cell).strip())
    if current_row:
        rows.append(current_row)
    return rows


def parse_strict_simple_two_cell_rows(table_markup: str) -> list[tuple[int, str, str]]:
    """Strict raw-markup table checker verifying F3-BIC-01 (rejects colspan/rowspan/nested/malformed)."""
    rows: list[tuple[int, str, str]] = []
    table_depth = 0
    in_row = False
    in_cell: str | None = None
    row_has_unsupported = False
    row_cells: list[str] = []
    cell_buf: list[str] = []
    row_index = -1

    i = 0
    n = len(table_markup)
    while i < n:
        lt = table_markup.find("<", i)
        if lt < 0:
            if in_cell is not None:
                return []
            break
        if lt > i and in_cell is not None:
            cell_buf.append(decode_basic_entities(table_markup[i:lt]))
        gt = table_markup.find(">", lt + 1)
        if gt < 0:
            return []
        raw_tag = table_markup[lt + 1 : gt].strip()
        is_closing = raw_tag.startswith("/")
        tag_body = (raw_tag[1:] if is_closing else raw_tag).strip()
        name_end = 0
        while name_end < len(tag_body) and tag_body[name_end].isalnum():
            name_end += 1
        tag_name = tag_body[:name_end].lower()
        attr_text = tag_body[name_end:].strip()

        if tag_name == "table":
            if not is_closing:
                table_depth += 1
                if table_depth > 1:
                    return []
            else:
                table_depth -= 1
                if table_depth < 0:
                    return []
        elif tag_name in ("thead", "tbody", "tfoot"):
            pass
        elif tag_name == "tr":
            if not is_closing:
                if in_row or in_cell is not None:
                    return []
                in_row = True
                row_index += 1
                row_has_unsupported = bool(attr_text)
                row_cells = []
            else:
                if not in_row or in_cell is not None:
                    return []
                if not row_has_unsupported and len(row_cells) == 2:
                    rows.append((row_index, row_cells[0], row_cells[1]))
                in_row = False
        elif tag_name in ("td", "th"):
            if not is_closing:
                if not in_row or in_cell is not None:
                    return []
                if re.search(r"\b(?:colspan|rowspan)\b", attr_text, re.I) or attr_text:
                    row_has_unsupported = True
                in_cell = tag_name
                cell_buf = []
            else:
                if in_cell != tag_name:
                    return []
                row_cells.append("".join(cell_buf).strip())
                in_cell = None
        elif tag_name == "br":
            if in_cell is not None:
                cell_buf.append("\n")
        else:
            if in_cell is not None:
                cell_buf.append(table_markup[lt : gt + 1])
        i = gt + 1

    if table_depth != 0 or in_row or in_cell is not None:
        return []
    return rows


def parse_pages(raw_text: str) -> list[dict]:
    """Mirror of SafeNativeDisplayParser.ParsePages."""
    page_token = "<PAGE>"
    block_token = "<BLOCK>"
    fork_token = "<FORK>"
    positions: list[int] = []
    pos = 0
    while pos <= len(raw_text):
        idx = raw_text.find(page_token, pos)
        if idx < 0:
            break
        positions.append(idx)
        pos = idx + len(page_token)
    pages: list[dict] = []
    for p_idx, start_pos in enumerate(positions):
        c_start = start_pos + len(page_token)
        c_end = positions[p_idx + 1] if p_idx + 1 < len(positions) else len(raw_text)
        page_body = raw_text[c_start:c_end]
        b_positions: list[int] = []
        b_pos = 0
        while b_pos <= len(page_body):
            b_idx = page_body.find(block_token, b_pos)
            if b_idx < 0:
                break
            b_positions.append(b_idx)
            b_pos = b_idx + len(block_token)
        blocks: list[dict] = []
        if not b_positions:
            trimmed = page_body.strip()
            if trimmed:
                blocks.append({"kind": "text", "text": trimmed, "table_rows": None})
        else:
            if b_positions[0] > 0:
                leading = page_body[: b_positions[0]].strip()
                if leading:
                    blocks.append({"kind": "text", "text": leading, "table_rows": None})
            for i, b_start_tok in enumerate(b_positions):
                seg_start = b_start_tok + len(block_token)
                seg_end = b_positions[i + 1] if i + 1 < len(b_positions) else len(page_body)
                segment = page_body[seg_start:seg_end]
                fork_idx = segment.find(fork_token)
                if fork_idx < 0:
                    blocks.append({"kind": "raw", "text": segment.strip(), "table_rows": None})
                    continue
                header = segment[:fork_idx]
                content = segment[fork_idx + len(fork_token) :].rstrip("\r\n")
                k_end = 0
                while k_end < len(header) and header[k_end].isascii() and header[k_end].isalpha():
                    k_end += 1
                kind = header[:k_end].lower() if k_end > 0 else "block"
                if kind == "table" and "<table" in content.lower():
                    blocks.append({
                        "kind": "table",
                        "text": content,
                        "table_rows": parse_plain_table_rows_f2(content),
                    })
                else:
                    blocks.append({
                        "kind": kind,
                        "text": decode_basic_entities(content),
                        "table_rows": None,
                    })
        pages.append({"page_number": p_idx + 1, "blocks": blocks})
    return pages


def strip_outer_and_one_colon(value: str) -> str:
    trimmed = value.strip()
    if trimmed.endswith(":"):
        trimmed = trimmed[:-1]
    return trimmed


def is_recognized_label_block(text: str) -> bool:
    s = strip_outer_and_one_colon(text)
    if s in LABEL_TO_FIELD:
        return True
    trimmed = text.strip()
    for label in LABEL_TO_FIELD:
        if trimmed.startswith(label + ":"):
            return True
    return False


def evaluate_work_order_suggestions(raw_text: str) -> dict[str, dict]:
    """Reference feasibility model of F3-review-correction.md WorkOrderReviewSuggestions."""
    pages = parse_pages(raw_text)
    candidates: dict[str, list[dict]] = {fid: [] for fid, _, _, _ in FIELD_SPECS}

    for page in pages:
        pno = page["page_number"]
        blocks = page["blocks"]
        for b_idx, blk in enumerate(blocks):
            kind = blk["kind"]
            b_text = blk["text"]

            if kind == "table":
                for row_idx, cell0, cell1 in parse_strict_simple_two_cell_rows(b_text):
                    label_key = strip_outer_and_one_colon(cell0)
                    if label_key in LABEL_TO_FIELD and cell1.strip():
                        fid, _, _ = LABEL_TO_FIELD[label_key]
                        candidates[fid].append({
                            "raw_value": cell1,
                            "page_number": pno,
                            "block_ordinal": b_idx,
                            "table_row": row_idx,
                            "table_col": 1,
                            "source_quote": cell1,
                        })
                continue

            if kind == "text":
                trimmed = b_text.strip()
                matched_inline = False
                for label, (fid, _, _) in LABEL_TO_FIELD.items():
                    if trimmed.startswith(label + ":"):
                        raw_after_colon = trimmed[len(label) + 1 :]
                        if raw_after_colon.startswith(":"):
                            # Reject "Label::..." under the single-colon rule rather than suggesting ":..."!
                            matched_inline = True
                            break
                        remainder = raw_after_colon.strip()
                        if remainder:
                            candidates[fid].append({
                                "raw_value": remainder,
                                "page_number": pno,
                                "block_ordinal": b_idx,
                                "table_row": None,
                                "table_col": None,
                                "source_quote": trimmed,
                            })
                            matched_inline = True
                        break
                if matched_inline:
                    continue

            if kind in ("text", "title"):
                label_key = strip_outer_and_one_colon(b_text)
                if label_key in LABEL_TO_FIELD:
                    fid, _, _ = LABEL_TO_FIELD[label_key]
                    if kind == "title" and fid != "issue_and_resolution":
                        continue
                    if b_idx + 1 < len(blocks):
                        nxt = blocks[b_idx + 1]
                        nxt_val = nxt["text"].strip()
                        if (
                            nxt["kind"] == "text"
                            and nxt_val
                            and not is_recognized_label_block(nxt["text"])
                        ):
                            candidates[fid].append({
                                "raw_value": nxt_val,
                                "page_number": pno,
                                "block_ordinal": b_idx + 1,
                                "table_row": None,
                                "table_col": None,
                                "source_quote": nxt["text"],
                            })

    out: dict[str, dict] = {}
    for fid, _, cap, multiline in FIELD_SPECS:
        found = candidates[fid]
        if len(found) == 0:
            out[fid] = {
                "suggestion_status": "missing",
                "suggested_value": None,
                "source_ref": None,
                "competing_refs": [],
                "initial_human_decision": "unreviewed",
            }
        elif len(found) > 1:
            out[fid] = {
                "suggestion_status": "ambiguous",
                "suggested_value": None,
                "source_ref": None,
                "competing_refs": [
                    {k: v for k, v in item.items() if k != "raw_value"} for item in found
                ],
                "initial_human_decision": "unreviewed",
            }
        else:
            cand = found[0]
            val = cand["raw_value"]
            if not val.strip() or not has_valid_review_text(val, max_utf16=cap, multiline=multiline):
                out[fid] = {
                    "suggestion_status": "invalid_or_oversized",
                    "suggested_value": None,
                    "source_ref": None,
                    "competing_refs": [],
                    "initial_human_decision": "unreviewed",
                }
            else:
                out[fid] = {
                    "suggestion_status": "suggested",
                    "suggested_value": val,
                    "source_ref": {k: v for k, v in cand.items() if k != "raw_value"},
                    "competing_refs": [],
                    "initial_human_decision": "unreviewed",
                }
    return out


class ReviewLedgerSimulator:
    """Reference state-machine verifying optimistic concurrency, replay-before-stale, and 128-cap."""

    MAX_REVISIONS = 128

    def __init__(self, doc_id: str, result_id: str, machine_suggestions: dict[str, str | None]) -> None:
        self.doc_id = doc_id
        self.result_id = result_id
        self.live_suggestions = dict(machine_suggestions)
        self.persisted_machine_snapshot: dict[str, str | None] | None = None
        self.current_revision = 0
        self.current_state: str | None = None
        self.revisions: dict[int, dict] = {}
        self.operations: dict[str, tuple[str, int]] = {}

    @staticmethod
    def canonical_digest(payload: dict) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return sha256_hex(encoded)

    def post_revision(self, op_key: str, payload: dict) -> tuple[int, dict]:
        req_digest = self.canonical_digest(payload)
        # 1. Idempotent replay checked BEFORE stale-head rejection and BEFORE 128-revision ceiling!
        if op_key in self.operations:
            saved_digest, saved_rev = self.operations[op_key]
            if saved_digest == req_digest:
                return 200, self.revisions[saved_rev]
            return 409, {"code": "idempotency_key_conflict"}

        if payload["document_id"] != self.doc_id or payload["result_id"] != self.result_id:
            return 422, {"code": "result_binding_mismatch"}

        state = payload["state"]
        if state not in ("draft", "reviewed"):
            return 400, {"code": "invalid_state"}

        snapshot = (
            self.persisted_machine_snapshot
            if self.persisted_machine_snapshot is not None
            else dict(self.live_suggestions)
        )

        fields = payload["fields"]
        if set(fields.keys()) != {fid for fid, _, _, _ in FIELD_SPECS}:
            return 400, {"code": "invalid_field_set"}

        for fid, _, cap, multiline in FIELD_SPECS:
            entry = fields[fid]
            dec = entry["decision"]
            val = entry.get("value")
            reason = entry.get("unknown_reason")
            mach = snapshot[fid]
            if dec == "accepted":
                if mach is None or val != mach or reason is not None:
                    return 422, {"code": "invalid_accepted_decision", "field": fid}
            elif dec == "edited":
                if val is None or not val.strip() or not has_valid_review_text(val, max_utf16=cap, multiline=multiline) or reason is not None:
                    return 422, {"code": "invalid_edited_decision", "field": fid}
            elif dec == "unknown":
                if val is not None:
                    return 422, {"code": "unknown_cannot_assert_value", "field": fid}
                if reason is not None and (not reason.strip() or not has_valid_review_text(reason, max_utf16=500, multiline=True)):
                    return 422, {"code": "invalid_unknown_reason", "field": fid}
            elif dec == "unreviewed":
                if state == "reviewed" or reason is not None:
                    return 422, {"code": "reviewed_requires_complete_decisions", "field": fid}
                if val is not None and (not val.strip() or not has_valid_review_text(val, max_utf16=cap, multiline=multiline)):
                    return 422, {"code": "invalid_draft_value", "field": fid}
            else:
                return 400, {"code": "invalid_decision", "field": fid}

        if payload["expected_revision"] != self.current_revision:
            return 409, {
                "code": "stale_expected_revision",
                "current_revision": self.current_revision,
                "current_state": self.current_state,
            }

        if self.current_revision >= self.MAX_REVISIONS:
            return 409, {"code": "revision_limit_reached", "max_revisions": self.MAX_REVISIONS}

        if self.persisted_machine_snapshot is None:
            self.persisted_machine_snapshot = snapshot

        new_rev = self.current_revision + 1
        record = {
            "revision_number": new_rev,
            "previous_revision_number": self.current_revision if self.current_revision > 0 else None,
            "state": state,
            "operation_key": op_key,
            "request_sha256": req_digest,
            "machine_snapshot": dict(self.persisted_machine_snapshot),
            "fields": json.loads(json.dumps(fields)),
        }
        self.revisions[new_rev] = record
        self.operations[op_key] = (req_digest, new_rev)
        self.current_revision = new_rev
        self.current_state = state
        return 201, record


def compute_worker_source_digest(reader: SafeRepoReader, repo_root: Path) -> str:
    py_rels = ["workers/local_ocr/run_worker.py"]
    local_ocr_dir = repo_root / "workers" / "local_ocr" / "local_ocr"
    py_rels.extend(
        f"workers/local_ocr/local_ocr/{p.name}"
        for p in sorted(local_ocr_dir.glob("*.py"), key=lambda x: x.name)
    )
    h = hashlib.sha256()
    for rel in py_rels:
        normalized = reader.read_bytes(rel).replace(b"\r\n", b"\n")
        f_sha = sha256_hex(normalized)
        rel_within_worker = rel.removeprefix("workers/local_ocr/")
        h.update(f"{rel_within_worker}:{len(normalized)}:{f_sha}\n".encode("utf-8"))
    return h.hexdigest()


def verify_markdown_links(reader: SafeRepoReader, repo_root: Path, md_rel_paths: list[str]) -> list[dict]:
    link_rx = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    checked: list[dict] = []
    for rel in md_rel_paths:
        text = reader.read_text(rel)
        base_dir = (repo_root / rel).parent
        for raw_target in link_rx.findall(text):
            target = raw_target.strip()
            if target.startswith(("http://", "https://", "mailto:", "#", "conversation://")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (base_dir / path_part).resolve()
            norm = str(resolved).lower()
            for bad in FORBIDDEN_PATH_SUBSTRINGS:
                if bad in norm:
                    raise AssertionError(f"Forbidden link target in {rel}: {target}")
            if not resolved.exists():
                raise AssertionError(f"Broken local Markdown link in {rel}: {target} -> {resolved}")
            checked.append({
                "source": rel,
                "target": target,
                "resolved": resolved.relative_to(repo_root).as_posix(),
            })
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify WP-0008 /002 F3 design and worker README review.")
    parser.add_argument("--output", required=True, help="Output JSON receipt path")
    parser.add_argument("--require-clean", action="store_true", help="Require clean git status before writing receipt")
    parser.add_argument("--extra-md", action="append", default=[], help="Additional Markdown path(s) to link-check")
    args = parser.parse_args(argv)

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[5]
    reader = SafeRepoReader(repo_root)
    assertions: list[dict] = []

    def record_assert(name: str, condition: bool, detail: object) -> None:
        if not condition:
            raise AssertionError(f"Check failed ({name}): {detail}")
        assertions.append({"check": name, "passed": True, "detail": detail})

    # 1. Git status, HEAD, lineage, diff inventory, and tree/report preservation
    status_before = run_git(repo_root, "status", "--porcelain", "--untracked-files=normal")
    if args.require_clean:
        record_assert("clean_worktree_before_execution", status_before == "", {"status_porcelain": status_before})

    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    branch_name = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    record_assert("owned_branch_identity", branch_name == "review/wp-0008-f3", {"branch": branch_name, "head": head_sha})

    anc_root = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ROOT_REPORT_001_SHA, head_sha],
        cwd=repo_root,
        check=False,
    ).returncode == 0
    record_assert("dispatch_001_is_ancestor_of_head", anc_root, {"dispatch_001": ROOT_REPORT_001_SHA, "head": head_sha})

    cand_diff_lines = run_git(repo_root, "diff", "--name-status", PACKET_BASE_SHA, DESIGN_CANDIDATE_SHA).splitlines()
    observed_cand_diff = {}
    for line in cand_diff_lines:
        status_tok, path_tok = line.split("\t", 1)
        observed_cand_diff[path_tok] = status_tok
    record_assert(
        "exact_11_path_candidate_diff",
        observed_cand_diff == EXPECTED_CANDIDATE_DIFF,
        {"count": len(observed_cand_diff), "paths": sorted(observed_cand_diff)},
    )

    rep_diff_lines = run_git(repo_root, "diff", "--name-status", DESIGN_CANDIDATE_SHA, ROOT_REPORT_001_SHA).splitlines()
    record_assert(
        "report_001_single_file_addition",
        rep_diff_lines == ["A\tdocs/agent-reports/eld-coordinator/WP-0008/001_2026-11-16_design_eld-coordinator.md"],
        {"diff": rep_diff_lines},
    )

    preserved_oids: dict[str, str] = {}
    for rel in PRESERVED_TREE_PATHS:
        base_oid = run_git(repo_root, "rev-parse", f"{PACKET_BASE_SHA}:{rel}")
        tip_oid = run_git(repo_root, "rev-parse", f"{ROOT_REPORT_001_SHA}:{rel}")
        head_oid = run_git(repo_root, "rev-parse", f"{head_sha}:{rel}")
        record_assert(f"preserved_oid:{rel}", base_oid == tip_oid == head_oid, {"oid": head_oid})
        preserved_oids[rel] = head_oid

    hist_report_changes = run_git(
        repo_root,
        "diff",
        "--name-status",
        "--diff-filter=MD",
        PACKET_BASE_SHA,
        head_sha,
        "--",
        "docs/agent-reports",
    )
    record_assert("zero_historical_reports_modified_or_deleted", hist_report_changes == "", {"diff": hist_report_changes})

    design_blob = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE_SHA}:docs/design/F3-review-correction.md")
    readme_blob = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE_SHA}:workers/local_ocr/README.md")
    kickoff_blob = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE_SHA}:docs/kickoffs/WP-0008-eld-f3-reviewer-design.md")
    base_report_files = run_git(repo_root, "ls-tree", "-r", "--name-only", PACKET_BASE_SHA, "docs/agent-reports").splitlines()
    review_dossier_text = reader.read_text("docs/reviews/WP-0008/eld-f3-reviewer/design/README.md")
    record_assert(
        "dossier_blob_and_report_count_parity",
        len(base_report_files) == 50
        and design_blob in review_dossier_text
        and readme_blob in review_dossier_text,
        {"base_report_file_count": len(base_report_files), "design_blob": design_blob, "readme_blob": readme_blob},
    )

    # 2. Worker README wording & worker_source_sha256 invariance
    worker_readme = reader.read_text("workers/local_ocr/README.md")
    runner_cs = reader.read_text("src/ELedgerCare.Infrastructure/Extraction/LocalPythonOcrWorkerRunner.cs")
    env_guard_py = reader.read_text("workers/local_ocr/local_ocr/env_guard.py")
    worker_py = reader.read_text("workers/local_ocr/local_ocr/worker.py")
    job_proc_cs = reader.read_text("src/ELedgerCare.Infrastructure/Extraction/WindowsJobProcess.cs")

    required_readme_tokens = (
        "HF_HUB_OFFLINE=1",
        "TRANSFORMERS_OFFLINE=1",
        "HF_HUB_DISABLE_XET=1",
        "PIP_NO_INDEX=1",
        "local_files_only=True",
        "OS-enforced outbound network blocking has not been verified",
        "not evidence of a network sandbox",
    )
    record_assert(
        "worker_readme_accurate_offline_wording",
        "network access (" not in worker_readme and all(tok in worker_readme for tok in required_readme_tokens),
        {"readme_blob": readme_blob},
    )
    record_assert(
        "runner_and_worker_match_readme_offline_flags",
        all(
            k in runner_cs
            for k in (
                'env["HF_HUB_OFFLINE"] = "1"',
                'env["TRANSFORMERS_OFFLINE"] = "1"',
                'env["HF_HUB_DISABLE_XET"] = "1"',
                'env["PIP_NO_INDEX"] = "1"',
            )
        )
        and 'environ.get("HF_HUB_OFFLINE") != "1"' in env_guard_py
        and 'environ.get("TRANSFORMERS_OFFLINE") != "1"' in env_guard_py
        and 'environ.get("HF_HUB_DISABLE_XET") != "1"' in env_guard_py
        and 'environ.get("PIP_NO_INDEX") != "1"' in env_guard_py
        and worker_py.count("local_files_only=True") == 2
        and "JobObjectLimitKillOnJobClose = 0x00002000" in job_proc_cs,
        {"local_files_only_calls": worker_py.count("local_files_only=True")},
    )

    recomputed_worker_sha = compute_worker_source_digest(reader, repo_root)
    record_assert(
        "worker_source_sha256_unchanged_by_readme_edit",
        recomputed_worker_sha == EXPECTED_WORKER_SOURCE_SHA256,
        {"worker_source_sha256": recomputed_worker_sha},
    )

    # 3. Genuine F2 seed artifacts & cross-session raw/provenance parity
    f01_pdf = reader.read_bytes("tests/fixtures/SYN-WO-01-v1-raster300.pdf")
    f07_pdf = reader.read_bytes("tests/fixtures/SYN-MP-01-v0-clean.pdf")
    f1_pdf = reader.read_bytes("tests/fixtures/F1-SWO-001.pdf")
    record_assert(
        "product_fixture_digests",
        (
            len(f01_pdf) == 372258
            and sha256_hex(f01_pdf) == F01_PDF_SHA256
            and len(f07_pdf) == 8422
            and sha256_hex(f07_pdf) == F07_PDF_SHA256
            and len(f1_pdf) == 887
            and sha256_hex(f1_pdf) == F1_PDF_SHA256
        ),
        {"f01_bytes": len(f01_pdf), "f07_bytes": len(f07_pdf), "f1_bytes": len(f1_pdf)},
    )

    author_f01_raw = reader.read_bytes(
        "docs/implementation/WP-0006/runtime-author-v2/runs/attempt-01a1e509-f5d4-7a01-80f1-4f23fe282930/output/raw_output.utf8.bin"
    )
    reviewer_f01_raw = reader.read_bytes(
        "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin"
    )
    reviewer_f01_env = json.loads(
        reader.read_text(
            "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/envelope.json"
        )
    )
    author_f07_raw = reader.read_bytes(
        "docs/implementation/WP-0006/runtime-author-v2/runs/attempt-01a1e50c-bdb9-7477-a96a-abb58323c615/output/raw_output.utf8.bin"
    )
    reviewer_f07_raw = reader.read_bytes(
        "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin"
    )
    record_assert(
        "genuine_f2_seed_parity",
        (
            author_f01_raw == reviewer_f01_raw
            and len(reviewer_f01_raw) == 3236
            and sha256_hex(reviewer_f01_raw) == F01_RAW_SHA256
            and reviewer_f01_env["provenance"]["worker_source_sha256"] == EXPECTED_WORKER_SOURCE_SHA256
            and reviewer_f01_env["input"]["sha256"] == F01_PDF_SHA256
            and author_f07_raw == reviewer_f07_raw
            and len(reviewer_f07_raw) == 7511
            and sha256_hex(reviewer_f07_raw) == F07_RAW_SHA256
        ),
        {"f01_raw_sha256": F01_RAW_SHA256, "f07_raw_sha256": F07_RAW_SHA256},
    )

    # 4. Five-field suggestion feasibility on genuine F01 & F07 raw outputs + boundary probes
    f01_suggestions = evaluate_work_order_suggestions(reviewer_f01_raw.decode("utf-8", "strict"))
    expected_f01_values = {
        "work_order_id": ("WO-004192", 1, 4),
        "property_name": ("Cedar Hollow Apartments", 1, 6),
        "building_unit": ("Bldg B - Unit 204", 1, 8),
        "requested_date": ("2026-10-16", 1, 10),
        "issue_and_resolution": (
            "Air handler fan running continuously with warm supply air at 79 F setpoint. "
            "Inspected condensing unit CHP-B204: dual run capacitor measured 18.2 uF on 45 uF herm leg "
            "and contactor points pitted. Replaced capacitor and 2-pole contactor from van stock; "
            "verified 19.4 F delta-T across evaporator coil.",
            1,
            24,
        ),
    }
    for fid, (want_val, want_page, want_block) in expected_f01_values.items():
        got = f01_suggestions[fid]
        record_assert(
            f"f01_suggestion:{fid}",
            (
                got["suggestion_status"] == "suggested"
                and got["suggested_value"] == want_val
                and got["source_ref"]["page_number"] == want_page
                and got["source_ref"]["block_ordinal"] == want_block
                and got["initial_human_decision"] == "unreviewed"
            ),
            {
                "page": got["source_ref"]["page_number"],
                "block_ordinal": got["source_ref"]["block_ordinal"],
                "utf16_len": utf16_code_units(got["suggested_value"]),
            },
        )

    f07_suggestions = evaluate_work_order_suggestions(reviewer_f07_raw.decode("utf-8", "strict"))
    record_assert(
        "f07_invoice_produces_zero_false_suggestions",
        all(v["suggestion_status"] == "missing" and v["suggested_value"] is None for v in f07_suggestions.values()),
        {fid: v["suggestion_status"] for fid, v in f07_suggestions.items()},
    )

    # Prove F3-BIC-01: SafeNativeDisplayParser.ParsePlainTableRows yields 2 cells on colspan row, while strict check rejects!
    spanning_table = '<table><tr><td colspan="4">Property:</td><td colspan="5">Cedar Hollow</td></tr></table>'
    naive_rows = parse_plain_table_rows_f2(spanning_table)
    strict_rows = parse_strict_simple_two_cell_rows(spanning_table)
    simple_table = "<table><tr><td>Property:</td><td>Cedar Hollow</td></tr></table>"
    record_assert(
        "bic01_table_span_detection",
        len(naive_rows) == 1
        and len(naive_rows[0]) == 2
        and strict_rows == []
        and parse_strict_simple_two_cell_rows(simple_table) == [(0, "Property:", "Cedar Hollow")],
        {"naive_cell_count_on_colspan": len(naive_rows[0]), "strict_rows_on_colspan": len(strict_rows)},
    )

    # Probe inline leading zeros, double colon rejection, no-skipping, ambiguity, UTF-16 caps, surrogates/NUL
    edge_raw = (
        "<PAGE>"
        "<BLOCK>text[0,0,1,1]<FORK>Work Order ID: 00042\n"
        "<BLOCK>text[0,0,1,1]<FORK>Property::\n"
        "<BLOCK>text[0,0,1,1]<FORK>ShouldNotMatchDoubleColon\n"
        "<BLOCK>text[0,0,1,1]<FORK>Building / Unit:\n"
        "<BLOCK>other[0,0,1,1]<FORK>SECTION DIVIDER\n"
        "<BLOCK>text[0,0,1,1]<FORK>Bldg Z\n"
        "<BLOCK>text[0,0,1,1]<FORK>Requested Date: 2026-10-16\n"
        "<BLOCK>text[0,0,1,1]<FORK>Requested Date:\n"
        "<BLOCK>text[0,0,1,1]<FORK>2026-10-16\n"
        "<BLOCK>title[0,0,1,1]<FORK>REPORTED SYMPTOM & TECHNICIAN RESOLUTION SUMMARY\n"
        "<BLOCK>text[0,0,1,1]<FORK>Line 1\n\tLine 2 ok"
    )
    edge_res = evaluate_work_order_suggestions(edge_raw)
    record_assert(
        "suggestion_edge_cases",
        (
            edge_res["work_order_id"]["suggested_value"] == "00042"
            and edge_res["property_name"]["suggestion_status"] == "missing"
            and edge_res["building_unit"]["suggestion_status"] == "missing"
            and edge_res["requested_date"]["suggestion_status"] == "ambiguous"
            and edge_res["requested_date"]["suggested_value"] is None
            and len(edge_res["requested_date"]["competing_refs"]) == 2
            and edge_res["issue_and_resolution"]["suggested_value"] == "Line 1\n\tLine 2 ok"
        ),
        {k: v["suggestion_status"] for k, v in edge_res.items()},
    )

    # UTF-16 astral scalar (2 code units) + NUL + unpaired surrogate checks
    record_assert(
        "utf16_and_surrogate_validation",
        (
            utf16_code_units("A" * 62 + "\U0001F527") == 64
            and has_valid_review_text("A" * 62 + "\U0001F527", max_utf16=64, multiline=False)
            and not has_valid_review_text("A" * 63 + "\U0001F527", max_utf16=64, multiline=False)
            and not has_valid_review_text("Bad\x00Null", max_utf16=64, multiline=False)
            and not has_valid_review_text("Bad\nLine", max_utf16=64, multiline=False)
            and not has_valid_review_text("Unpaired\ud800Surrogate", max_utf16=64, multiline=True)
        ),
        {"astral_wrench_utf16_units": utf16_code_units("\U0001F527")},
    )

    # 5. State machine, optimistic concurrency, replay-before-stale, and 128-cap verification
    sim = ReviewLedgerSimulator(
        doc_id="01a1e571-2838-714b-861b-bf0835d7c90a",
        result_id="01a1e571-9999-7000-8000-000000000001",
        machine_suggestions={fid: f01_suggestions[fid]["suggested_value"] for fid, _, _, _ in FIELD_SPECS},
    )

    draft_fields = {
        "work_order_id": {"decision": "accepted", "value": "WO-004192", "unknown_reason": None},
        "property_name": {"decision": "edited", "value": "Cedar Hollow Apartments - North", "unknown_reason": None},
        "building_unit": {"decision": "unreviewed", "value": "Draft Unit Note", "unknown_reason": None},
        "requested_date": {"decision": "unknown", "value": None, "unknown_reason": "Illegible stamp on scan"},
        "issue_and_resolution": {
            "decision": "accepted",
            "value": expected_f01_values["issue_and_resolution"][0],
            "unknown_reason": None,
        },
    }
    req1 = {
        "document_id": sim.doc_id,
        "result_id": sim.result_id,
        "expected_revision": 0,
        "state": "draft",
        "fields": draft_fields,
    }
    st_r1, body_r1 = sim.post_revision("op-1", req1)
    # Mutate live suggestion map AFTER Rev 1 to prove persisted snapshot immutability!
    sim.live_suggestions["work_order_id"] = "MUTATED-BY-FUTURE-MAPPER"

    # Premature 'reviewed' with unreviewed field must reject (422) without advancing revision
    bad_rev_req = {**req1, "expected_revision": 1, "state": "reviewed"}
    st_bad_rev, _ = sim.post_revision("op-bad-reviewed", bad_rev_req)

    # Complete all 5 fields and save explicit 'reviewed' Revision 2
    reviewed_fields = {
        **draft_fields,
        "building_unit": {"decision": "edited", "value": "Bldg B - Unit 204A", "unknown_reason": None},
    }
    req2 = {
        "document_id": sim.doc_id,
        "result_id": sim.result_id,
        "expected_revision": 1,
        "state": "reviewed",
        "fields": reviewed_fields,
    }
    st_r2, body_r2 = sim.post_revision("op-2", req2)

    # Replay op-1 AFTER Revision 2 exists -> must return 200 with Revision 1!
    st_replay1, body_replay1 = sim.post_revision("op-1", req1)
    # Same key op-1 with different content -> 409
    st_conflict_key, _ = sim.post_revision("op-1", {**req1, "state": "reviewed", "fields": reviewed_fields})
    # Stale expectedRevision=0 with new key -> 409 with current_revision=2
    st_stale, body_stale = sim.post_revision("op-stale", req1)

    # Advance to revision 128 and verify replay of op-128 still returns 200 while op-129 returns 409
    for rev_target in range(3, 129):
        nxt_state = "draft" if rev_target % 2 == 1 else "reviewed"
        req_n = {
            "document_id": sim.doc_id,
            "result_id": sim.result_id,
            "expected_revision": rev_target - 1,
            "state": nxt_state,
            "fields": reviewed_fields,
        }
        st_n, _ = sim.post_revision(f"op-{rev_target}", req_n)
        assert st_n == 201

    req_128 = {
        "document_id": sim.doc_id,
        "result_id": sim.result_id,
        "expected_revision": 127,
        "state": "reviewed",
        "fields": reviewed_fields,
    }
    st_replay_128, body_replay_128 = sim.post_revision("op-128", req_128)
    st_over_cap, body_over_cap = sim.post_revision(
        "op-129",
        {**req_128, "expected_revision": 128, "state": "draft"},
    )

    record_assert(
        "optimistic_concurrency_idempotency_and_128_cap",
        (
            st_r1 == 201
            and body_r1["revision_number"] == 1
            and st_bad_rev == 422
            and st_r2 == 201
            and body_r2["revision_number"] == 2
            and body_r2["machine_snapshot"]["work_order_id"] == "WO-004192"
            and st_replay1 == 200
            and body_replay1["revision_number"] == 1
            and st_conflict_key == 409
            and st_stale == 409
            and body_stale["current_revision"] == 2
            and st_replay_128 == 200
            and body_replay_128["revision_number"] == 128
            and st_over_cap == 409
            and body_over_cap["code"] == "revision_limit_reached"
            and len(sim.revisions) == 128
        ),
        {"total_revisions": len(sim.revisions), "replay_128_status": st_replay_128, "cap_129_status": st_over_cap},
    )

    # 6. Disjoint port allocations & Markdown links
    port_allocations = {
        "f1_author": (5180, 4200, 55432),
        "f1_reviewer": (5280, 4300, 55433),
        "f2_author": (5190, 4210, 55434),
        "f2_reviewer": (5290, 4310, 55435),
        "f3_author": (5390, 4410, 55436),
        "f3_reviewer": (5490, 4510, 55437),
    }
    flat_ports = [p for triple in port_allocations.values() for p in triple]
    f3_design_text = reader.read_text("docs/design/F3-review-correction.md")
    record_assert(
        "port_disjointness_across_f1_f2_f3",
        len(flat_ports) == len(set(flat_ports)) == 18
        and "API5390/UI4410/PG55436" in f3_design_text
        and "API5490/UI4510/PG55437" in f3_design_text,
        {"distinct_port_count": len(set(flat_ports)), "f3_reviewer": port_allocations["f3_reviewer"]},
    )

    md_targets = [
        "docs/design/F3-review-correction.md",
        "docs/coordination/WP-0008-0009-authority.md",
        "docs/kickoffs/WP-0008-eld-f3-reviewer-design.md",
        "workers/local_ocr/README.md",
        "docs/agent-reports/eld-coordinator/WP-0008/001_2026-11-16_design_eld-coordinator.md",
        "docs/reviews/WP-0008/eld-f3-reviewer/design/README.md",
        *args.extra_md,
    ]
    checked_links = verify_markdown_links(reader, repo_root, md_targets)
    record_assert("local_markdown_links_resolve", len(checked_links) > 0, {"checked_link_count": len(checked_links)})

    record_assert(
        "zero_sealed_wp0009_paths_opened",
        all(not any(b in p.lower() for b in FORBIDDEN_PATH_SUBSTRINGS) for p in reader.opened_paths),
        {"opened_file_count": len(reader.opened_paths)},
    )

    helper_bytes = script_path.read_bytes()
    receipt = {
        "schema": "eledgercare.wp-0008.f3-design-review-receipt/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f3-reviewer",
        "branch": branch_name,
        "frozen_head_sha": head_sha,
        "packet_base_sha": PACKET_BASE_SHA,
        "authority_sha": AUTHORITY_SHA,
        "reviewed_design_candidate_sha": DESIGN_CANDIDATE_SHA,
        "reviewed_root_report_001_sha": ROOT_REPORT_001_SHA,
        "referenced_f2_source_sha": ACCEPTED_F2_SOURCE_SHA,
        "referenced_f2_review_004_sha": ACCEPTED_F2_REVIEW_004_SHA,
        "reviewed_blobs": {
            "docs/design/F3-review-correction.md": design_blob,
            "workers/local_ocr/README.md": readme_blob,
            "docs/kickoffs/WP-0008-eld-f3-reviewer-design.md": kickoff_blob,
        },
        "helper_path": "docs/reviews/WP-0008/eld-f3-reviewer/design/verify_f3_design_and_readme.py",
        "helper_sha256_raw": sha256_hex(helper_bytes),
        "helper_sha256_lf": sha256_hex(helper_bytes.replace(b"\r\n", b"\n")),
        "verdicts": {
            "f3_design": "accepted",
            "worker_readme_network_wording": "accepted",
            "kickoff_bindings": ["F3-KR-01"],
            "implementation_checkpoints": [
                "F3-BIC-01",
                "F3-BIC-02",
                "F3-BIC-03",
                "F3-BIC-04",
                "F3-BIC-05",
                "F3-BIC-06",
            ],
        },
        "preserved_tree_oids": preserved_oids,
        "worker_source_sha256": recomputed_worker_sha,
        "f01_suggestion_preview": f01_suggestions,
        "checked_markdown_links": checked_links,
        "opened_repo_paths": sorted(set(reader.opened_paths)),
        "assertion_count": len(assertions),
        "all_assertions_passed": True,
        "assertions": assertions,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    print(f"OK: {len(assertions)} assertions passed; receipt written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
