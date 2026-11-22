"""Reconcile span-by-span scores with the independent record and extract the two released findings."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUTHOR = "6c9ecae26aff3b2faa47d90d2f16bcee12b8a191"
REVIEW = "7d65875a1ff2d7ad8a008ea83f5484507dbd5db3"
PROBE = "docs/research/WP-0030/trace/evidence/"
NAMES = ("Alder", "Cedar")
PHASE = {"zero":"initial", "post_write":"post", "native_pre_target":"native_pre"}


def blob(ref, path):
    return subprocess.check_output(["git","-C",ROOT,"cat-file","blob",ref+":"+path])


def require(ok, message):
    if not ok:
        raise ValueError(message)


def point(row):
    src = row["members"]["Alder"]["source"]
    return {"step":row["step_index"],"phase":row["phase"],"source_pointer":src["pointer"] if src else None,
            "absolute_page":src["absolute_page"] if src else None,"kind":src["kind"] if src else None,
            "block_kind":src["block_kind"] if src else None,"events":[e["kind"] for e in src["events"]] if src else [],
            "excerpts":{n:row["members"][n]["source"]["literal"] for n in NAMES} if src else None,
            "owner_candidates_eligible":row["both_owner_eligible"],"delta":row["delta"],
            "winners":{n:row["members"][n]["top_owner"] for n in NAMES},"paired_win":row["paired_win"]}


def change(before,after):
    return {"from":point(before),"to":point(after)}


def audit():
    reviews = defaultdict(list)
    for line in blob(REVIEW,"docs/reviews/WP-0030/evidence/steps.jsonl").splitlines():
        row = json.loads(line)
        reviews[row["run"]].append(row)
    published = json.loads(blob(AUTHOR,PROBE+"findings.json"))
    packages = {}
    for arm in ("M1","M3"):
        for horizon in (12,30):
            name = f"{arm}-{horizon}"
            data = blob(AUTHOR,PROBE+name+".json")
            rows = json.loads(data)
            peer = reviews[f"{arm}/{horizon}"]
            for row,ref in zip(rows,peer,strict=True):
                require(PHASE[row["phase"]] == ref["phase"] and row["step_index"] == ref["step"]
                        and row["checkpoints"] == ref["boundaries"],"Misaligned phase")
                margins = []
                for who in NAMES:
                    member = row["members"][who]
                    observation = ref[who]["read"]
                    raw = struct.pack("<ff",*(member["scores"][n] for n in NAMES))
                    require(raw.hex() == member["scores_f32le_hex"] == observation["score_f32le"],"Score bytes")
                    for key in ("query_sha256","read_sha256","matrix_sha256","owner_eligible"):
                        require(member[key] == observation[key],key)
                    require(member["controller"]["depth"] == observation["controller"]["depth"],"Depth disagreement")
                    actual = member["source"]
                    independent = ref[who]["source"]
                    if actual:
                        require(actual["pointer"] == independent["ptr"] and actual["literal"] == independent["text"]
                                and actual["feature_sha256"] == independent["feature_f32le_sha256"],"Span identity")
                    else:
                        require(independent is None,"Initial state has a source")
                    a,c = struct.unpack("<ff",raw)
                    margins.append(a-c)
                    rank = "Alder" if a>c else "Cedar" if c>a else None
                    require(rank == member["top_owner"],"Wrong ranking")
                delta = margins[0]-margins[1]
                require(struct.pack("<d",delta).hex() == ref["delta_f64le"] == row["delta_f64le_hex"],"Signed response")
                require((margins[0] > 0 > margins[1]) == row["paired_win"] == ref["paired_win"],"Same-step win")
            writes = [r for r in rows if r["phase"]=="post_write"]
            require([r["step_index"] for r in writes]==list(range(1,len(writes)+1)), "Discontinuous trace")
            owner, = [r for r in rows if "t1" in r["checkpoints"]]
            opening, = [r for r in rows if "t2" in r["checkpoints"]]
            target, = [r for r in rows if "t3" in r["checkpoints"]]
            transitions = list(zip(rows,rows[1:]))
            first = next((l,r) for l,r in transitions if r["phase"]=="post_write" and r["delta"]>0)
            later = next((l,r) for l,r in transitions if r["phase"]=="post_write" and r["delta"]>0
                         and r["step_index"]>owner["step_index"])
            rev = [change(l,r) for l,r in transitions if l["delta"]*r["delta"] < 0]
            attenuation = [r for l,r in transitions if abs(r["delta"]) < abs(l["delta"])]
            positive_drop = [r for l,r in transitions if l["delta"]>0 and r["delta"]<l["delta"]]
            late = [(l,r) for l,r in transitions if r["step_index"]>opening["step_index"] and
                    r["phase"]=="post_write" and r["step_index"]<=target["step_index"]]
            greatest = max(late, key=lambda pair:pair[0]["delta"]-pair[1]["delta"])
            early = [r for r in writes if r["step_index"]<=opening["step_index"]]
            literal_changes = [r["step_index"] for r in early if "literal" in r["alignment"]["different_fields"]]
            feature_changes = [r["step_index"] for r in early if "feature_sha256" in r["alignment"]["different_fields"]]
            wins = [point(r) for r in rows if r["paired_win"]]
            report = published[name]
            require(len(rev)==len(report["sign_reversals"]) and len(attenuation)==len(report["absolute_attenuation"])
                    and len(positive_drop)==len(report["positive_response_decreases"]) and len(wins)==len(report["paired_wins"]),
                    "Finding counts disagree")
            packages[name] = {"raw_trace_sha256":hashlib.sha256(data).hexdigest(),"writes":len(writes),"paired_reads":len(rows),
               "first_favorable":change(*first),"first_both_eligible":point(next(r for r in rows if r["both_owner_eligible"])),
               "owner_write":point(owner),"first_favorable_after_owner":change(*later),"strict_sign_reversals":rev,
               "steps_at_zero":[r["step_index"] for r in rows if r["delta"]==0],"absolute_attenuations":len(attenuation),
               "decreases_from_positive":len(positive_drop),"opening_end":point(opening),
               "largest_post_opening_decrease_through_posting":change(*greatest),"native_posting":point(target),
               "post_target_write":point(rows[-1]),"final_typed":{n:target["members"][n]["native"]["typed"] for n in NAMES},
               "paired_wins":wins,"opening_literal_changed_steps":literal_changes,"opening_feature_changed_steps":feature_changes}
    return {"packet":"WP-0030","author":AUTHOR,"independent":REVIEW,
            "total_paired_reads":sum(p["paired_reads"] for p in packages.values()),
            "total_paired_post_writes":sum(p["writes"] for p in packages.values()),
            "strict_paired_wins":sum(len(p["paired_wins"]) for p in packages.values()),
            "paired_read_semantics":"Four zero-state reads, one observation per aligned span write and four native pre-posting observations. Identical phases reused across document lengths are separate traversal checks.",
            "per_arm_horizon":packages}


if __name__ == "__main__":
    result = audit()
    with Path(sys.argv[1]).open("x",encoding="utf8",newline="\n") as out:
        json.dump(result,out,indent=2,allow_nan=False)
        out.write("\n")
    print(result["total_paired_reads"],result["strict_paired_wins"])
