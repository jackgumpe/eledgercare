"""Adversarial CPU scoring controls. This module fabricates predictions ONLY for tests."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from score import compare, norm, read, score

HERE = Path(__file__).resolve().parent


def perfect(t, direct=False):
    out = dict(source_sha256=t["source_sha256"], pages=[])
    for ref in t["pages"]:
        spans = [dict(text=line["text"], bbox=line["bbox"]) for line in ref["lines"]]
        tables = []
        for table in ref["tables"]:
            if direct:
                spans.extend(dict(text=cell["text"], bbox=cell["bbox"]) for row in table["rows"] for cell in row)
            else:
                tables.append(dict(bbox=table["bbox"], rows=[[cell["text"] for cell in row] for row in table["rows"]]))
        out["pages"].append(dict(page=ref["page"], source_sha256=t["source_sha256"], state="complete",
                                 text=ref["text"], spans=spans, tables=tables))
    return out


def controls():
    cases = {x:read(HERE/"dev"/x/"truth.json") for x in ("short","dense","boundary")}
    results = {}

    def verify(name, condition):
        if not condition:
            raise AssertionError(name)
        results[name] = "pass"

    for case, gt in cases.items():
        for direct in (False, True):
            out = score(gt, perfect(gt, direct))
            c = out["counts"]
            verify(f"perfect_{case}_{'spans' if direct else 'grid'}",
                   out["packet_complete"] and c["cer"] == 0 and c["critical_errors"] == 0 and
                   c["correct_lines"] == c["reference_lines"] and c["correct_cells"] == c["reference_cells"])
    short, dense, boundary = cases.values()
    control = score(dense, perfect(dense))
    d = perfect(dense)
    rows = d["pages"][0]["tables"][0]["rows"]
    rows[1][3], rows[2][3] = rows[2][3], rows[1][3]
    bad = score(dense,d)
    check = compare(control,bad)
    verify("swapped_rows_identical_page_text", bad["counts"]["cer"] == 0 and bad["counts"]["critical_errors"] == 2 and
           bad["counts"]["correct_cells"] == control["counts"]["correct_cells"]-2 and not check["inside_quality_budget"])
    verify("new_unflagged_locations", len(check["new_or_changed_critical_errors"]) == 2 and not check["unattended_quality_gate"])
    rows[1][3] = dict(text=rows[1][3], flagged=True)
    flagged = score(dense,d)
    verify("flag_does_not_fix_value", flagged["counts"]["unflagged_critical_errors"] == 1 and
           flagged["counts"]["critical_errors"] == 2 and flagged["counts"]["correct_cells"] == bad["counts"]["correct_cells"])
    d = perfect(dense)
    rows = d["pages"][0]["tables"][0]["rows"]
    rows.pop(3)
    c = score(dense,d)["counts"]
    verify("repeated_row_not_deduplicated", c["correct_cells"] < c["reference_cells"] and c["unflagged_critical_errors"] > 0)
    rows.append(["","","","","",""])
    rows[3].pop()
    detail = score(dense,d)["pages"][0]["cells"]
    verify("absent_empty_cell_not_explicit_blank", any(c["expected"] == "" and c["observed"] is None and not c["correct"] for c in detail))
    d = perfect(dense)
    rows = d["pages"][0]["tables"][0]["rows"]
    rows.append(list(rows[-1]))
    c = score(dense,d)["counts"]
    verify("extra_grid_cells_penalized", c["extra_cells"] == 6 and c["cell_accuracy"] < 1)
    d = perfect(dense)
    d["pages"][0]["tables"][0]["bbox"] = [1,5,310,40]
    c = score(dense,d)["counts"]
    verify("misplaced_table_cannot_collect_values", c["correct_cells"] == 0 and c["extra_cells"] == c["reference_cells"])
    d = perfect(dense,True)
    s = d["pages"][0]["spans"]
    first = next(i for i, v in enumerate(s) if v["text"] == "I0-701")
    second = next(i for i,v in enumerate(s) if v["text"] == "10-7O1")
    s[first]["bbox"], s[second]["bbox"] = s[second]["bbox"], s[first]["bbox"]
    verify("direct_cell_source_positions", score(dense,d)["counts"]["critical_errors"] == 2)
    d = perfect(short)
    d["pages"][0]["spans"][1]["text"] += " CL-1017"
    verify("ambiguous_critical_line", score(short,d)["counts"]["critical_errors"] == 1)
    d = perfect(short)
    d["pages"][0]["spans"][1]["page"] = 2
    b = score(short,d)
    verify("different_span_source", b["counts"]["wrong_source"] == 1 and b["counts"]["critical_errors"] == 1)
    d = perfect(dense)
    d["pages"][0]["tables"][0]["rows"][1][0] = dict(text="I0-701", page=2)
    b = score(dense,d)
    verify("different_cell_source", b["counts"]["wrong_source"] == 1 and b["counts"]["critical_errors"] == 1)
    d = perfect(boundary)
    d["pages"][0]["source_sha256"] = "0"*64
    bad = score(boundary,d)
    length = len(norm(boundary["pages"][0]["text"]))
    verify("foreign_page_insertions_and_deletions", not bad["packet_complete"] and
           bad["counts"]["wrong_source"] == 1 and bad["counts"]["edits"] == 2*length)
    d = perfect(boundary)
    d["pages"].reverse()
    b = score(boundary,d)
    verify("swapped_source_page_order", not b["packet_complete"] and b["counts"]["edits"] == 0)
    d = perfect(boundary)
    d["pages"].pop(2)
    b = score(boundary,d)
    verify("silently_omitted_blank_fails_completion", not b["packet_complete"] and b["counts"]["edits"] == 0)
    d = perfect(boundary)
    d["pages"][2]["text"] = "X"
    b = score(boundary,d)
    verify("blank_page_hallucination_adds_insertion", b["counts"]["edits"] == 1 and any(f["issue"]=="ink_on_blank" for f in b["faults"]))
    d = perfect(short)
    d["pages"][0]["text"] = ""
    b = score(short,d)
    verify("unexpected_empty_retains_full_denominator", not b["packet_complete"] and b["counts"]["cer"] == 1 and b["counts"]["cell_accuracy"] is None)
    d = perfect(short)
    d["pages"].append(deepcopy(d["pages"][0]))
    b = score(short,d)
    verify("duplicate_page_charged", not b["packet_complete"] and b["counts"]["cer"] == 1)
    d = perfect(short)
    d["pages"][0]["state"] = "truncated"
    verify("truncation_cannot_claim_complete", not score(short,d)["packet_complete"])
    d = perfect(short)
    d["pages"][0]["text"] = d["pages"][0]["text"].replace("0.81", "0.18")
    b = score(short,d)
    verify("edit_cost_source_chars", b["counts"]["edits"] == 2 and b["counts"]["reference_chars"] == len(norm(short["pages"][0]["text"])))
    ct = deepcopy(short)
    ct["pages"] = [dict(page=1,width=612,height=792,lines=[],tables=[],text="")]
    d = perfect(ct)
    d["pages"][0]["text"] = "x"
    b = score(ct,d)
    verify("empty_family_na_with_insertion", b["counts"]["cer"] is None and b["counts"]["edits"] == 1 and b["counts"]["cell_accuracy"] is None)
    return results


if __name__ == "__main__":
    print(json.dumps(controls(), indent=2))
