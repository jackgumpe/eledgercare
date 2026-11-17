"""Deterministic CPU-only verification helper for WP-0010 /002 independent F4 archive design review.

Verifies Git lineage, exact authority/candidate/report diffs, protected-tree & historical-report
immutability, genuine WP-0006 F2 seed digests, SafeNativeDisplayParser + F4 machine projection
feasibility (including colspan cell preservation, non-cell/malformed table fallback, missing-<PAGE>
document fallback, U+0000 sanitization without truncation, empty-result completion markers, and
whitespace-only unit delimiters), C-locale PostgreSQL ILIKE escaping/collation parity, multi-revision
review/draft/unknown/old-link search semantics, cross-page/field/source AND matching, microsecond +
RFC 4122 UUID keyset pagination, surrogate-safe <=240 UTF-16 snippet clipping, inert XSS segments,
competing two-initializer idempotency vs. conflict detection, 24-port disjointness across F1..F4,
WP-0011/WP-0009 sealed-path refusal, and local Markdown link resolution.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

PACKET_BASE_SHA = "956c056be2ec970340074871ecdd7e1a9855d944"
AUTHORITY_SHA = "8d23d755a35be26ff29c319c527bd770abdcae4b"
DESIGN_CANDIDATE_SHA = "01a6dab0695c93246b4cf04d1a2098d3b77248d8"
ROOT_REPORT_001_SHA = "3a59f78df399da449028edb1839be3a5ee457f90"
ACCEPTED_F3_SOURCE_SHA = "dda4b4d5856ac45105c31ba1d6d6813debdab8a7"
ACCEPTED_F3_REVIEW_007_SHA = "299b9ee81528191e4d964b9e22745f477f2c4e8c"
ACCEPTED_F3_CLOSURE_005_SHA = "3282b9db7b7f05bbb14fd000591a732bbda581bc"

EXPECTED_DESIGN_BLOB = "f821581ccb32d545bed51a80f316613286ead3bf"
EXPECTED_KICKOFF_BLOB = "8a7fd82e6d504da5da5a5898440eae55c9031973"
EXPECTED_AUTHORITY_BLOB = "3479b028d80d75f246233ef286fd000864708fa7"
EXPECTED_REPORT_001_BLOB = "fe3532d6e3e2ac4e9ba89b94dad68c8493dffced"

F01_PDF_SHA256 = "47b2df6a33309bdc056c852f7f20c6c5824c4adb5a8b785fda05ed81e34489cd"
F01_RAW_SHA256 = "7503761ae46afef6adf579881d011764283474354fac3e185598fc7d266aff95"
F07_PDF_SHA256 = "15e39351f1bcd571815e642ac066d36b12096d732b34f8742155224c8dffc7f3"
F07_RAW_SHA256 = "c399ad892e257500e2b6a9ac8b0bc3d8a17e9c10041262c4bca6a48fb9b9b639"
F1_PDF_SHA256 = "875a2d8c83c1c1002b38840f8136b60bd5ebcfe8d2df47187bf36454c59497cb"

FORBIDDEN_PATH_SUBSTRINGS = (
    "eledgercare-mapping",
    "eledgercare-coverage",
    "wp-0009/sealed",
    "wp-0009\\sealed",
    "wp-0009-fresh-families",
    "wp-0011-diagnostic-families",
    "eld-coverage-custodian",
    "eld-coverage-author",
    "eld-coverage-reviewer",
    "docs/kickoffs/wp-0011-",
    "docs\\kickoffs\\wp-0011-",
)

EXPECTED_AUTHORITY_DIFF = {
    "AGENTS.md": "M",
    "CURRENT.md": "M",
    "INDEX.md": "M",
    "docs/coordination/WP-0010-0011-authority.md": "A",
    "docs/kickoffs/WP-0011-eld-eval-custodian.md": "A",
    "docs/kickoffs/WP-0011-eld-mapping-author.md": "A",
    "docs/kickoffs/WP-0011-eld-mapping-reviewer.md": "A",
}

EXPECTED_CANDIDATE_DIFF = {
    **EXPECTED_AUTHORITY_DIFF,
    "docs/design/F4-source-linked-archive.md": "A",
    "docs/kickoffs/WP-0010-eld-f4-reviewer-design.md": "A",
}

PRESERVED_TREE_PATHS = (
    "src",
    "tests",
    "web",
    "deploy",
    "ELedgerCare.slnx",
    "workers",
    "evaluation",
    "qualification",
    "research",
)

PRODUCT_TREE_PATHS = (
    "src",
    "tests",
    "web",
    "deploy",
    "ELedgerCare.slnx",
    "workers",
)

FIELD_SPECS = (
    ("work_order_id", "Work Order ID", 64, False),
    ("property_name", "Property", 200, False),
    ("building_unit", "Building / Unit", 120, False),
    ("requested_date", "Requested Date", 64, False),
    ("issue_and_resolution", "Issue & Resolution", 4000, True),
)
FIELD_KEY_TO_LABEL = {fid: label for fid, label, _, _ in FIELD_SPECS}

PORT_RESERVATIONS = {
    "f1_author": (5180, 4200, 55432),
    "f1_reviewer": (5280, 4300, 55433),
    "f2_author": (5190, 4210, 55434),
    "f2_reviewer": (5290, 4310, 55435),
    "f3_author": (5390, 4410, 55436),
    "f3_reviewer": (5490, 4510, 55437),
    "f4_author": (5590, 4610, 55438),
    "f4_reviewer": (5690, 4710, 55439),
}


class SafeRepoReader:
    """Enforces read-only access inside the owned reviewer worktree and refuses sealed/WP-0011 paths."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.opened_paths: list[str] = []

    def _guard(self, path: Path) -> Path:
        resolved = path.resolve()
        norm = str(resolved).lower()
        for bad in FORBIDDEN_PATH_SUBSTRINGS:
            if bad in norm:
                raise PermissionError(f"Refusing forbidden sealed/R&D path: {resolved}")
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


def string_to_utf16_units(text: str) -> list[int]:
    """Converts a Python string (which may contain lone surrogates in synthetic negative tests) into UTF-16 code units."""
    units: list[int] = []
    for ch in text:
        cp = ord(ch)
        if cp <= 0xFFFF:
            units.append(cp)
        else:
            cp_prime = cp - 0x10000
            units.append(0xD800 + (cp_prime >> 10))
            units.append(0xDC00 + (cp_prime & 0x3FF))
    return units


def utf16_units_to_string(units: list[int]) -> str:
    """Reconstructs a valid Unicode string from a surrogate-safe UTF-16 code-unit slice."""
    chars: list[str] = []
    i = 0
    while i < len(units):
        u = units[i]
        if 0xD800 <= u <= 0xDBFF:
            if i + 1 >= len(units) or not (0xDC00 <= units[i + 1] <= 0xDFFF):
                raise ValueError(f"Unpaired high surrogate 0x{u:04X} at index {i}")
            low = units[i + 1]
            cp = 0x10000 + ((u - 0xD800) << 10) + (low - 0xDC00)
            chars.append(chr(cp))
            i += 2
        elif 0xDC00 <= u <= 0xDFFF:
            raise ValueError(f"Unpaired low surrogate 0x{u:04X} at index {i}")
        else:
            chars.append(chr(u))
            i += 1
    return "".join(chars)


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


def table_has_non_cell_text_or_unclosed_tag(table_markup: str) -> bool:
    """Detects malformed table content outside <td>/<th> or unclosed '<' tags (F4-BIC-02)."""
    in_cell = False
    has_table_open = False
    i = 0
    n = len(table_markup)
    while i < n:
        lt = table_markup.find("<", i)
        if lt < 0:
            if not in_cell and table_markup[i:].strip():
                return True
            if in_cell:
                return True
            break
        if lt > i and not in_cell and table_markup[i:lt].strip():
            return True
        gt = table_markup.find(">", lt + 1)
        if gt < 0:
            return True
        raw_tag = table_markup[lt + 1 : gt].strip()
        is_closing = raw_tag.startswith("/")
        tag_body = (raw_tag[1:] if is_closing else raw_tag).strip()
        name_end = 0
        while name_end < len(tag_body) and tag_body[name_end].isalnum():
            name_end += 1
        tag_name = tag_body[:name_end].lower()
        if tag_name == "table" and not is_closing:
            has_table_open = True
        elif tag_name in ("td", "th"):
            in_cell = not is_closing
        elif not in_cell and tag_name not in ("table", "thead", "tbody", "tfoot", "tr"):
            return True
        i = gt + 1
    return (not has_table_open) or in_cell


def sanitize_pg_text_no_truncate(text: str) -> tuple[str, bool]:
    """Replaces U+0000 with U+FFFD for PostgreSQL text storage without length truncation (F4-BIC-02)."""
    if "\x00" not in text:
        return text, False
    return text.replace("\x00", "\ufffd"), True


