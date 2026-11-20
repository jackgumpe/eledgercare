"""Join frozen scorer observations to routed Windows fields. Run only after prediction freeze."""
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import chain
import re

from score import layout, norm


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(rows, key):
    index = {row[key]: row for row in rows}
    require(len(index) == len(rows), f"duplicate {key}")
    return index


def field_links(truth, windows, fields):
    """Probe a geometry-identical copy. Text tags identify exactly which observed fields the scorer reads."""
    probes = deepcopy(windows["pages"])
    tags = {}
    sources = set()
    for index, field in enumerate(fields.values()):
        marker = f"WP20FIELD{index}END"
        p = field["page"]
        page = probes[p - 1]
        require(page["page"] == p and marker not in windows["pages"][p - 1]["text"], "invalid probe")
        tags[marker] = field["id"]
        if field["kind"] == "cell":
            table, row, col = (field[key] for key in ("table_index", "row_index", "col_index"))
            key = (p, table, row, col)
            require(key not in sources, "overlapping cell selectors")
            sources.add(key)
            page["tables"][table]["rows"][row][col] = marker
        else:
            require(field["kind"] == "prose" and field["span_indices"], "invalid prose selector")
        for span in field["span_indices"]:
            key = (p, span)
            require(key not in sources, "overlapping span selectors")
            sources.add(key)
            page["spans"][span]["text"] = marker
    refs_by_id = defaultdict(list)
    ids_by_ref = defaultdict(list)
    for ref, page in zip(truth["pages"], probes, strict=True):
        details = layout(ref, page, truth["source_sha256"])
        for item in chain(details["cells"], details["lines"]):
            for marker in sorted(set(re.findall(r"WP20FIELD\d+END", item["observed"] or ""))):
                fid = tags[marker]
                refs_by_id[fid].append(item["at"])
                ids_by_ref[item["at"]].append(fid)
    return refs_by_id, ids_by_ref


def references(truth, label):
    result = {}
    for page in truth["pages"]:
        prefix = f"page/{page['page']}"
        for i, line in enumerate(page["lines"], 1):
            result[f"{prefix}/line/{i}"] = dict(
                region="prose", printed_label_match=label(line["text"]), column=None)
        for ti, table in enumerate(page["tables"], 1):
            for ri, row in enumerate(table["rows"], 1):
                for ci, cell in enumerate(row, 1):
                    header = table["rows"][0][ci-1]["text"] if ci <= len(table["rows"][0]) else None
                    result[f"{prefix}/table/{ti}/row/{ri}/col/{ci}"] = dict(
                        region="header" if ri == 1 else "body", column=header,
                        printed_label_match=bool(ri > 1 and header and label(header)))
    return result


def observations(scored, view):
    rows = [row for page in scored["pages"] for row in
            (page["critical"] if view == "critical" else chain(page["cells"], page["lines"]))]
    return unique(rows, "at")


def transition(previous, current):
    return ("right" if previous else "wrong") + "_to_" + ("right" if current else "wrong")


def outcome(rows, selected):
    w, n, r = (rows[key]["correct"] for key in ("windows", "native", "routed"))
    status = ("substituted" if any(x["status"] == "substituted" for x in selected)
              else "unresolved" if selected else "outside_trigger")
    opportunity = None
    if not w and n:
        opportunity = ("recovered" if r else "substituted_not_recovered" if status == "substituted" else status)
    return dict(transition=transition(w, r), native_transition=transition(w, n), coverage=status,
                opportunity=opportunity, native_risk=w and not n, introduced=w and not r)


def field_rows(scores, view, reference, ids_by_ref, decisions):
    grids = {key: observations(value, view) for key, value in scores.items()}
    locs = grids["windows"]
    require(all(g.keys() == locs.keys() for g in grids.values()), "mismatched scorer locations")
    critical = observations(scores["windows"], "critical")
    evidence = []
    for at in locs:
        readings = {arm: grid[at] for arm, grid in grids.items()}
        w, n, r = (readings[key] for key in ("windows", "native", "routed"))
        expected = w["expected"]
        require(expected == n["expected"] == r["expected"], "mismatched expected value")
        selected = [decisions[fid] for fid in ids_by_ref[at]]
        flags = {key: entry.get("flagged") for key, entry in readings.items()}
        row = dict(at=at, **reference[at], critical_location=at in critical,
                   selected_ids=ids_by_ref[at], windows=w["correct"], native=n["correct"], routed=r["correct"],
                   printed_blank=expected == "", legitimate_spacing=" " in norm(expected),
                   flags=flags, missing={arm: item["observed"] is None for arm, item in readings.items()},
                   **outcome(readings, selected))
        row["observed_changed"] = w["observed"] != r["observed"]
        if row["observed_changed"] or row["opportunity"] or row["native_risk"]:
            row["witness"] = dict(expected=expected, **{arm: item["observed"] for arm, item in readings.items()})
        evidence.append(row)
    return evidence


