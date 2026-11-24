"""Compare both independent tables and validate schedule, custody and native archived score bytes."""
import argparse
import gzip
import json
import math
from pathlib import Path
import struct
import subprocess

DIRECTORY = Path(__file__).resolve().parent
BASE = "d9741d6e880d06192b9f3e56ab8056d391da1b9e"
CUSTODY = "d2ed1e76734f702ea41c242d8ec823519c5bf073"
ARMS = [(m, w, r) for m, writes in (("M1", ("W0", "W1", "W2a", "W2b")), ("M3", ("W0", "W1")))
        for w in writes for r in ("R0", "R1")]
ID = ["task", "pair", "horizon", "model", "write", "read"]
READ_ID = ID + ["phase", "step"]
TABLES = {
    "scores": (READ_ID + ["binder"], ["score_hex", "top", "gap", "score_pass", "gap_pass"]),
    "contrasts": (READ_ID, ["alpha", "beta", "delta", "mu", "gamma", "wins"]),
    "terminals": (ID + ["binder"], ["typed"]),
    "custody": (["pair"], ["horizon", "tier", "answerable", "members"]),
}


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", *args])


def check(ok, context):
    if not ok:
        raise ValueError(str(context))


def blob(rev, path):
    return git("cat-file", "blob", rev + ":" + path)


def js(rev, path):
    return json.loads(blob(rev, path))


def hashed_file(rev, prefix, table):
    files = git("ls-tree", "-r", "--name-only", rev, prefix).decode().splitlines()
    name = prefix + table + ".json"
    choices = [p for p in files if p in (name, name + ".gz")]
    check(len(choices) == 1, (table, choices))
    path = choices[0]
    data = blob(rev, path)
    return json.loads(gzip.decompress(data) if path.endswith(".gz") else data), {
        "revision": rev, "path": path, "blob": git("rev-parse", rev + ":" + path).decode().strip(),
    }


def index(rows, keys, fields):
    result = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        check(key not in result, ("duplicate", key))
        result[key] = {name: row[name] for name in fields}
    return result


def same(left, right):
    if type(left) is float or type(right) is float:
        return type(left) in (int, float) and type(right) in (int, float) and struct.pack("<d", left) == struct.pack("<d", right)
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(same(value, right[key]) for key, value in left.items())
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(x, y) for x, y in zip(left, right))
    return type(left) is type(right) and left == right


def load_both(author, review):
    tables = {}
    bindings = {}
    for name, (keys, fields) in TABLES.items():
        a, ab = hashed_file(author, "docs/research/WP-0035/evidence/", name)
        r, rb = hashed_file(review, "docs/reviews/WP-0035/evidence/", name)
        left, right = index(a, keys, fields), index(r, keys, fields)
        check(left.keys() == right.keys(), ("different row identities", name, sorted(set(left)^set(right))[:3]))
        for key, row in left.items():
            for field in fields:
                check(same(row[field], right[key][field]), ("different value", name, key, field, row[field], right[key][field]))
        tables[name] = left
        bindings[name] = {"author": ab, "review": rb, "exact_rows": len(left)}
    return tables, bindings


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def array(hex_string):
    values = struct.unpack("<ff", bytes.fromhex(hex_string))
    check(all(math.isfinite(s) for s in values), "Nonfinite owner score")
    return values


def structural(phase, step, archived):
    names = []
    if phase == "native_pre":
        return ["tpost"]
    if phase != "post":
        return []
    if step in (7, 8, 9, 11, 12):
        names.append(f"write_{step}")
    events = [e["kind"] for e in archived["Alder"]["events_applied"]]
    names.extend(e for e in events if e in ("OPEN_CHILD", "TENTATIVE_CLOSE", "CONFIRM_POP", "TARGET"))
    return names