def build_machine_projection(
    result_id: str,
    document_id: str,
    raw_bytes: bytes,
    expected_page_count: int,
    projection_version: str = "archive-machine-v1",
) -> dict:
    """Reference deterministic F4 machine projection over SafeNativeDisplayParser (F4-BIC-02, F4-BIC-05)."""
    if len(raw_bytes) < 1 or len(raw_bytes) > 16_777_216:
        raise ValueError("raw_bytes outside 1..16,777,216 ceiling")
    if expected_page_count < 1 or expected_page_count > 3:
        raise ValueError("expected_page_count outside 1..3 ceiling")

    raw_sha = sha256_hex(raw_bytes)
    raw_text = raw_bytes.decode("utf-8")

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

    units: list[dict] = []

    def append_unit(page_no: int | None, text: str, is_fallback: bool) -> None:
        cleaned, had_nul = sanitize_pg_text_no_truncate(text)
        if cleaned.strip():
            units.append({
                "unit_ordinal": len(units),
                "page_number": page_no,
                "is_fallback": is_fallback or had_nul,
                "searchable_text": cleaned,
            })

    # Document-level fallback if physical page mapping cannot be established honestly.
    if len(positions) == 0 or len(positions) != expected_page_count:
        append_unit(None, decode_basic_entities(raw_text), True)
    else:
        if positions[0] > 0 and raw_text[: positions[0]].strip():
            append_unit(None, decode_basic_entities(raw_text[: positions[0]].strip()), True)

        for p_idx, start_pos in enumerate(positions):
            pno = p_idx + 1
            c_start = start_pos + len(page_token)
            c_end = positions[p_idx + 1] if p_idx + 1 < len(positions) else len(raw_text)
            page_slice = raw_text[c_start:c_end]

            b_positions: list[int] = []
            b_pos = 0
            while b_pos <= len(page_slice):
                b_idx = page_slice.find(block_token, b_pos)
                if b_idx < 0:
                    break
                b_positions.append(b_idx)
                b_pos = b_idx + len(block_token)

            page_lines: list[str] = []
            page_fallback_lines: list[str] = []

            if not b_positions:
                if page_slice.strip():
                    page_lines.append(page_slice.strip())
            else:
                if b_positions[0] > 0 and page_slice[: b_positions[0]].strip():
                    page_lines.append(page_slice[: b_positions[0]].strip())

                for i, b_tok in enumerate(b_positions):
                    seg_start = b_tok + len(block_token)
                    seg_end = b_positions[i + 1] if i + 1 < len(b_positions) else len(page_slice)
                    segment = page_slice[seg_start:seg_end]
                    fork_idx = segment.find(fork_token)
                    if fork_idx < 0:
                        if segment.strip():
                            page_fallback_lines.append(segment.strip())
                        continue
                    header = segment[:fork_idx]
                    content = segment[fork_idx + len(fork_token) :].rstrip("\r\n")
                    k_end = 0
                    while k_end < len(header) and header[k_end].isascii() and header[k_end].isalpha():
                        k_end += 1
                    kind = header[:k_end].lower() if k_end > 0 else "block"

                    if kind == "block":
                        if content.strip():
                            page_fallback_lines.append(decode_basic_entities(content))
                    elif kind == "table" and "<table" in content.lower():
                        rows = parse_plain_table_rows_f2(content)
                        malformed = (len(rows) == 0) or table_has_non_cell_text_or_unclosed_tag(content)
                        if rows:
                            for row in rows:
                                non_empty_cells = [c for c in row if c]
                                if non_empty_cells:
                                    # Join strictly with '\t' whitespace (never '|' or ',') per F4-BIC-02!
                                    page_lines.append("\t".join(non_empty_cells))
                        if malformed and content.strip():
                            page_fallback_lines.append(decode_basic_entities(content))
                    elif kind == "table":
                        if content.strip():
                            page_fallback_lines.append(decode_basic_entities(content))
                    else:
                        decoded = decode_basic_entities(content)
                        if decoded.strip():
                            page_lines.append(decoded)

            if page_lines:
                append_unit(pno, "\n".join(page_lines), False)
            if page_fallback_lines:
                append_unit(pno, "\n".join(page_fallback_lines), True)

    canonical_units_bytes = json.dumps(units, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "result_id": result_id,
        "document_id": document_id,
        "raw_output_sha256": raw_sha,
        "projection_version": projection_version,
        "unit_count": len(units),
        "has_fallback": any(u["is_fallback"] for u in units),
        "projection_sha256": sha256_hex(canonical_units_bytes),
        "units": units,
    }