def tally(rows):
    moves = ("right_to_right", "wrong_to_right", "right_to_wrong", "wrong_to_wrong")
    return dict(total=len(rows),
                correct={arm: sum(r[arm] for r in rows) for arm in ("windows", "native", "routed")},
                windows_to_routed={k: sum(r["transition"] == k for r in rows) for k in moves},
                windows_to_native={k: sum(r["native_transition"] == k for r in rows) for k in moves},
                coverage={k: sum(r["coverage"] == k for r in rows) for k in ("outside_trigger", "substituted", "unresolved")},
                opportunities=dict(Counter(r["opportunity"] for r in rows if r["opportunity"])),
                retrospective_oracle_correct=sum(r["windows"] or r["native"] for r in rows),
                native_risks=sum(r["native_risk"] for r in rows),
                native_risks_introduced=sum(r["native_risk"] and r["introduced"] for r in rows),
                changed_existing_errors=sum(r["transition"] == "wrong_to_wrong" and r["observed_changed"] for r in rows),
                changed_outside_trigger=[r["at"] for r in rows if r["observed_changed"] and not r["selected_ids"]],
                added_flags=[r["at"] for r in rows if r["flags"]["routed"] and not r["flags"]["windows"]])


def evaluate(truth, windows, manifest, binding, scores, label):
    fields = unique(manifest["fields"], "id")
    decisions = unique(binding["fields"], "id")
    require(fields.keys() == decisions.keys(), "missing binding decision")
    for fid, item in decisions.items():
        field = fields[fid]
        require(field["page"] == item["page"], "decision page")
        require(item["status"] in ("substituted", "unresolved"), "unknown decision")
        require(item["changed"] == (item["emitted_value"] != field["windows_value"]), "changed flag")
        if item["status"] == "unresolved":
            require(item["native_value"] is None and not item["changed"], "unresolved changed value")
    refs_by_id, ids_by_ref = field_links(truth, windows, fields)
    reference = references(truth, label)
    crit = field_rows(scores, "critical", reference, ids_by_ref, decisions)
    regions = field_rows(scores, "region", reference, ids_by_ref, decisions)
    by_ref = unique(regions, "at")
    crit_ref = unique(crit, "at")
    triggers = []
    for fid, item in fields.items():
        found = refs_by_id[fid]
        triggers.append(dict(id=fid, kind=item["kind"], page=item["page"], window_start=item["window_start"],
                             status=decisions[fid]["status"], reason=decisions[fid]["reason"],
                             changed=decisions[fid]["changed"], windows_label=item["label_text"],
                             scored_locations=found,
                             any_printed_label=any(reference[at]["printed_label_match"] for at in found),
                             any_critical=any(at in crit_ref for at in found),
                             any_critical_error=any(at in crit_ref and not crit_ref[at]["windows"] for at in found),
                             any_windows_region_error=any(not by_ref[at]["windows"] for at in found),
                             any_critical_opportunity=any(at in crit_ref and crit_ref[at]["opportunity"] for at in found)))
    protected = [r for r in regions if r["printed_blank"] or r["legitimate_spacing"]]
    groups = {
        "critical": crit,
        "critical_table": [r for r in crit if r["region"] != "prose"],
        "critical_prose": [r for r in crit if r["region"] == "prose"],
        "all_cells_and_full_lines": regions,
        "noncritical_locations": [r for r in regions if not r["critical_location"]],
        "full_lines_with_critical_value": [r for r in regions if r["critical_location"] and r["region"] == "prose"],
        "printed_blank_cells": [r for r in regions if r["printed_blank"] and r["region"] != "prose"],
        "legitimately_spaced_cells": [r for r in regions if r["legitimate_spacing"] and r["region"] != "prose"],
        "legitimately_spaced_lines": [r for r in regions if r["legitimate_spacing"] and r["region"] == "prose"],
        "legitimately_spaced_critical_values": [r for r in crit if r["legitimate_spacing"]],
        "printed_label_targets": [r for r in regions if r["printed_label_match"]],
        "unselected_critical": [r for r in crit if not r["selected_ids"]],
        "selected_critical": [r for r in crit if r["selected_ids"]],
    }
    for disposition in ("substituted", "unresolved"):
        groups[disposition + "_critical"] = [r for r in crit if r["coverage"] == disposition]
    counts = {name:tally(group) for name, group in groups.items()}
    require(len(crit) == scores["routed"]["counts"]["critical_values"], "critical reconciliation")
    require(all(counts["critical"]["correct"][key] == len(crit) - arm["counts"]["critical_errors"]
                for key, arm in scores.items()), "critical correctness reconciliation")
    summary = dict(
        metrics=counts, selected_fields=len(triggers),
        selection=dict(kind=dict(Counter(t["kind"] for t in triggers)),
                       status=dict(Counter(t["status"] for t in triggers)),
                       reasons=dict(Counter(t["reason"] for t in triggers)),
                       field_value_changed=sum(t["changed"] for t in triggers),
                       unmatched=sum(not t["scored_locations"] for t in triggers),
                       multiple_reference_locations=sum(len(t["scored_locations"]) > 1 for t in triggers),
                       multiple_triggers_per_location=sum(len(r["selected_ids"]) > 1 for r in regions),
                       no_reference_label=sum(not t["any_printed_label"] for t in triggers),
                       no_critical_error=sum(not t["any_critical_error"] for t in triggers),
                       no_critical_opportunity=sum(not t["any_critical_opportunity"] for t in triggers),
                       already_correct_regions=sum(bool(t["scored_locations"]) and not t["any_windows_region_error"] for t in triggers),
                       no_critical_value=sum(not t["any_critical"] for t in triggers)),
        printed_label_targets_missed=[r["at"] for r in regions if r["printed_label_match"] and not r["selected_ids"]],
        protected_damaged=[r["at"] for r in protected if r["introduced"]],
        protected_critical_value_damaged=[r["at"] for r in crit if r["legitimate_spacing"] and r["introduced"]])
    return summary, dict(critical=crit, regions=regions, triggers=triggers)