def validate(tables, inputs, archive):
    checkpoints = {}
    expected_scores, expected_terminal = set(), set()
    native = js(BASE, "docs/research/WP-0027/owners/owner-rankings.json")["arms"]
    for task in ("A", "B"):
        for pair, group in inputs[task].items():
            horizon = group["horizon"]
            members = group["members"]
            if task == "B":
                observed = tables["custody"][pair,]
                hashes = inputs["cal_windows_receipt_metadata_pooled"]
                expected = {bid: [hashes[tag] for tag in m["windows"]] for bid, m in members.items()}
                check(observed == {"tier":1, "horizon":horizon, "members":expected, "answerable":group["answerable"]}, ("custody", pair))
            for model, write, read in [*ARMS, ("M2", "symbolic", "symbolic")]:
                id_tuple = (task, pair, horizon, model, write, read)
                expected_terminal.update(id_tuple + (bid,) for bid in members)
                if model == "M2" or (task == "B" and not group["answerable"]):
                    continue
                phases = [(phase, step) for mod, h, phase, step in archive if mod == model and h == horizon] if task == "A" else [("native_pre",-1)]
                for phase, step in phases:
                    key = id_tuple + (phase, step)
                    contrasts = tables["contrasts"][key]
                    margins = {}
                    for bid, m in members.items():
                        row = tables["scores"][key + (bid,)]
                        expected_scores.add(key + (bid,))
                        a, c = array(row["score_hex"])
                        gap = abs(a-c)
                        check(same(row["top"], max(a,c)) and same(row["gap"],gap)
                              and row["score_pass"] is (max(a,c) >= 1.) and row["gap_pass"] is (f32(gap) >= f32(.1)),
                              ("top score or threshold",key,bid,row))
                        owner = m["expected"]["owner"]
                        margins[owner] = a-c
                        if write == "W0" and read == "R0":
                            if task == "A":
                                reference = archive[model,horizon,phase,step][owner]["read"]["score_f32le"]
                            else:
                                attempt, = native[model]["by_binder"][bid]["attempts_by_ptr"].values()
                                raw = attempt["fields"]["owner"]["scores_by_key"]
                                reference = struct.pack("<ff",raw["alder"],raw["cedar"]).hex()
                            check(row["score_hex"] == reference, ("native score bits",key,bid))
                    a, c = margins["Alder"], margins["Cedar"]
                    delta, mu = a-c, (a+c)/2
                    values = dict(alpha=a,beta=c,delta=delta,mu=mu,gamma=delta-2*abs(mu),wins=int(a>0)+int(c<0))
                    for field in values:
                        check(same(values[field],contrasts[field]), ("pair arithmetic", key,field,values[field],contrasts[field]))
                    if task == "A":
                        historical = archive[model,horizon,phase,step]
                        if write == "W0" and read == "R0":
                            check(struct.pack("<d",delta).hex()==historical["delta_f64le"], ("native delta bits",key))
                        labels = structural(phase,step,historical)
                        if labels:
                            checkpoints[key] = {"labels":labels,**values,"members":{bid:tables["scores"][key+(bid,)] for bid in members}}
    check(set(tables["scores"]) == expected_scores, "Score coverage")
    check(set(tables["contrasts"]) == {k[:-1] for k in expected_scores}, "Contrast coverage")
    check(set(tables["terminals"]) == expected_terminal and len(tables["custody"])==10, "Terminal or custody coverage")
    return checkpoints

def normalize(value):
    from html import unescape
    return " ".join(unescape(value).split()).casefold() if isinstance(value, str) else value


