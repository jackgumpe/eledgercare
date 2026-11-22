"""Recompute paired owner diagnostics from the published candidate-score bytes."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
NAMES = ("Alder", "Cedar")
TIMES = ("t1", "t2", "t3")
KEY = "33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5"
GATE = "docs/reviews/WP-0029/capture-gate.json"
RESULT = "docs/research/WP-0029/scoring/evidence/result.json"


def read(rev, name):
    data = subprocess.check_output(["git","-C",ROOT,"cat-file","blob",rev+":"+name])
    return json.loads(data), hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def reconcile(score_revision, gate_revision):
    result, result_sha = read(score_revision, RESULT)
    gate, gate_sha = read(gate_revision, GATE)
    require(result["gate"]["revision"] == gate_revision and result["gate"]["sha256"] == gate_sha
            and result["gate"]["authenticated"] == gate["authenticated"] and
            result["cedar_rgb_key"] == gate["rgb_key"] == KEY, "Scorer or capture gate identity")
    inventory = result["capture_inventory"]
    trajectories = []
    typed = []
    for arm in ("M1","M3"):
        for pair in result["arms"][arm]:
            by_owner = {m["owner"]:m for m in pair["members"]}
            require(set(by_owner) == set(NAMES) and pair["counts"]["planned"] == 1, "Pair identity")
            taken = pair["counts"]["completed"]
            require(pair["counts"]["admitted"] == taken and taken in (0,1), "Unexpected counts")
            require(by_owner["Cedar"]["rgb_keys_by_window"][0] == KEY, "Cedar window reuse")
            initial = None
            for t in TIMES:
                rows = {name:by_owner[name]["checkpoints"][t] for name in NAMES}
                scores = {name:rows[name]["scores"] for name in NAMES}
                record = {"arm":arm,"horizon":pair["horizon"],"time":t,"raw":scores}
                expected = pair["metrics"][t]
                if not taken:
                    require(all(v is None for member in scores.values() for v in member.values())
                            and expected["delta"] is None,"Unadmitted score")
                    trajectories.append(dict(record,reason=pair["reason"]))
                    continue
                require(gate["authenticated"] and gate["eligible_owner_cue"] and len(inventory) == 11,
                        "Score without signed archive and cue")
                margins = {}
                ranks = {}
                for owner in NAMES:
                    s = scores[owner]
                    raw = struct.pack("<ff",s["Alder"],s["Cedar"])
                    require(hashlib.sha256(raw).hexdigest() == rows[owner]["score_bytes_f32le_sha256"],"Raw score bytes")
                    margins[owner] = s["Alder"] - s["Cedar"]
                    ranks[owner] = "tie" if margins[owner] == 0 else max(NAMES, key=s.__getitem__)
                    require(rows[owner]["candidate_order"] == list(NAMES) and
                            rows[owner]["query_sha256"] == by_owner[owner]["checkpoints"]["t3"]["query_sha256"],
                            "Candidate list or fixed final query")
                    if t == "t3":
                        parity = by_owner[owner]["parity"]
                        require(len(set(parity["final_state"].values())) == 1 and
                                parity["first_checkpoints"] == parity["repeat_checkpoints"], "Duplicate parity")
                        typed.append({"arm":arm,"horizon":pair["horizon"],"owner":owner,
                                      "ranked_first":ranks[owner],"typed":rows[owner]["typed"]})
                a,c = (margins[name] for name in NAMES)
                mu,delta = (a+c)/2, a-c
                if t == "t1":
                    initial = delta
                ratio = delta/initial if abs(initial) > 1e-6 else None
                win = a > 0 and c < 0
                require(expected == {"margin_Alder_input":a, "margin_Cedar_input":c,"mu":mu,"delta":delta,
                        "D":delta-initial,"ratio":ratio,"positive_response":delta>0,"correct_paired_win":win,
                        "delta_gt_twice_abs_mu":delta>2*abs(mu)} and win == (delta>2*abs(mu)), "Paired arithmetic")
                require(rows["Alder"]["query_sha256"] == rows["Cedar"]["query_sha256"], "Within-pair query")
                record.update(margins=margins, mu=mu, delta=delta, D=delta-initial, ratio=ratio,
                              ranked_first=ranks, strict_paired_win=win)
                trajectories.append(record)
    early = []
    for arm,pairs in result["arms"].items():
        for owner in NAMES:
            for t in ("t1","t2"):
                records = [next(m for m in p["members"] if m["owner"] == owner)["checkpoints"][t] for p in pairs]
                claims = result["cross_horizon"][arm][owner][t]
                if claims["shared"] is None:
                    continue
                scores_hex = [struct.pack("<ff",*(cp["scores"][n] for n in NAMES)).hex() for cp in records]
                queries = [cp["query_sha256"] for cp in records]
                require(scores_hex == [claims["score_f32le_hex_by_horizon"][str(h)] for h in (12,30)]
                        and (scores_hex[0] == scores_hex[1] and queries[0] == queries[1]) == claims["shared"],
                        "Cross-horizon comparability")
                early.append({"arm":arm,"owner":owner,"time":t,"shared":claims["shared"]})
    return {"score_revision":score_revision,"score_sha256":result_sha,"gate_revision":gate_revision,
            "gate_sha256":gate_sha,"counts":result["arm_pair_counts"],"unique_triples_read":len(inventory),
            "opening_uses":[{"owner":"Cedar","horizon":h,"window":1,"rgb_key":KEY} for h in (12,30)],
            "paired_checkpoints":trajectories,"typed_decisions":typed,"early_cross_horizon_checks":early}


if __name__ == "__main__":
    result = reconcile(sys.argv[1],sys.argv[2])
    with Path(sys.argv[3]).open("x",encoding="utf8",newline="\n") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
