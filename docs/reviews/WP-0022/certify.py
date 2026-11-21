"""Reconcile independent reader state, physical ownership and literal transcription with published artifacts."""
from argparse import ArgumentParser
from collections import Counter
import json
from pathlib import Path
import subprocess

from replay import load, save


def git_json(commit, path):
    return json.loads(subprocess.check_output(["git","show",f"{commit}:{path}"]))


def main(out, coordinator, dest):
    root = "docs/coordination/WP-0022/"
    official = git_json(coordinator, root + "scores.json")
    categories = {"value_owned":"owned","value_flagged":"unambiguous-abstention","other_word_flagged":"incidental-flag",
                  "ambiguous_flagged":"ambiguous-abstention","blank_safely_withheld":"safe-withholding"}
    data = {"official_revision":coordinator,"arms":{}}
    for arm in ("R","W"):
        c = Counter()
        for history in sorted(out.glob(f"history-{arm}-*.json")):
            doc = history.stem.split("-")[-1]
            detailed = git_json(coordinator,root + "witnesses/" + doc + ".json")
            canonical = detailed[arm]
            seen_typed = set()
            for entry in load(history):
                loc = f"{entry['page']}/{entry['line']}"
                other = canonical["lines"][loc]
                assert entry["words"] == other["words"]
                if arm == "W":
                    assert entry["native_line_text"] == other["text"]
                for phase in ("before","after"):
                    normalized = [dict(scope=f["scope"],headingRefs=f["heading_refs"],headerRefs=f["header_refs"],
                                       x0Anchors=f["anchors"],rules=f["rules"],headerPage=f["header_page"],
                                       headedGrid=f["headed_grid"]) for f in entry[phase]]
                    expect = canonical["states"][other[phase]]["frames"]
                    assert normalized == expect, (arm,doc,loc,phase)
                    seen_typed.update(f["scope"] for f in normalized if f["headerRefs"] and f["headingRefs"] and f["x0Anchors"])
                c["all_line_entries"] += 1
            for scope in sorted(seen_typed):
                c["docs_with_typed_" + scope] += 1
            for case in sorted(out.glob(doc + "-T*.json")):
                review = load(case)
                target, observed = review["target"], review[arm]
                truth = detailed["targets"][case.stem]
                s = official["rows"][target["id"]][arm]
                assert observed["status"] == categories[s["outcome"]] and observed["pass"] == s["passed"]
                assert observed["false_posts"] == s["silentWrongPosts"] and observed["amount_intersections"] == s["intersectionRefs"]
                assert observed["amount_words"] == s["centeredRefs"]
                assert len(observed["events"]) == len(s["events"])
                for our, their in zip(observed["events"],s["events"]):
                    assert (our["ref"],our["source"],our["flag"],our["cross_row"],our["reason"]) == (
                        their["ref"],their["origin"],their["flagged"],their["crossesKeyedRows"],their["reason"])
                    for ours, theirs in (("property_region","property"),("unit_region","unit"),("heading","sectionHeading")):
                        assert our["binding"][ours] == their["context"][theirs]
                    c["compared_target_events"] += 1
                if target["kind"] != "blank":
                    assert len(observed["amount_words"]) == 1
                    ref = observed["amount_words"][0]
                    words = [w for line in observed["trace"] for w in line["words"] if w["ref"] == ref]
                    assert len(words) == 1 and words[0]["text"] == target["literal"]
                    c["exact_physical_literal_" + target["kind"]] += 1
                for ours, theirs in zip(observed["trace"],truth[arm]["lineDecisions"],strict=True):
                    assert [target["page"],ours["line"]] == [int(n) for n in theirs["line"].split("/")]
                    for a,b in zip(ours["header_deltas_pt"],theirs["savedHeaderDeltas"],strict=True):
                        x = a["candidate_minus_amount_header_x0"]
                        assert (round(x,6) if x is not None else None) == b["dx0"]
                    assert [round(x["candidate_minus_observed_header_x0"],6) for x in ours["physical_header_deltas_pt"]] == theirs["dx0ToPhysicalAmountHeader"]
                c["all_targets"] += 1
        data["arms"][arm] = dict(c)
    save(dest,data)
    print(json.dumps(data,indent=2))


if __name__ == "__main__":
    cli = ArgumentParser(description=__doc__)
    cli.add_argument("out",type=Path)
    cli.add_argument("coordinator")
    cli.add_argument("dest",type=Path)
    args = cli.parse_args()
    main(args.out,args.coordinator,args.dest)