def escape_postgres_like_literal(term: str) -> str:
    """Explicit LIKE/ILIKE metacharacter escaping with '\\' escape character (F4-BIC-01)."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def c_locale_ascii_fold(text: str) -> str:
    """Exact mirror of PostgreSQL initdb --encoding=UTF8 --no-locale (LC_CTYPE=C) case-folding."""
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if 0x41 <= code <= 0x5A:
            out.append(chr(code + 32))
        else:
            out.append(ch)
    return "".join(out)


def postgres_c_ilike_evaluate(haystack: str, pattern: str, escape_char: str = "\\") -> bool:
    """Evaluates SQL `haystack ILIKE pattern ESCAPE '\\'` under PostgreSQL LC_CTYPE=C."""
    if len(escape_char) != 1:
        raise ValueError("escape_char must be 1 character")
    rx_parts = ["^"]
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == escape_char:
            if i + 1 >= len(pattern):
                raise ValueError("Postgres 22025: LIKE pattern must not end with escape character")
            rx_parts.append(re.escape(c_locale_ascii_fold(pattern[i + 1])))
            i += 2
        elif ch == "%":
            rx_parts.append(".*")
            i += 1
        elif ch == "_":
            rx_parts.append(".")
            i += 1
        else:
            rx_parts.append(re.escape(c_locale_ascii_fold(ch)))
            i += 1
    rx_parts.append("$")
    regex = re.compile("".join(rx_parts), re.DOTALL)
    return regex.match(c_locale_ascii_fold(haystack)) is not None


def validate_and_parse_archive_query(params: list[tuple[str, str]]) -> tuple[int, dict]:
    """Validates GET /api/archive query parameters per F4-source-linked-archive.md & F4-BIC-01."""
    seen_keys: set[str] = set()
    param_map: dict[str, str] = {}
    for k, v in params:
        if k not in ("q", "source", "limit", "after"):
            return 400, {"code": "unknown_query_parameter", "parameter": k}
        if k in seen_keys:
            return 400, {"code": "duplicate_query_parameter", "parameter": k}
        seen_keys.add(k)
        param_map[k] = v

    source = param_map.get("source", "all")
    if source not in ("all", "machine", "reviewed"):
        return 400, {"code": "invalid_source_filter"}

    limit = 20
    if "limit" in param_map:
        raw_lim = param_map["limit"]
        if not re.fullmatch(r"[1-9][0-9]*", raw_lim):
            return 400, {"code": "invalid_limit"}
        limit = int(raw_lim)
        if limit < 1 or limit > 50:
            return 400, {"code": "invalid_limit"}

    raw_q = param_map.get("q", "")
    q_units = string_to_utf16_units(raw_q)
    i = 0
    while i < len(q_units):
        u = q_units[i]
        if u == 0:
            return 400, {"code": "null_character_forbidden"}
        if 0xD800 <= u <= 0xDBFF:
            if i + 1 >= len(q_units) or not (0xDC00 <= q_units[i + 1] <= 0xDFFF):
                return 400, {"code": "unpaired_surrogate_forbidden"}
            i += 2
            continue
        if 0xDC00 <= u <= 0xDFFF:
            return 400, {"code": "unpaired_surrogate_forbidden"}
        ch = chr(u)
        if (u < 0x20 or 0x7F <= u <= 0x9F) and ch not in ("\t", "\r", "\n"):
            return 400, {"code": "control_character_forbidden"}
        i += 1

    trimmed_q = raw_q.strip()
    if utf16_code_units(trimmed_q) > 160:
        return 400, {"code": "query_too_long"}

    terms = trimmed_q.split() if trimmed_q else []
    if len(terms) > 8:
        return 400, {"code": "too_many_query_terms"}
    for t in terms:
        if utf16_code_units(t) > 64:
            return 400, {"code": "query_term_too_long"}

    return 200, {
        "terms": terms,
        "source": source,
        "limit": limit,
        "after": param_map.get("after"),
    }


def query_scope_digest(source: str, terms: list[str]) -> str:
    payload = {"v": 1, "source": source, "terms": terms}
    return sha256_hex(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def encode_keyset_cursor(submitted_at_micros: int, document_id: str, source: str, terms: list[str]) -> str:
    body = {
        "v": "archive-cursor/1",
        "t": submitted_at_micros,
        "id": document_id.lower(),
        "s": source,
        "qh": query_scope_digest(source, terms),
    }
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_and_validate_cursor(cursor: str, expected_source: str, expected_terms: list[str]) -> tuple[bool, dict]:
    if not cursor or len(cursor) > 256 or not re.fullmatch(r"[A-Za-z0-9_-]+", cursor):
        return False, {"code": "invalid_cursor"}
    pad = "=" * ((4 - (len(cursor) % 4)) % 4)
    try:
        decoded = base64.urlsafe_b64decode((cursor + pad).encode("ascii")).decode("utf-8")
        obj = json.loads(decoded)
    except Exception:
        return False, {"code": "invalid_cursor"}
    if not isinstance(obj, dict) or set(obj.keys()) != {"v", "t", "id", "s", "qh"}:
        return False, {"code": "invalid_cursor"}
    if obj["v"] != "archive-cursor/1" or not isinstance(obj["t"], int) or isinstance(obj["t"], bool):
        return False, {"code": "invalid_cursor"}
    doc_id = obj["id"]
    if (
        not isinstance(doc_id, str)
        or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", doc_id)
        or doc_id == "00000000-0000-0000-0000-000000000000"
    ):
        return False, {"code": "invalid_cursor"}
    if obj["s"] != expected_source or obj["qh"] != query_scope_digest(expected_source, expected_terms):
        return False, {"code": "cursor_query_mismatch"}
    return True, {"submitted_at_micros": obj["t"], "document_id": doc_id}


def clip_surrogate_safe_witness_snippet(text: str, term: str, max_utf16_units: int = 240) -> dict:
    """Clips <=240 UTF-16 code units around a C-locale literal match without splitting surrogate pairs (F4-BIC-06)."""
    folded_text = c_locale_ascii_fold(text)
    folded_term = c_locale_ascii_fold(term)
    py_idx = folded_text.find(folded_term)
    if py_idx < 0:
        raise ValueError("Term not found in C-locale matched unit")

    # Convert to UTF-16 code-unit offsets (identical between folded and original because ASCII fold is 1:1 in code points & UTF-16 units).
    text_units = string_to_utf16_units(text)
    match_u_start = utf16_code_units(text[:py_idx])
    match_u_len = utf16_code_units(term)
    match_u_end = match_u_start + match_u_len

    budget_around = max(0, max_utf16_units - match_u_len)
    before_budget = budget_around // 2
    win_start = max(0, match_u_start - before_budget)
    win_end = min(len(text_units), win_start + max_utf16_units)
    if win_end - win_start < max_utf16_units and win_start > 0:
        win_start = max(0, win_end - max_utf16_units)

    # Step INWARD if boundary lands mid-surrogate pair so length never grows past max_utf16_units!
    if 0 < win_start < len(text_units) and (0xDC00 <= text_units[win_start] <= 0xDFFF):
        win_start += 1
    if win_start < win_end < len(text_units) and (0xD800 <= text_units[win_end - 1] <= 0xDBFF):
        win_end -= 1

    rel_start = match_u_start - win_start
    rel_end = match_u_end - win_start
    sliced_units = text_units[win_start:win_end]
    snippet_str = utf16_units_to_string(sliced_units)
    before_str = utf16_units_to_string(sliced_units[:rel_start])
    match_str = utf16_units_to_string(sliced_units[rel_start:rel_end])
    after_str = utf16_units_to_string(sliced_units[rel_end:])

    return {
        "snippet": snippet_str,
        "utf16_length": len(sliced_units),
        "prefix_clipped": win_start > 0,
        "suffix_clipped": win_end < len(text_units),
        "segments": [
            *([{"text": before_str, "highlighted": False}] if before_str else []),
            {"text": match_str, "highlighted": True},
            *([{"text": after_str, "highlighted": False}] if after_str else []),
        ],
    }


class ArchiveSimulator:
    """Reference in-memory model of F4 archive projection backfill, initializer races, and snapshot search."""

    PROJECTION_VERSION = "archive-machine-v1"

    def __init__(self) -> None:
        self.ready = False
        self.conflict_error: str | None = None
        self.documents: dict[str, dict] = {}
        self.extraction_results: dict[str, dict] = {}
        self.projections: dict[tuple[str, str], dict] = {}
        self.revisions_by_doc: dict[str, list[dict]] = {}

    def submit_document(self, doc_id: str, submitted_at_micros: int, page_count: int, status: str = "awaiting_extraction") -> None:
        self.documents[doc_id] = {
            "document_id": doc_id.lower(),
            "submitted_at_micros": submitted_at_micros,
            "page_count": page_count,
            "status": status,
        }
        self.revisions_by_doc.setdefault(doc_id.lower(), [])

    def seed_unprojected_result(self, result_id: str, doc_id: str, raw_bytes: bytes, page_count: int) -> None:
        doc_key = doc_id.lower()
        self.documents[doc_key]["status"] = "completed"
        self.extraction_results[result_id] = {
            "result_id": result_id,
            "document_id": doc_key,
            "raw_bytes": raw_bytes,
            "raw_output_sha256": sha256_hex(raw_bytes),
            "page_count": page_count,
        }

    def publish_completed_result_atomic(
        self,
        result_id: str,
        doc_id: str,
        raw_bytes: bytes,
        page_count: int,
        *,
        fenced_out: bool = False,
        fail_mid_tx: bool = False,
    ) -> bool:
        if fenced_out:
            return False
        proj = build_machine_projection(result_id, doc_id.lower(), raw_bytes, page_count, self.PROJECTION_VERSION)
        if fail_mid_tx:
            return False
        self.seed_unprojected_result(result_id, doc_id, raw_bytes, page_count)
        self.projections[(result_id, self.PROJECTION_VERSION)] = proj
        return True

    def run_backfill_initializer(self) -> tuple[bool, str | None]:
        # 1. Verify existing projection metadata integrity against extraction_results.
        for (res_id, ver), proj in self.projections.items():
            if ver != self.PROJECTION_VERSION:
                continue
            res = self.extraction_results.get(res_id)
            if (
                res is None
                or proj["document_id"] != res["document_id"]
                or proj["raw_output_sha256"] != res["raw_output_sha256"]
                or len(proj["units"]) != proj["unit_count"]
            ):
                self.ready = False
                self.conflict_error = f"projection_conflict:{res_id}"
                return False, self.conflict_error

        # 2. Fill missing projections per bounded result; reconcile concurrent 23505 via projection_sha256.
        for res_id in sorted(self.extraction_results):
            key = (res_id, self.PROJECTION_VERSION)
            res = self.extraction_results[res_id]
            computed = build_machine_projection(res_id, res["document_id"], res["raw_bytes"], res["page_count"], self.PROJECTION_VERSION)
            if key in self.projections:
                existing = self.projections[key]
                if (
                    existing["document_id"] != computed["document_id"]
                    or existing["raw_output_sha256"] != computed["raw_output_sha256"]
                    or existing["unit_count"] != computed["unit_count"]
                    or existing["projection_sha256"] != computed["projection_sha256"]
                ):
                    self.ready = False
                    self.conflict_error = f"race_conflict:{res_id}"
                    return False, self.conflict_error
            else:
                self.projections[key] = computed

        self.ready = True
        self.conflict_error = None
        return True, None

    def save_review_revision(
        self,
        doc_id: str,
        status: str,
        fields: dict[str, dict],
        operator_label: str | None = None,
    ) -> int:
        doc_key = doc_id.lower()
        revs = self.revisions_by_doc[doc_key]
        rev_num = len(revs) + 1
        revs.append({
            "revision_number": rev_num,
            "status": status,
            "operator_display_label": operator_label,
            "fields": json.loads(json.dumps(fields)),
        })
        return rev_num

    def _latest_reviewed_and_head(self, doc_id: str) -> tuple[dict | None, dict | None]:
        revs = self.revisions_by_doc.get(doc_id, [])
        head = revs[-1] if revs else None
        reviewed = [r for r in revs if r["status"] == "reviewed"]
        latest_rev = reviewed[-1] if reviewed else None
        return latest_rev, head

    def search(self, params: list[tuple[str, str]]) -> tuple[int, dict]:
        if not self.ready or self.conflict_error is not None:
            return 503, {"code": self.conflict_error or "archive_not_ready"}

        # Never serve misleading 200 OK if any committed extraction_results row lacks a current projection!
        for res_id in self.extraction_results:
            if (res_id, self.PROJECTION_VERSION) not in self.projections:
                return 503, {"code": "archive_projection_incomplete"}

        status_code, parsed = validate_and_parse_archive_query(params)
        if status_code != 200:
            return status_code, parsed

        terms: list[str] = parsed["terms"]
        source: str = parsed["source"]
        limit: int = parsed["limit"]
        after_raw: str | None = parsed["after"]

        cursor_tuple: tuple[int, str] | None = None
        if after_raw is not None:
            ok, cur = decode_and_validate_cursor(after_raw, source, terms)
            if not ok:
                return 400, cur
            cursor_tuple = (cur["submitted_at_micros"], cur["document_id"])

        # Deterministic sort: submitted_at DESC, document_id DESC (RFC 4122 lowercase hex order).
        ordered_docs = sorted(
            self.documents.values(),
            key=lambda d: (d["submitted_at_micros"], d["document_id"]),
            reverse=True,
        )

        proj_by_doc = {
            proj["document_id"]: proj
            for (_, ver), proj in self.projections.items()
            if ver == self.PROJECTION_VERSION
        }

        matched_cards: list[dict] = []
        for doc in ordered_docs:
            doc_id = doc["document_id"]
            key_tuple = (doc["submitted_at_micros"], doc_id)
            if cursor_tuple is not None and not (key_tuple < cursor_tuple):
                continue

            proj = proj_by_doc.get(doc_id)
            latest_rev, head_rev = self._latest_reviewed_and_head(doc_id)
            has_newer_draft = bool(
                head_rev is not None
                and head_rev["status"] == "draft"
                and latest_rev is not None
                and head_rev["revision_number"] > latest_rev["revision_number"]
            )

            # Card title uses reviewed work_order_id/property_name ONLY from latest_reviewed (never draft!).
            title_parts: list[str] = []
            if latest_rev is not None:
                for t_key in ("work_order_id", "property_name"):
                    f_entry = latest_rev["fields"].get(t_key)
                    if f_entry and f_entry["decision"] in ("accepted", "edited") and f_entry.get("value"):
                        title_parts.append(f_entry["value"])
            display_title = " · ".join(title_parts) if title_parts else f"Document {doc_id[:8]}"

            if not terms:
                if source == "machine" and proj is None:
                    continue
                if source == "reviewed" and latest_rev is None:
                    continue
                matched_cards.append({
                    "document_id": doc_id,
                    "submitted_at_micros": doc["submitted_at_micros"],
                    "status": doc["status"],
                    "display_title": display_title,
                    "latest_reviewed_revision": latest_rev["revision_number"] if latest_rev else None,
                    "current_head_revision": head_rev["revision_number"] if head_rev else 0,
                    "current_head_status": head_rev["status"] if head_rev else "unreviewed",
                    "has_newer_draft": has_newer_draft,
                    "contributing_sources": [],
                    "witnesses": [],
                    "has_more_matches": False,
                })
                if len(matched_cards) >= limit + 1:
                    break
                continue

            # Nonempty query: gather eligible units strictly per source filter.
            eligible_units: list[dict] = []
            if source in ("all", "reviewed") and latest_rev is not None:
                for fid, label, _, _ in FIELD_SPECS:
                    fe = latest_rev["fields"].get(fid)
                    if fe and fe["decision"] in ("accepted", "edited") and fe.get("value"):
                        eligible_units.append({
                            "source": "reviewed",
                            "revision_number": latest_rev["revision_number"],
                            "field_key": fid,
                            "field_label": label,
                            "page_number": fe.get("consulted_page_number"),
                            "is_fallback": False,
                            "text": fe["value"],
                        })
            if source in ("all", "machine") and proj is not None:
                for u in proj["units"]:
                    eligible_units.append({
                        "source": "machine",
                        "result_id": proj["result_id"],
                        "page_number": u["page_number"],
                        "is_fallback": u["is_fallback"],
                        "label": "Machine extraction — unreviewed",
                        "text": u["searchable_text"],
                    })

            if not eligible_units:
                continue

            patterns = [escape_postgres_like_literal(t) for t in terms]
            per_term_matches: list[list[dict]] = []
            doc_matches_all = True
            for t, pat in zip(terms, patterns):
                hits = [u for u in eligible_units if postgres_c_ilike_evaluate(u["text"], pat)]
                if not hits:
                    doc_matches_all = False
                    break
                per_term_matches.append(hits)

            if not doc_matches_all:
                continue

            total_unit_term_matches = sum(len(h) for h in per_term_matches)
            witnesses: list[dict] = []
            seen_unit_snip: dict[tuple, dict] = {}
            contributing_sources: list[str] = []

            for t, hits in zip(terms, per_term_matches):
                chosen = hits[0]
                src_kind = chosen["source"]
                if src_kind not in contributing_sources:
                    contributing_sources.append(src_kind)
                snip = clip_surrogate_safe_witness_snippet(chosen["text"], t, 240)
                dedup_key = (
                    src_kind,
                    chosen.get("revision_number"),
                    chosen.get("field_key"),
                    chosen.get("page_number"),
                    snip["snippet"],
                )
                if dedup_key in seen_unit_snip:
                    if t not in seen_unit_snip[dedup_key]["matched_terms"]:
                        seen_unit_snip[dedup_key]["matched_terms"].append(t)
                    continue

                w = {
                    "source": src_kind,
                    "label": (
                        f"{chosen['field_label']} (Reviewed Revision #{chosen['revision_number']})"
                        if src_kind == "reviewed"
                        else "Machine extraction — unreviewed"
                    ),
                    "revision_number": chosen.get("revision_number"),
                    "field_key": chosen.get("field_key"),
                    "page_number": chosen.get("page_number"),
                    "is_fallback": chosen["is_fallback"],
                    "matched_terms": [t],
                    "snippet": snip["snippet"],
                    "snippet_utf16_length": snip["utf16_length"],
                    "segments": snip["segments"],
                }
                seen_unit_snip[dedup_key] = w
                witnesses.append(w)

            matched_cards.append({
                "document_id": doc_id,
                "submitted_at_micros": doc["submitted_at_micros"],
                "status": doc["status"],
                "display_title": display_title,
                "latest_reviewed_revision": latest_rev["revision_number"] if latest_rev else None,
                "current_head_revision": head_rev["revision_number"] if head_rev else 0,
                "current_head_status": head_rev["status"] if head_rev else "unreviewed",
                "has_newer_draft": has_newer_draft,
                "contributing_sources": contributing_sources,
                "witnesses": witnesses,
                "has_more_matches": total_unit_term_matches > len(witnesses),
            })
            if len(matched_cards) >= limit + 1:
                break

        has_more = len(matched_cards) > limit
        page_items = matched_cards[:limit]
        next_cursor = (
            encode_keyset_cursor(
                page_items[-1]["submitted_at_micros"],
                page_items[-1]["document_id"],
                source,
                terms,
            )
            if has_more and page_items
            else None
        )
        return 200, {
            "items": page_items,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }


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


def build_inventory_payload(repo_root: Path, head_sha: str, preserved_oids: dict[str, str]) -> dict:
    diff_lines = run_git(repo_root, "diff", "--name-status", ROOT_REPORT_001_SHA, head_sha).splitlines()
    deliverable_files: list[dict] = []
    for line in diff_lines:
        if not line.strip():
            continue
        status_tok, rel_path = line.split("\t", 1)
        raw_bytes = (repo_root / rel_path).read_bytes()
        lf_bytes = raw_bytes.replace(b"\r\n", b"\n")
        blob_oid = run_git(repo_root, "rev-parse", f"{head_sha}:{rel_path}")
        deliverable_files.append({
            "path": rel_path,
            "git_status": status_tok,
            "blob_oid": blob_oid,
            "bytes_raw": len(raw_bytes),
            "bytes_lf": len(lf_bytes),
            "sha256_raw": sha256_hex(raw_bytes),
            "sha256_lf": sha256_hex(lf_bytes),
        })
    return {
        "schema": "eledgercare.wp-0010.f4-design-review-inventory/1",
        "reviewer": "eld-f4-reviewer",
        "branch": "review/wp-0010-f4",
        "packet_base_sha": PACKET_BASE_SHA,
        "authority_sha": AUTHORITY_SHA,
        "reviewed_design_candidate_sha": DESIGN_CANDIDATE_SHA,
        "review_execution_base_sha": ROOT_REPORT_001_SHA,
        "frozen_deliverable_sha": head_sha,
        "deliverable_file_count": len(deliverable_files),
        "deliverable_files": deliverable_files,
        "preserved_tree_oids": preserved_oids,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify WP-0010 /002 F4 archive design review.")
    parser.add_argument("--output", required=True, help="Output JSON verification receipt path")
    parser.add_argument("--inventory-output", help="Optional output JSON inventory path")
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

    # 1. Git status, owned branch, ancestry, exact candidate/authority/report diffs, and protected trees
    status_before = run_git(repo_root, "status", "--porcelain", "--untracked-files=normal")
    if args.require_clean:
        record_assert("clean_worktree_before_execution", status_before == "", {"status_porcelain": status_before})

    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    branch_name = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    record_assert("owned_branch_identity", branch_name == "review/wp-0010-f4", {"branch": branch_name, "head": head_sha})

    anc_ok = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ROOT_REPORT_001_SHA, head_sha],
        cwd=repo_root,
        check=False,
    ).returncode == 0
    record_assert("dispatch_001_is_ancestor_of_head", anc_ok, {"dispatch_001": ROOT_REPORT_001_SHA, "head": head_sha})

    auth_diff = dict(
        line.split("\t", 1)[::-1]
        for line in run_git(repo_root, "diff", "--name-status", PACKET_BASE_SHA, AUTHORITY_SHA).splitlines()
    )
    record_assert(
        "exact_7_path_authority_diff",
        auth_diff == EXPECTED_AUTHORITY_DIFF,
        {"count": len(auth_diff), "paths": sorted(auth_diff)},
    )

    cand_diff = dict(
        line.split("\t", 1)[::-1]
        for line in run_git(repo_root, "diff", "--name-status", PACKET_BASE_SHA, DESIGN_CANDIDATE_SHA).splitlines()
    )
    record_assert(
        "exact_9_path_candidate_diff",
        cand_diff == EXPECTED_CANDIDATE_DIFF,
        {"count": len(cand_diff), "paths": sorted(cand_diff)},
    )

    rep_diff = run_git(repo_root, "diff", "--name-status", DESIGN_CANDIDATE_SHA, ROOT_REPORT_001_SHA).splitlines()
    record_assert(
        "report_001_single_file_addition",
        rep_diff == ["A\tdocs/agent-reports/eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md"],
        {"diff": rep_diff},
    )

    if head_sha != ROOT_REPORT_001_SHA:
        owned_diff = run_git(repo_root, "diff", "--name-only", ROOT_REPORT_001_SHA, head_sha).splitlines()
        record_assert(
            "reviewer_owned_paths_only",
            all(
                p.startswith("docs/reviews/WP-0010/eld-f4-reviewer/design/")
                or p == "docs/agent-reports/eld-f4-reviewer/WP-0010/002_2026-11-17_review_eld-f4-reviewer.md"
                for p in owned_diff
            ),
            {"owned_diff_paths": owned_diff},
        )

    preserved_oids: dict[str, str] = {}
    for rel in PRESERVED_TREE_PATHS:
        base_oid = run_git(repo_root, "rev-parse", f"{PACKET_BASE_SHA}:{rel}")
        cand_oid = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE_SHA}:{rel}")
        tip_oid = run_git(repo_root, "rev-parse", f"{ROOT_REPORT_001_SHA}:{rel}")
        head_oid = run_git(repo_root, "rev-parse", f"{head_sha}:{rel}")
        record_assert(f"preserved_oid:{rel}", base_oid == cand_oid == tip_oid == head_oid, {"oid": head_oid})
        preserved_oids[rel] = head_oid

    for rel in PRODUCT_TREE_PATHS:
        f3_oid = run_git(repo_root, "rev-parse", f"{ACCEPTED_F3_SOURCE_SHA}:{rel}")
        record_assert(f"matches_accepted_f3_source:{rel}", f3_oid == preserved_oids[rel], {"oid": f3_oid})

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
    base_reports = run_git(repo_root, "ls-tree", "-r", "--name-only", PACKET_BASE_SHA, "docs/agent-reports").splitlines()
    tip_reports = run_git(repo_root, "ls-tree", "-r", "--name-only", ROOT_REPORT_001_SHA, "docs/agent-reports").splitlines()
    record_assert(
        "historical_reports_immutable",
        hist_report_changes == "" and len(base_reports) == 68 and len(tip_reports) == 69,
        {"base_count": len(base_reports), "tip_001_count": len(tip_reports)},
    )

    design_blob = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE_SHA}:docs/design/F4-source-linked-archive.md")
    kickoff_blob = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE_SHA}:docs/kickoffs/WP-0010-eld-f4-reviewer-design.md")
    authority_blob = run_git(repo_root, "rev-parse", f"{DESIGN_CANDIDATE_SHA}:docs/coordination/WP-0010-0011-authority.md")
    report_001_blob = run_git(
        repo_root,
        "rev-parse",
        f"{ROOT_REPORT_001_SHA}:docs/agent-reports/eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md",
    )
    dossier_text = reader.read_text("docs/reviews/WP-0010/eld-f4-reviewer/design/README.md")
    prep_text = reader.read_text("docs/reviews/WP-0010/eld-f4-reviewer/design/preparation-findings.md")
    record_assert(
        "reviewed_blob_oids_match_and_pinned_in_dossier",
        (
            design_blob == EXPECTED_DESIGN_BLOB
            and kickoff_blob == EXPECTED_KICKOFF_BLOB
            and authority_blob == EXPECTED_AUTHORITY_BLOB
            and report_001_blob == EXPECTED_REPORT_001_BLOB
            and design_blob in dossier_text
            and report_001_blob in dossier_text
            and design_blob in prep_text
        ),
        {
            "design_blob": design_blob,
            "kickoff_blob": kickoff_blob,
            "authority_blob": authority_blob,
            "report_001_blob": report_001_blob,
        },
    )

    # 2. Primary-source anchors in accepted F1..F3 codebase
    setup_cluster_ps1 = reader.read_text("deploy/dev/postgres/setup-cluster.ps1")
    grant_sql = reader.read_text("deploy/dev/database/grant-runtime.sql")
    parser_cs = reader.read_text("src/ELedgerCare.Domain/Processing/SafeNativeDisplayParser.cs")
    ext_store_cs = reader.read_text("src/ELedgerCare.Infrastructure/Persistence/ExtractionStore.cs")
    rev_store_cs = reader.read_text("src/ELedgerCare.Infrastructure/Persistence/WorkOrderReviewStore.cs")
    db_ctx_cs = reader.read_text("src/ELedgerCare.Infrastructure/Persistence/ELedgerCareDbContext.cs")
    pm_tests_cs = reader.read_text("tests/ELedgerCare.Infrastructure.Tests/PersistenceMappingTests.cs")
    di_tests_cs = reader.read_text("tests/ELedgerCare.Acceptance.Tests/DurableIntakeTests.cs")
    pdf_url_ts = reader.read_text("web/src/app/review/pdf-preview-url.ts")
    rev_page_ts = reader.read_text("web/src/app/review/work-order-review-page.ts")

    record_assert(
        "primary_source_anchors_verified",
        (
            "--encoding=UTF8 --no-locale" in setup_cluster_ps1
            and "GRANT UPDATE (\n    current_revision_number," in grant_sql.replace("\r\n", "\n")
            and "internal static IReadOnlyList<IReadOnlyList<string>> ParsePlainTableRows" in parser_cs
            and "WHERE job_id = @jobId AND status = 'running' AND latest_fencing_token = @token" in ext_store_cs
            and "public async Task<GetReviewRevisionOutcome> GetRevisionAsync" in rev_store_cs
            and 'ux_work_order_review_revisions_document_revision' in db_ctx_cs
            and "Assert.Equal(15, foreignKeys.Count);" in pm_tests_cs
            and "Migrated_schema_has_logged_tables_restrict_foreign_keys_and_designed_constraints" in di_tests_cs
            and "strictSameOriginPreviewRegex" in pdf_url_ts
            and "unsavedReviewChangesGuard" in rev_page_ts
        ),
        {"pg_initdb_locale": "C (--no-locale)", "current_fk_count": 15},
    )

    # 3. Genuine F2 seed artifacts & SafeNativeDisplayParser machine projection feasibility
    f01_pdf = reader.read_bytes("tests/fixtures/SYN-WO-01-v1-raster300.pdf")
    f07_pdf = reader.read_bytes("tests/fixtures/SYN-MP-01-v0-clean.pdf")
    f1_pdf = reader.read_bytes("tests/fixtures/F1-SWO-001.pdf")
    f01_raw = reader.read_bytes(
        "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e571-297a-7f0e-a293-e9e1c0851cd4/output/raw_output.utf8.bin"
    )
    f07_raw = reader.read_bytes(
        "docs/reviews/WP-0006/eld-next-reviewer/runtime-execution/runs/attempt-01a1e573-ca25-733e-b048-44c8ea2ac61d/output/raw_output.utf8.bin"
    )
    f01_author_raw = reader.read_bytes(
        "docs/implementation/WP-0006/runtime-author-v2/runs/attempt-01a1e509-f5d4-7a01-80f1-4f23fe282930/output/raw_output.utf8.bin"
    )
    f07_author_raw = reader.read_bytes(
        "docs/implementation/WP-0006/runtime-author-v2/runs/attempt-01a1e50c-bdb9-7477-a96a-abb58323c615/output/raw_output.utf8.bin"
    )

    record_assert(
        "genuine_f2_seed_digests_and_author_reviewer_parity",
        (
            len(f01_pdf) == 372258
            and sha256_hex(f01_pdf) == F01_PDF_SHA256
            and len(f07_pdf) == 8422
            and sha256_hex(f07_pdf) == F07_PDF_SHA256
            and len(f1_pdf) == 887
            and sha256_hex(f1_pdf) == F1_PDF_SHA256
            and len(f01_raw) == 3236
            and sha256_hex(f01_raw) == sha256_hex(f01_author_raw) == F01_RAW_SHA256
            and len(f07_raw) == 7511
            and sha256_hex(f07_raw) == sha256_hex(f07_author_raw) == F07_RAW_SHA256
        ),
        {"syn_wo_01_raw_sha256": F01_RAW_SHA256, "syn_mp_01_raw_sha256": F07_RAW_SHA256},
    )

    wo_proj = build_machine_projection(
        "01a1e573-a855-7735-96e1-f5d14cada602",
        "01a1e571-1111-7000-8000-000000000001",
        f01_raw,
        1,
    )
    mp_proj = build_machine_projection(
        "01a1e578-8bfa-7bba-b104-ea8309dbfd9e",
        "01a1e573-2222-7000-8000-000000000002",
        f07_raw,
        3,
    )
    record_assert(
        "genuine_f2_machine_projections_clean_and_markup_free",
        (
            wo_proj["unit_count"] == 1
            and not wo_proj["has_fallback"]
            and wo_proj["units"][0]["page_number"] == 1
            and "0018-TERM-QC" in wo_proj["units"][0]["searchable_text"]
            and "<table" not in wo_proj["units"][0]["searchable_text"].lower()
            and mp_proj["unit_count"] == 3
            and not mp_proj["has_fallback"]
            and [u["page_number"] for u in mp_proj["units"]] == [1, 2, 3]
            and "MP01-P2" in mp_proj["units"][1]["searchable_text"]
            and "$1,535.35" in mp_proj["units"][2]["searchable_text"]
            and "colspan" not in mp_proj["units"][1]["searchable_text"].lower()
            and "<td>" not in mp_proj["units"][2]["searchable_text"].lower()
        ),
        {
            "wo_unit_count": wo_proj["unit_count"],
            "mp_pages": [u["page_number"] for u in mp_proj["units"]],
            "wo_projection_sha256": wo_proj["projection_sha256"],
            "mp_projection_sha256": mp_proj["projection_sha256"],
        },
    )

    # Edge cases for F4-BIC-02: non-cell table caption/orphaned text, missing <PAGE>, U+0000 byte, and empty result marker
    caption_table = "<PAGE><BLOCK>table[0,0,10,10]<FORK><table><caption>Schedule 99-Z</caption><tr><td>Cell Alpha</td></tr></table>"
    naive_rows = parse_plain_table_rows_f2("<table><caption>Schedule 99-Z</caption><tr><td>Cell Alpha</td></tr></table>")
    cap_proj = build_machine_projection("res-cap", "00000000-0000-7000-8000-000000000010", caption_table.encode("utf-8"), 1)
    no_page_proj = build_machine_projection(
        "res-nopage",
        "00000000-0000-7000-8000-000000000011",
        b"Unstructured raw OCR output without page token",
        1,
    )
    nul_proj = build_machine_projection(
        "res-nul",
        "00000000-0000-7000-8000-000000000012",
        b"<PAGE><BLOCK>text[0,0,1,1]<FORK>Boiler\x00Check 007",
        1,
    )
    empty_proj = build_machine_projection(
        "res-empty",
        "00000000-0000-7000-8000-000000000013",
        b"<PAGE>   \r\n  ",
        1,
    )
    record_assert(
        "bic02_projection_fallbacks_nul_safety_and_empty_marker",
        (
            naive_rows == [["Cell Alpha"]]
            and cap_proj["has_fallback"]
            and any("Schedule 99-Z" in u["searchable_text"] and u["is_fallback"] for u in cap_proj["units"])
            and no_page_proj["unit_count"] == 1
            and no_page_proj["units"][0]["page_number"] is None
            and no_page_proj["units"][0]["is_fallback"]
            and "\x00" not in nul_proj["units"][0]["searchable_text"]
            and "Boiler\ufffdCheck 007" == nul_proj["units"][0]["searchable_text"]
            and empty_proj["unit_count"] == 0
            and empty_proj["units"] == []
            and len(empty_proj["projection_sha256"]) == 64
        ),
        {
            "naive_rows_dropped_caption": True,
            "fallback_preserved_caption": True,
            "missing_page_coordinate": no_page_proj["units"][0]["page_number"],
            "empty_marker_unit_count": empty_proj["unit_count"],
        },
    )

    # 4. Literal SQL LIKE escaping & C-locale collation parity (F4-BIC-01)
    sample_haystack = r"7.50% discount on SKU_0042 \ path Café Élite"
    record_assert(
        "bic01_literal_like_escaping_and_c_locale_collation",
        (
            postgres_c_ilike_evaluate(sample_haystack, escape_postgres_like_literal("7.50%"))
            and not postgres_c_ilike_evaluate("7.500 discount", escape_postgres_like_literal("7.50%"))
            and postgres_c_ilike_evaluate(sample_haystack, escape_postgres_like_literal("SKU_0042"))
            and not postgres_c_ilike_evaluate("SKUX0042", escape_postgres_like_literal("SKU_0042"))
            and postgres_c_ilike_evaluate(sample_haystack, escape_postgres_like_literal("\\"))
            and postgres_c_ilike_evaluate(sample_haystack, escape_postgres_like_literal("sku_0042"))
            # C-locale: ASCII folds ('sku' == 'SKU'), non-ASCII 'É' != 'é'
            and postgres_c_ilike_evaluate(sample_haystack, escape_postgres_like_literal("Élite"))
            and not postgres_c_ilike_evaluate(sample_haystack, escape_postgres_like_literal("élite"))
            # Soft-hyphen U+00AD is literal in Postgres ILIKE, never ignored
            and not postgres_c_ilike_evaluate("work\u00adorder", escape_postgres_like_literal("workorder"))
        ),
        {"escaped_backslash_pattern": escape_postgres_like_literal("\\")},
    )

    # 5. Query validation bounds (NUL, lone surrogates, controls, duplicate/unknown keys, >8 terms, >64 term, >160 total, limit)
    invalid_cases = [
        ("unknown_param", [("foo", "1")], "unknown_query_parameter"),
        ("dup_q", [("q", "a"), ("q", "b")], "duplicate_query_parameter"),
        ("empty_source", [("source", "")], "invalid_source_filter"),
        ("bad_source", [("source", "fuzzy")], "invalid_source_filter"),
        ("zero_limit", [("limit", "0")], "invalid_limit"),
        ("leading_zero_limit", [("limit", "05")], "invalid_limit"),
        ("over_max_limit", [("limit", "51")], "invalid_limit"),
        ("nul_in_q", [("q", "pump\x00valve")], "null_character_forbidden"),
        ("lone_high_surrogate", [("q", "ab\ud800cd")], "unpaired_surrogate_forbidden"),
        ("lone_low_surrogate", [("q", "\udc00abc")], "unpaired_surrogate_forbidden"),
        ("bell_control", [("q", "pump\x07")], "control_character_forbidden"),
        ("nine_terms", [("q", "t1 t2 t3 t4 t5 t6 t7 t8 t9")], "too_many_query_terms"),
        ("term_65_chars", [("q", "a" * 65)], "query_term_too_long"),
        ("total_161_chars", [("q", ("a" * 53) + " " + ("b" * 53) + " " + ("c" * 53))], "query_too_long"),
    ]
    for case_name, q_params, expected_code in invalid_cases:
        st, body = validate_and_parse_archive_query(q_params)
        record_assert(f"query_rejection:{case_name}", st == 400 and body["code"] == expected_code, body)

    # Astral scalar wrench 🔧 (U+1F527 = 2 UTF-16 code units): 32 wrenches = 64 UTF-16 units (accepted), 33 = 66 UTF-16 units (rejected!)
    ok_32_wrenches, _ = validate_and_parse_archive_query([("q", "🔧" * 32)])
    bad_33_wrenches, err_33 = validate_and_parse_archive_query([("q", "🔧" * 33)])
    record_assert(
        "utf16_astral_term_length_ceiling",
        ok_32_wrenches == 200 and bad_33_wrenches == 400 and err_33["code"] == "query_term_too_long",
        {"wrench_32_utf16_units": utf16_code_units("🔧" * 32), "wrench_33_utf16_units": utf16_code_units("🔧" * 33)},
    )

    # 6. Surrogate-safe <=240 UTF-16 snippet clipping & inert XSS segments (F4-BIC-06)
    long_astral_prefix = "🔧" * 80  # 160 UTF-16 code units (odd clipping offsets land inside surrogate pairs!)
    long_astral_suffix = "🔧" * 80
    hostile_doc_text = f"{long_astral_prefix}<script>window.__xss=1</script> TARGET-0099 <img src=x onerror=alert(1)>{long_astral_suffix}"
    clipped = clip_surrogate_safe_witness_snippet(hostile_doc_text, "target-0099", 240)
    record_assert(
        "bic06_surrogate_safe_240_snippet_and_inert_xss_segments",
        (
            clipped["utf16_length"] <= 240
            and clipped["prefix_clipped"]
            and clipped["suffix_clipped"]
            and "TARGET-0099" in clipped["snippet"]
            and "<script>window.__xss=1</script>" in clipped["snippet"]
            and any(s["highlighted"] and s["text"] == "TARGET-0099" for s in clipped["segments"])
            and "".join(s["text"] for s in clipped["segments"]) == clipped["snippet"]
        ),
        {"snippet_utf16_length": clipped["utf16_length"], "segment_count": len(clipped["segments"])},
    )

    # 7. Full Archive Simulator: readiness 503, competing initializers, revision replacement, unknown removal,
    #    newer draft isolation, cross-page/field/source AND without cross-doc bleed, and microsecond/UUID keyset paging
    sim = ArchiveSimulator()
    t_base = int(datetime(2026, 11, 17, 3, 0, 0, tzinfo=timezone.utc).timestamp() * 1_000_000)

    doc_unproc = "01a20000-0000-7000-8000-000000000001"
    doc_wo = "01a20000-0000-7000-8000-000000000002"
    doc_mp = "01a20000-0000-7000-8000-000000000003"

    sim.submit_document(doc_unproc, t_base + 300, 2, status="awaiting_extraction")
    sim.submit_document(doc_wo, t_base + 200, 1)
    sim.submit_document(doc_mp, t_base + 200, 3)  # Same microsecond timestamp as doc_wo to test UUID tie-breaker!

    sim.seed_unprojected_result("res-wo", doc_wo, f01_raw, 1)
    sim.seed_unprojected_result("res-mp", doc_mp, f07_raw, 3)

    # Before initializer completes -> explicit 503 archive_not_ready (never misleading empty 200 OK!)
    pre_st, pre_body = sim.search([])
    record_assert("not_ready_returns_503", pre_st == 503 and pre_body["code"] == "archive_not_ready", pre_body)

    # Two competing initializers run sequentially/idempotently on same state -> both succeed with identical projection_sha256
    init1_ok, init1_err = sim.run_backfill_initializer()
    snap_after_1 = dict(sim.projections)
    init2_ok, init2_err = sim.run_backfill_initializer()
    record_assert(
        "two_initializers_idempotent_reconciliation",
        init1_ok and init2_ok and init1_err is None and init2_err is None and sim.projections == snap_after_1,
        {"projected_results": len(sim.projections)},
    )

    # Conflict detection: tampered projection digest surfaces diagnostic 503 without mutating extraction_results
    sim_conflict = ArchiveSimulator()
    sim_conflict.submit_document(doc_wo, t_base, 1)
    sim_conflict.seed_unprojected_result("res-wo", doc_wo, f01_raw, 1)
    sim_conflict.run_backfill_initializer()
    sim_conflict.projections[("res-wo", ArchiveSimulator.PROJECTION_VERSION)]["raw_output_sha256"] = "0" * 64
    conf_ok, conf_err = sim_conflict.run_backfill_initializer()
    conf_st, _ = sim_conflict.search([("q", "WO-004192")])
    record_assert(
        "conflicting_projection_fails_closed_503",
        (not conf_ok) and conf_err == "projection_conflict:res-wo" and conf_st == 503,
        {"conflict_error": conf_err},
    )

    # Fenced-out or failed-transaction publish exposes neither result nor projection
    fenced_res = sim.publish_completed_result_atomic("res-fenced", doc_unproc, f01_raw, 1, fenced_out=True)
    rolled_res = sim.publish_completed_result_atomic("res-rolled", doc_unproc, f01_raw, 1, fail_mid_tx=True)
    record_assert(
        "fenced_and_rolled_back_publishes_expose_nothing",
        (not fenced_res)
        and (not rolled_res)
        and ("res-fenced", ArchiveSimulator.PROJECTION_VERSION) not in sim.projections
        and ("res-rolled", ArchiveSimulator.PROJECTION_VERSION) not in sim.projections,
        {"unproc_status": sim.documents[doc_unproc]["status"]},
    )

    # Review lifecycle on doc_wo:
    # Rev #1 (draft): edits property_name to "DRAFT-ONLY-NAME" -> must NOT be searchable or used as card title!
    sim.save_review_revision(
        doc_wo,
        "draft",
        {
            "work_order_id": {"decision": "unreviewed", "value": None, "consulted_page_number": None},
            "property_name": {"decision": "edited", "value": "DRAFT-ONLY-NAME", "consulted_page_number": None},
            "building_unit": {"decision": "unreviewed", "value": None, "consulted_page_number": None},
            "requested_date": {"decision": "unreviewed", "value": None, "consulted_page_number": None},
            "issue_and_resolution": {"decision": "unreviewed", "value": None, "consulted_page_number": None},
        },
        operator_label="OP-SECRET-LABEL",
    )
    _, draft_only_hit = sim.search([("q", "DRAFT-ONLY-NAME")])
    _, browse_rev_when_draft_only = sim.search([("source", "reviewed")])
    record_assert(
        "draft_only_not_searched_and_excluded_from_reviewed_filter",
        len(draft_only_hit["items"]) == 0 and len(browse_rev_when_draft_only["items"]) == 0,
        {"draft_hits": 0},
    )

    # Rev #2 (reviewed): sets building_unit="Bldg B - Unit 204-REV2" (with provenance page 1) and property_name="Human Property NoCoords" (no provenance!)
    sim.save_review_revision(
        doc_wo,
        "reviewed",
        {
            "work_order_id": {"decision": "accepted", "value": "WO-004192", "consulted_page_number": 1},
            "property_name": {"decision": "edited", "value": "Human Property NoCoords", "consulted_page_number": None},
            "building_unit": {"decision": "edited", "value": "Bldg B - Unit 204-REV2", "consulted_page_number": 1},
            "requested_date": {"decision": "accepted", "value": "2026-10-16", "consulted_page_number": 1},
            "issue_and_resolution": {"decision": "unknown", "value": None, "unknown_reason": "REASON-NOT-SEARCHED", "consulted_page_number": None},
        },
        operator_label="OP-SECRET-LABEL",
    )

    # Rev #3 (reviewed): supersedes Rev #2 by marking building_unit="unknown" -> "204-REV2" removed from reviewed search!
    sim.save_review_revision(
        doc_wo,
        "reviewed",
        {
            "work_order_id": {"decision": "accepted", "value": "WO-004192", "consulted_page_number": 1},
            "property_name": {"decision": "edited", "value": "Human Property NoCoords", "consulted_page_number": None},
            "building_unit": {"decision": "unknown", "value": None, "unknown_reason": "UNIT-UNKNOWN-REASON", "consulted_page_number": None},
            "requested_date": {"decision": "accepted", "value": "2026-10-16", "consulted_page_number": 1},
            "issue_and_resolution": {"decision": "unknown", "value": None, "unknown_reason": "REASON-NOT-SEARCHED", "consulted_page_number": None},
        },
        operator_label="OP-SECRET-LABEL",
    )

    # Rev #4 (draft): newer draft head edits property_name="NEWER-UNAPPROVED-DRAFT" -> Rev #3 stays authoritative reviewed source + has_newer_draft=True!
    sim.save_review_revision(
        doc_wo,
        "draft",
        {
            "work_order_id": {"decision": "accepted", "value": "WO-004192", "consulted_page_number": 1},
            "property_name": {"decision": "edited", "value": "NEWER-UNAPPROVED-DRAFT", "consulted_page_number": None},
            "building_unit": {"decision": "unknown", "value": None, "unknown_reason": None, "consulted_page_number": None},
            "requested_date": {"decision": "accepted", "value": "2026-10-16", "consulted_page_number": 1},
            "issue_and_resolution": {"decision": "unreviewed", "value": None, "consulted_page_number": None},
        },
        operator_label="OP-SECRET-LABEL",
    )

    _, sup_rev_res = sim.search([("q", "204-REV2"), ("source", "reviewed")])
    _, mach_unit_res = sim.search([("q", "Unit 204"), ("source", "all")])
    _, unk_reason_res = sim.search([("q", "UNIT-UNKNOWN-REASON")])
    _, op_label_res = sim.search([("q", "OP-SECRET-LABEL")])
    _, newer_draft_res = sim.search([("q", "NEWER-UNAPPROVED-DRAFT")])
    _, no_coord_res = sim.search([("q", "NoCoords"), ("source", "reviewed")])
    _, cross_src_res = sim.search([("q", "NoCoords Oakbrook"), ("source", "all")])
    _, cross_doc_false_res = sim.search([("q", "NoCoords MP01-P3"), ("source", "all")])
    _, multi_page_and_res = sim.search([("q", "MP01-P1 MP01-P3"), ("source", "machine")])

    record_assert(
        "f4_02_03_revision_replacement_unknown_draft_provenance_and_and_semantics",
        (
            len(sup_rev_res["items"]) == 0
            and len(mach_unit_res["items"]) == 1
            and mach_unit_res["items"][0]["contributing_sources"] == ["machine"]
            and mach_unit_res["items"][0]["witnesses"][0]["label"] == "Machine extraction — unreviewed"
            and len(unk_reason_res["items"]) == 0
            and len(op_label_res["items"]) == 0
            and len(newer_draft_res["items"]) == 0
            and len(no_coord_res["items"]) == 1
            and no_coord_res["items"][0]["latest_reviewed_revision"] == 3
            and no_coord_res["items"][0]["current_head_revision"] == 4
            and no_coord_res["items"][0]["has_newer_draft"] is True
            and no_coord_res["items"][0]["display_title"] == "WO-004192 · Human Property NoCoords"
            # Human-edited value without coordinates has page_number=None (zero fabricated coordinates!)
            and no_coord_res["items"][0]["witnesses"][0]["page_number"] is None
            # Cross-source AND within doc_wo combines reviewed ('NoCoords') + machine ('Oakbrook')
            and len(cross_src_res["items"]) == 1
            and set(cross_src_res["items"][0]["contributing_sources"]) == {"reviewed", "machine"}
            and len(cross_src_res["items"][0]["witnesses"]) == 2
            # Never ANDs across two different documents!
            and len(cross_doc_false_res["items"]) == 0
            # Multi-page AND within 3-page SYN-MP-01 matches Page 1 and Page 3
            and len(multi_page_and_res["items"]) == 1
            and [w["page_number"] for w in multi_page_and_res["items"][0]["witnesses"]] == [1, 3]
        ),
        {
            "latest_reviewed": 3,
            "current_head_draft": 4,
            "cross_source_witness_count": len(cross_src_res["items"][0]["witnesses"]),
        },
    )

    # Keyset pagination: empty query source=all has 3 docs:
    # 1st: doc_unproc (t_base + 300)
    # 2nd: doc_mp     (t_base + 200, '...0003' > '...0002' in RFC 4122 hex DESC!)
    # 3rd: doc_wo     (t_base + 200, '...0002')
    p1_st, p1 = sim.search([("limit", "2")])
    p2_st, p2 = sim.search([("limit", "2"), ("after", p1["next_cursor"])])
    mismatch_q_st, mismatch_q = sim.search([("q", "WO-004192"), ("after", p1["next_cursor"])])
    mismatch_src_st, mismatch_src = sim.search([("source", "machine"), ("after", p1["next_cursor"])])
    oversized_cur_st, _ = sim.search([("after", "A" * 257)])

    record_assert(
        "f4_04_deterministic_keyset_pagination_and_cursor_binding",
        (
            p1_st == 200
            and p1["has_more"] is True
            and [x["document_id"] for x in p1["items"]] == [doc_unproc, doc_mp]
            and p2_st == 200
            and p2["has_more"] is False
            and p2["next_cursor"] is None
            and [x["document_id"] for x in p2["items"]] == [doc_wo]
            and mismatch_q_st == 400
            and mismatch_q["code"] == "cursor_query_mismatch"
            and mismatch_src_st == 400
            and mismatch_src["code"] == "cursor_query_mismatch"
            and oversized_cur_st == 400
        ),
        {"page_1_ids": [x["document_id"] for x in p1["items"]], "page_2_ids": [x["document_id"] for x in p2["items"]]},
    )

    # 8. Port disjointness across F1, F2, F3, and F4 (8 triplets = 24 unique ports)
    all_ports = [port for triplet in PORT_RESERVATIONS.values() for port in triplet]
    record_assert(
        "port_disjointness_across_f1_f2_f3_f4",
        len(all_ports) == 24 and len(set(all_ports)) == 24,
        {
            "distinct_port_count": len(set(all_ports)),
            "f4_author": list(PORT_RESERVATIONS["f4_author"]),
            "f4_reviewer": list(PORT_RESERVATIONS["f4_reviewer"]),
        },
    )

    # 9. Local Markdown link checks & zero sealed/WP-0011 paths opened
    md_to_check = [
        "docs/design/F4-source-linked-archive.md",
        "docs/coordination/WP-0010-0011-authority.md",
        "docs/agent-reports/eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md",
        "docs/reviews/WP-0010/eld-f4-reviewer/design/preparation-findings.md",
        "docs/reviews/WP-0010/eld-f4-reviewer/design/README.md",
        *args.extra_md,
    ]
    checked_links = verify_markdown_links(reader, repo_root, md_to_check)
    record_assert(
        "local_markdown_links_resolve",
        len(checked_links) > 0,
        {"checked_link_count": len(checked_links)},
    )

    refused_probes: list[str] = []
    for forbidden_probe in (
        "docs/kickoffs/WP-0011-eld-eval-custodian.md",
        "../eld-coverage-custodian/README.md",
        "../../eLedgerCare-Q0/WP-0005",
    ):
        try:
            reader.read_bytes(forbidden_probe)
        except PermissionError:
            refused_probes.append(forbidden_probe)
    record_assert(
        "safe_repo_reader_refuses_wp0011_and_external_paths",
        len(refused_probes) == 3,
        {"refused_probes": refused_probes},
    )

    opened_unique = sorted(set(reader.opened_paths))
    record_assert(
        "zero_sealed_or_wp0011_paths_opened",
        all(not any(bad in p.lower() for bad in FORBIDDEN_PATH_SUBSTRINGS) for p in opened_unique),
        {"opened_file_count": len(opened_unique)},
    )

    helper_raw = script_path.read_bytes()
    helper_lf = helper_raw.replace(b"\r\n", b"\n")
    receipt = {
        "schema": "eledgercare.wp-0010.f4-design-review-receipt/1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "eld-f4-reviewer",
        "branch": branch_name,
        "frozen_head_sha": head_sha,
        "packet_base_sha": PACKET_BASE_SHA,
        "authority_sha": AUTHORITY_SHA,
        "reviewed_design_candidate_sha": DESIGN_CANDIDATE_SHA,
        "reviewed_root_report_001_sha": ROOT_REPORT_001_SHA,
        "accepted_f3_source_sha": ACCEPTED_F3_SOURCE_SHA,
        "accepted_f3_review_007_sha": ACCEPTED_F3_REVIEW_007_SHA,
        "accepted_f3_closure_005_sha": ACCEPTED_F3_CLOSURE_005_SHA,
        "reviewed_blobs": {
            "docs/design/F4-source-linked-archive.md": design_blob,
            "docs/kickoffs/WP-0010-eld-f4-reviewer-design.md": kickoff_blob,
            "docs/coordination/WP-0010-0011-authority.md": authority_blob,
            "docs/agent-reports/eld-coordinator/WP-0010/001_2026-11-17_design_eld-coordinator.md": report_001_blob,
        },
        "helper_path": "docs/reviews/WP-0010/eld-f4-reviewer/design/verify_f4_design.py",
        "helper_sha256_raw": sha256_hex(helper_raw),
        "helper_sha256_lf": sha256_hex(helper_lf),
        "verdicts": {
            "f4_design": "accepted",
            "concrete_design_blockers": 0,
            "kickoff_bindings": ["F4-KR-01"],
            "implementation_checkpoints": [f"F4-BIC-0{i}" for i in range(1, 9)],
        },
        "preserved_tree_oids": preserved_oids,
        "genuine_f2_projection_summary": {
            "syn_wo_01": {
                "raw_sha256": wo_proj["raw_output_sha256"],
                "unit_count": wo_proj["unit_count"],
                "has_fallback": wo_proj["has_fallback"],
                "projection_sha256": wo_proj["projection_sha256"],
            },
            "syn_mp_01": {
                "raw_sha256": mp_proj["raw_output_sha256"],
                "unit_count": mp_proj["unit_count"],
                "pages": [u["page_number"] for u in mp_proj["units"]],
                "has_fallback": mp_proj["has_fallback"],
                "projection_sha256": mp_proj["projection_sha256"],
            },
        },
        "checked_markdown_links": checked_links,
        "opened_repo_paths": opened_unique,
        "assertion_count": len(assertions),
        "all_assertions_passed": True,
        "assertions": assertions,
    }

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = repo_root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    if args.inventory_output:
        inv_path = Path(args.inventory_output)
        if not inv_path.is_absolute():
            inv_path = repo_root / inv_path
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        inv_payload = build_inventory_payload(repo_root, head_sha, preserved_oids)
        inv_path.write_text(json.dumps(inv_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    print(f"PASS: {len(assertions)} assertions verified at HEAD {head_sha}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
