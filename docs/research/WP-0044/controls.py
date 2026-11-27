"""Read-only checks of the admitted archive and finite arithmetic examples."""
import hashlib
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parents[1] / "coordination/WP-0043/native-evidence.json"


def archive_rows():
    data = ARCHIVE.read_bytes()
    if hashlib.sha256(data).hexdigest() != "66eb8bd4a1d51b813f7de7a846ce841238614017cb9c5970ebd82595a42218bb":
        raise ValueError("pinned archive bytes changed")
    archive = json.loads(data)
    rows = archive["retained_rows"]
    gaps = [r["final_top_two"]["value"] - r["final_top_two"]["runner_up_value"] for r in rows]
    support = []
    for row in rows:
        width, slack = divmod(row["copies"][2]["copy_bytes"], 4)
        changes = row["c2_differs_from_c1_at_token_ids"]
        negative_inf = struct.unpack("<f", bytes.fromhex(row["post_page_eos_fp32le"]))[0] == -float("inf")
        if slack or not (row["c0_all_finite"] and row["c0_identical_c1"] and changes == [1] and negative_inf):
            raise ValueError("archive support premise")
        support.append({"vocabulary": width, "excluded": changes, "allowed": width-len(changes)})
    prior = archive["offline_scorer"]["verdict"]
    conflicts = [c for c in prior["conflicts"] if c["field"] == "argv" and
                 c["expected"][0] != c["observed"][0] and c["expected"][1:] == c["observed"][1:]]
    missing = {m["row"] for m in prior["missing"] if m["key"] == "native_custody_unqualified"}
    qualified = sum(row["row"] not in missing and row["verdict"] == "P" for row in prior["rows"])
    outcome = {"joint": "M" if conflicts else prior["verdict"], "argv0_conflicts": len(conflicts),
               "qualified_pairs": 0 if conflicts else prior["public_pairs_matched"],
               "scheduled_pairs": prior["scheduled_pairs"], "qualified_rows": qualified,
               "scheduled_rows": len(prior["rows"]), "row_verdicts": [r["verdict"] for r in prior["rows"]],
               "target_document_equal": archive["public_content"]["F07.warm1"]["same_all_public_fields"]}
    return {"archive.gaps": gaps, "archive.support": support, "archive.verdict": outcome}


def winner(scores):
    return max(range(len(scores)), key=scores.__getitem__)


def math_rows():
    before = [28., 17.125]
    after = [x + 10 for x in before]
    delta = [b-a for a, b in zip(before, after)]
    gap = before[0] - before[1]
    tie_high = [before[0], before[1] + gap]
    tie_low = list(reversed(tie_high))
    stock_q, linked_q = 0, 2
    def logits(q):
        return [1-q, q]
    return {
        "math.shift": {"linf": max(map(abs, delta)), "oscillation": max(delta)-min(delta),
                       "old": winner(before), "new": winner(after), "gap": gap},
        "math.tie": {"unique": tie_high.count(max(tie_high)) == 1,
                     "higher_id_competitor": {"before": winner(before), "after": winner(tie_high)},
                     "lower_id_competitor": {"before": winner(before[::-1]), "after": winner(tie_low)},
                     "gap": gap},
        "math.signed_zero": {"equal": 0.0 == -0.0, "positive": struct.pack("<f", 0.).hex(),
                             "negative": struct.pack("<f", -0.).hex()},
        "math.linked": {"first": winner(logits(0)), "reset": winner(logits(stock_q)),
                        "linked": winner(logits(linked_q)), "reset_scores": logits(stock_q),
                        "linked_scores": logits(linked_q)}
    }
