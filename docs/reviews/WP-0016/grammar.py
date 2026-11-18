"""Named structural grammar for raw native page output: rd-wp0016-native-structure-v1. Stdlib only.

Structural evidence only. A syntactically valid header establishes neither a correct box nor the
existence of a table. More well-formed tags are never treated as factual truth and never change a score.

  page      := "<PAGE>" preamble block*
  block     := header content
  header    := "<BLOCK>" label level? ws* box "<FORK>"
  label     := [\\w-]+                          (identical to the frozen adapter's formats.BLOCK)
  level     := "<LEVEL" digit+ ">"              (documented for label "title" only; public rule 0186467)
  box       := "[" ws* int "," ws* int "," ws* int "," ws* int ws* "]"
  box-valid := every int <= 999, x1 < x2, y1 < y2   (frozen adapter's good_box)
  content   := any text up to the next "<BLOCK>" or end; may contain <table>...</table>

Each "<BLOCK>" occurrence gets exactly one header class:
  frozen              accepted by the frozen adapter (no level)
  title_level         documented title<LEVELn> header; accepted only by the public title rule
  undocumented_level  <LEVELn> on a non-title label
  malformed           no header production matches; reason is recorded
Independently, a syntactically complete header whose box fails box-valid is counted as box_invalid.
"""
import re
from collections import Counter

NAME = "rd-wp0016-native-structure-v1"
HEADER = re.compile(r"<BLOCK>(?P<label>[\w-]+)(?:<LEVEL(?P<level>\d+)>)?\s*"
                    r"\[\s*(?P<x1>\d+),\s*(?P<y1>\d+),\s*(?P<x2>\d+),\s*(?P<y2>\d+)\s*\]<FORK>")
BOX_SYNTAX = re.compile(r"\s*\[\s*\d+,\s*\d+,\s*\d+,\s*\d+\s*\]\s*")
SPECIAL = re.compile(r"<(/?)([A-Z][A-Z0-9_]*)>")
KNOWN = {"PAGE", "BLOCK", "FORK"}
LEVEL = re.compile(r"<LEVEL\d+>")
TABLE_OPEN = re.compile(r"<table\b", re.I)
TABLE_CLOSE = re.compile(r"</table\s*>", re.I)


def classify_page(raw, frozen_block=None, title_rule=None):
    """Counts only (no text). Optional pinned regexes cross-check this parser against the frozen ones."""
    out = dict(grammar=NAME, page_marker_ok=raw.startswith("<PAGE>") and raw.count("<PAGE>") == 1)
    body = raw[len("<PAGE>"):] if raw.startswith("<PAGE>") else raw
    starts = [m.start() for m in re.finditer(r"<BLOCK>", body)]
    classes, reasons, labels = Counter(), Counter(), Counter()
    header_ends, box_invalid, empty = set(), 0, 0
    for k, pos in enumerate(starts):
        nxt = starts[k + 1] if k + 1 < len(starts) else len(body)
        m = HEADER.match(body, pos)
        if m and m.end() <= nxt:
            label, level = m.group("label"), m.group("level")
            if level is None:
                classes["frozen"] += 1
            elif label == "title":
                classes["title_level"] += 1
            else:
                classes["undocumented_level"] += 1
            labels[label] += 1
            header_ends.add(m.end())
            x1, y1, x2, y2 = (int(m.group(g)) for g in ("x1", "y1", "x2", "y2"))
            if not (max(x1, y1, x2, y2) <= 999 and x1 < x2 and y1 < y2):
                box_invalid += 1
            if not body[m.end():nxt].strip():
                empty += 1
            continue
        classes["malformed"] += 1
        region = body[pos + len("<BLOCK>"):nxt]
        if "<FORK>" not in region:
            reasons["no_fork_before_next_block_or_end"] += 1
            continue
        head = region[:region.index("<FORK>")]
        lab = re.match(r"[\w-]+", head)
        rest = head[lab.end():] if lab else head
        rest = LEVEL.sub("", rest, count=1) if rest.startswith("<LEVEL") else rest
        if not lab:
            reasons["bad_label"] += 1
        elif "[" not in rest:
            reasons["no_box"] += 1
        elif not BOX_SYNTAX.fullmatch(rest):
            reasons["bad_box_syntax"] += 1
        else:
            reasons["other"] += 1
    forks = [m.end() for m in re.finditer(r"<FORK>", body)]
    specials = Counter()
    for m in SPECIAL.finditer(body):
        if m.group(2) not in KNOWN and not LEVEL.fullmatch(m.group(0)):
            specials[m.group(0)] += 1
    first = starts[0] if starts else len(body)
    opens, closes = len(TABLE_OPEN.findall(body)), len(TABLE_CLOSE.findall(body))
    out.update(blocks=len(starts), classes=dict(classes), malformed_reasons=dict(reasons), labels=dict(labels),
               box_invalid=box_invalid, empty_blocks=empty,
               orphan_fork=sum(e not in header_ends for e in forks),
               level_outside_header=len(LEVEL.findall(body)) - classes["title_level"] - classes["undocumented_level"],
               unknown_specials=dict(specials), preamble_nonspace_chars=len("".join(body[:first].split())),
               table_open=opens, table_close=closes, table_unbalanced=opens != closes)
    out["structurally_valid"] = (out["page_marker_ok"] and not classes["malformed"] and not classes["undocumented_level"]
                                 and not box_invalid and not out["orphan_fork"] and not out["level_outside_header"]
                                 and not specials and not out["table_unbalanced"])
    if frozen_block is not None:
        out["agrees_with_frozen_block"] = len(frozen_block.findall(body)) == classes["frozen"]
    if title_rule is not None:
        out["agrees_with_title_rule"] = len(title_rule.findall(raw)) == classes["title_level"]
    return out


def totals(pages):
    """Aggregate classify_page outputs."""
    t = Counter()
    reasons, specials, labels = Counter(), Counter(), Counter()
    for p in pages:
        t["pages"] += 1
        t["pages_structurally_valid"] += p["structurally_valid"]
        t["pages_with_malformed"] += bool(p["classes"].get("malformed"))
        t["page_marker_faults"] += not p["page_marker_ok"]
        for k in ("blocks", "box_invalid", "empty_blocks", "orphan_fork", "level_outside_header",
                  "preamble_nonspace_chars", "table_open", "table_close"):
            t[k] += p[k]
        t["table_unbalanced_pages"] += p["table_unbalanced"]
        for k, v in p["classes"].items():
            t["header_" + k] += v
        reasons.update(p["malformed_reasons"])
        specials.update(p["unknown_specials"])
        labels.update(p["labels"])
        t["parser_disagreements"] += (p.get("agrees_with_frozen_block") is False) + (p.get("agrees_with_title_rule") is False)
    return dict(grammar=NAME, **t, malformed_reasons=dict(reasons), unknown_specials=dict(specials), labels=dict(labels))