def tally(tables, inputs, archive):
    historical = js(BASE, "docs/research/WP-0027/owners/owner-rankings.json")["arms"]
    results = []
    pair_rows = []
    for task in ("A", "B"):
        for model, w, read in [*ARMS, ("M2", "symbolic", "symbolic")]:
            for subset in ("all", 12, 30):
                n = {"answerable_pairs":0, "safety_pairs":0, "answerable_binders":0, "safety_binders":0,
                     "typed_correct_postings":0, "typed_wrong_postings":0, "typed_abstentions":0,
                     "safety_correct_abstentions":0, "safety_wrong_postings":0, "typed_reasons":{}}
                if model != "M2":
                    n.update(simultaneous_wins=0,member_rank_correct=0,owner_cutoff_correct=0,owner_cutoff_wrong=0,
                             below_score_only=0,below_gap_only=0,below_both=0)
                for pair, group in inputs[task].items():
                    horizon = group["horizon"]
                    if subset not in ("all", horizon):
                        continue
                    answerable = task == "A" or group["answerable"]
                    n["answerable_pairs" if answerable else "safety_pairs"] += 1
                    key = (task, pair, horizon, model, w, read)
                    if model != "M2" and answerable:
                        point = next(step for mod,h,phase,step in archive if mod==model and h==horizon and phase=="native_pre") if task=="A" else -1
                        c = tables["contrasts"][key+("native_pre",point)]
                        n["simultaneous_wins"] += c["wins"] == 2
                        n["member_rank_correct"] += c["wins"]
                        if subset == "all":
                            pair_rows.append(dict(zip(ID,key),**c))
                    for bid, member in group["members"].items():
                        n["answerable_binders" if answerable else "safety_binders"] += 1
                        typed = tables["terminals"][key+(bid,)]["typed"]
                        if w=="W0" and read=="R0":
                            if task=="B":
                                original = historical[model]["by_binder"][bid]["selected_binder_decision"]
                            else:
                                p=next(row for (mod,h,phase,_),row in archive.items() if mod==model and h==horizon and phase=="native_pre")
                                original = p[member["owner"]]["native"]["typed"]
                            check(typed == original, ("native complete posting",key,bid,typed,original))
                        check(typed["type"] in ("ABSTAIN","Posting"), ("typed",key,bid))
                        if typed["type"] == "ABSTAIN":
                            n["typed_abstentions"] += 1
                            n["safety_correct_abstentions"] += not answerable
                            reason = typed["reason"]
                            n["typed_reasons"][reason] = n["typed_reasons"].get(reason,0)+1
                        else:
                            correct = answerable and all(normalize(typed.get(f))==normalize(v) for f,v in member["expected"].items())
                            n["typed_correct_postings" if correct else "typed_wrong_postings"] += 1
                            n["safety_wrong_postings"] += not answerable
                        if model != "M2" and answerable:
                            row = tables["scores"][key+("native_pre",point,bid)]
                            a,b = array(row["score_hex"])
                            if row["score_pass"] and row["gap_pass"]:
                                correct = a>b if member["expected"]["owner"]=="Alder" else b>a
                                n["owner_cutoff_correct" if correct else "owner_cutoff_wrong"] += 1
                            else:
                                bucket = ("below_score_only" if row["gap_pass"] else "below_gap_only" if row["score_pass"] else "below_both")
                                n[bucket] += 1
                if model=="M2":
                    for field in ("simultaneous_wins","member_rank_correct","owner_cutoff_correct","owner_cutoff_wrong",
                                  "below_score_only","below_gap_only","below_both"):
                        n[field]=None
                else:
                    check(sum(n[k] for k in ("owner_cutoff_correct","owner_cutoff_wrong","below_score_only","below_gap_only","below_both"))
                          ==n["answerable_binders"], "Owner-only counts")
                check(sum(n[k] for k in ("typed_correct_postings","typed_wrong_postings","typed_abstentions"))
                      ==n["answerable_binders"]+n["safety_binders"],"Typed counts")
                results.append({"task":task,"horizon":subset,"model":model,"write":w,"read":read,**n})
    return results, pair_rows


def main(author, review, output):
    inputs = js(CUSTODY, "docs/coordination/WP-0035/input-custody.json")
    source = [json.loads(s) for s in blob(BASE, "docs/reviews/WP-0030/evidence/steps.jsonl").splitlines()]
    archive = {(d["run"][:2],int(d["run"][3:]),d["phase"],d["step"]):d for d in source}
    check(len(archive)==len(source)==224,"Archive index")
    tables, bindings = load_both(author, review)
    checkpoints = validate(tables, inputs, archive)
    totals, pair_rows = tally(tables, inputs, archive)
    data = {"base":BASE, "input_custody":CUSTODY,"verified_evidence":bindings,
            "native_archive":{"paired_records":224,"per_member_ordered_score_bytes":448,"terminal_phase":"native_pre",
                              "write_after_read":{"12":36,"30":72},"reads_after_writes":{"12":35,"30":71}},
            "exact_native_calibration":{"answerable_pairs":8,"scored_members_per_model":16,"full_decisions_per_model":20},
            "metrics":totals,"terminal_pair_contrasts":pair_rows,
            "checkpoints":[dict(zip(READ_ID,key),**v) for key,v in checkpoints.items()]}
    with output.open("x",encoding="utf8",newline="\n") as out:
        json.dump(data,out,allow_nan=False,separators=(",",":"))
        out.write("\n")
    print("Exact independent rows", {k:v["exact_rows"] for k,v in bindings.items()}, "checkpoint rows",len(checkpoints))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("author_evidence")
    cli.add_argument("review_evidence")
    cli.add_argument("output",type=Path)
    args=cli.parse_args()
    main(args.author_evidence,args.review_evidence,args.output)
