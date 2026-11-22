"""Transcribe the independently published replay to the author's evidence schema and compare bytes."""
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inputs import FIT, FIX, HISTORY, NAMES, NEW, OLD, ROOT, blob, encoded, sha, write

AUTHOR = "6c9ecae26aff3b2faa47d90d2f16bcee12b8a191"
REVIEW = "7d65875a1ff2d7ad8a008ea83f5484507dbd5db3"
ADIR = "docs/research/WP-0030/trace/evidence/"
RDIR = "docs/reviews/WP-0030/evidence/"
OUT = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0030/review")
PHASE = {"initial":"zero", "native_pre":"native_pre_target", "post":"post_write"}
DIFFS = ("rgb_key","literal","cells","events","metadata_sha256","feature_sha256","raw_span_sha256",
         "selected_token_ids_u32le_sha256")


def pretty(obj):
    return json.dumps(obj,indent=2,sort_keys=True,allow_nan=False).encode() + b"\n"


def f32(value):
    return struct.unpack("<f",struct.pack("<f",value))[0]


def catalog_for_comparison(inventory):
    out = {}
    with ZipFile(io.BytesIO(blob(*OLD))) as old, ZipFile(io.BytesIO(blob(*NEW))) as new:
        for key, dataset in inventory.items():
            rev, path, _ = dataset["source"]
            z = {OLD[0]:old, NEW[0]:new}[rev]
            native = json.loads(z.read(dataset["prefix"] + "metadata.json"))["raw"].encode("utf-8")
            records = []
            for index, item in enumerate(dataset["spans"]):
                rec = item["raw_record"]
                lo, hi = rec["byte_range"]
                assert sha(native[lo:hi]) == item["raw_slice_sha256"]
                ids = item["token_ids"]
                records.append({"metadata":rec, "metadata_sha256":item["metadata_sha256"],
                                "literal_sha256":item["text_sha256"], "raw_span":native[lo:hi].decode("utf-8"),
                                "raw_span_sha256":item["raw_slice_sha256"], "feature_offset_bytes":5120*index,
                                "feature_sha256":item["feature_f32le_sha256"],
                                "selected_token_ids_u32le_sha256":sha(struct.pack(f"<{len(ids)}I",*ids))})
            out[key] = {"members_sha256":dataset["members"], "source":rev+":"+path, "prefix":dataset["prefix"],
                        "pages":dataset["pages"], "spans":records}
    return out


def convert_member(row, sources):
    obs = row["read"]
    src = row["source"]
    where, controls = None, []
    if src:
        ptr = src["ptr"]
        record = sources[src["key"]]["spans"][ptr[2]]
        where = {"pointer":ptr,"window_index":ptr[0],"absolute_page":src["page"],"kind":src["kind"],
                 "block_kind":src["block"],"literal":src["text"],"cells":src["cells"],"events":src["events"],
                 "rgb_key":src["key"], "feature_sha256":src["feature_f32le_sha256"],"literal_sha256":src["text_sha256"],
                 "raw_span_sha256":src["raw_slice_sha256"],"metadata_sha256":src["metadata_sha256"],
                 "selected_token_ids_u32le_sha256":record["selected_token_ids_u32le_sha256"]}
        for e,c in zip(src["events"],row["events_applied"],strict=True):
            assert e["kind"] == c["kind"]
            controls.append({"event":e["kind"],"literal":e["literal"],"ptr":ptr,"depth_after":c["after_depth"],
                             "pop_rank":c["pop_rank"],"shadow_hold":c["held_here"]})
    top = None if obs["top"] == "tie" else obs["top"]
    scores = obs["scores"]
    out = {k:obs[k] for k in ("controller","registry","owner_eligible","query_sha256","matrix_sha256","read_sha256",
                              "owner_columns_sha256","zero_read","margin")}
    out.update(phase=PHASE[row["phase"]], step_index=row["step"], source=where, control_events=controls,
               checkpoints=row["boundaries"], scope_clear=obs["native_scope_clear"],
               scores=dict(zip(NAMES,scores,strict=True)), scores_f32le_hex=obs["score_f32le"],
               margin_f64le_hex=obs["margin_f64le"], top_owner=top, exact_top_tie=top is None,
               rank={n:1+int(top is not None and n != top) for n in NAMES},
               top_score_pass=max(scores)>=1.,top_gap_pass=f32(abs(obs["margin"]))>=f32(.1))
    if row["phase"] == "native_pre":
        att = row["native"].copy()
        att["logit_sha256"] = {f:sha(bytes.fromhex(v)) for f,v in att.pop("score_bytes").items()}
        out["native"] = att
    return out


def pair_row(index, row, sources):
    members = {n:convert_member(row[n],sources) for n in NAMES}
    a,c = (members[n]["source"] for n in NAMES)
    align = None
    if a:
        align = {"pointer":a["pointer"],"ordered_roles":[e["kind"] for e in a["events"]],
                 "different_fields":[k for k in DIFFS if a[k]!=c[k]]}
    d = row["delta"]
    return {"members":members,"observation_index":index, "step_index":row["step"],"phase":PHASE[row["phase"]],
            "checkpoints":row["boundaries"],"delta":d,"delta_f64le_hex":row["delta_f64le"],
            "sign":int(d>0)-int(d<0),"both_owner_eligible":all(m["owner_eligible"] for m in members.values()),
            "paired_win":row["paired_win"], "alignment":align}


def point(row):
    a = row["members"]["Alder"]["source"]
    p = {k:row[k] for k in ("observation_index","phase","step_index","delta","delta_f64le_hex","paired_win")}
    p.update({k:a[k] if a else None for k in ("pointer","absolute_page","kind","block_kind")})
    p["ordered_roles"] = [e["kind"] for e in a["events"]] if a else []
    p["literals"] = {n:row["members"][n]["source"]["literal"] for n in NAMES} if a else None
    return p


def check_findings(series, proof):
    def transition(i):
        return {"previous": point(series[i-1]), "current": point(series[i])}
    def changes(rows):
        for event in rows:
            i = event["index"]
            p = transition(i)
            assert p["previous"]["delta"] == event["previous"] and p["current"]["delta"] == event["current"]
            yield p
    owner = proof["owner"]["index"]
    wins = [series[w["index"]] for w in proof["wins"]]
    writes = [row for row in series if row["phase"]=="post_write"]
    return {"first_favorable_from_zero":transition(proof["first_positive"]["index"]),
            "first_favorable_after_owner_write":transition(proof["first_positive_after_owner"]["index"]),
            "owner_write":point(series[owner]),"native_posting":point(series[-2]),"post_target_write":point(series[-1]),
            "writes":proof["writes"],"observations":proof["observations"],
            "zero_response":[point(r) for r in series if r["sign"]==0],
            "before_owner_write":[point(r) for r in writes if r["observation_index"]<owner],
            "paired_wins":[point(r) for r in wins],"eligible_paired_wins":[point(r) for r in wins if r["both_owner_eligible"]],
            "source_difference_steps":{k:[r["step_index"] for r in writes if k in r["alignment"]["different_fields"]] for k in DIFFS},
            "sign_transitions":list(changes(proof["sign_changes"])),
            "sign_reversals":list(changes(t for t in proof["sign_changes"] if t["strict_crossing"])),
            "absolute_attenuation":list(changes(proof["absolute_reductions"])),
            "positive_response_decreases":list(changes(proof["decreases_from_positive"]))}


def parity(series, bind, history, fit, pair, arm):
    out = {}
    for n in NAMES:
        b = bind[n]
        source, = (m for m in pair["members"] if m["owner"] == n)
        old, = (m for m in history["members"] if m["owner"] == n)
        checkpoints = {}
        for trace in series:
            m = trace["members"][n]
            for cp in trace["checkpoints"]:
                expected = old["checkpoints"][cp]
                ref_scores = struct.pack("<ff",*(expected["scores"][k] for k in NAMES)).hex()
                assert ref_scores == m["scores_f32le_hex"]
                entry = {k:m[k] for k in ("step_index","phase","scores_f32le_hex","margin_f64le_hex","query_sha256")}
                entry.update(pointer=m["source"]["pointer"], original_scores_f32le_hex=ref_scores)
                if cp == "t3":
                    entry["native"] = m["native"]
                checkpoints[cp] = entry
        s = series[-2]["members"][n]["source"]
        target = {"ptr":s["pointer"],"literal":s["literal"],"cells":s["cells"],"candidate_order":list(NAMES),
                  "parent_ptr":checkpoints["t1"]["pointer"],"query_sha256":b["query_sha256"]}
        out[n] = {"binder":b["binder"],"owner":n,"target":target,"target_id":source["target"],
                  "source_pdf":source["source_pdf"],"source_pdf_sha256":source["source_pdf_sha256"],
                  "rgb_keys_by_window":b["keys"],"query_f32le_hex":b["query_f32le"],
                  "query_sha256":b["query_sha256"],"checks":checkpoints}
    return {"anchor_order":list(NAMES),"anchors_sha256":bind["anchor_sha256"],"arm_weight_sha256":fit["weights"][arm],
            "cuts":fit["thresholds"][arm],"pair":pair["pair"],"members":out}


def main(candidate):
    assert not sys.flags.optimize and sys.flags.isolated and sys.flags.dont_write_bytecode
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip() == candidate
    def rfile(file):
        return blob(REVIEW,RDIR+file)
    def afile(file):
        return blob(AUTHOR,ADIR+file)
    reviewed = json.loads(rfile("runtime.json"))
    for name, expected in reviewed["evidence_sha256"].items():
        assert sha(rfile(name)) == expected
    series = [json.loads(line) for line in rfile("steps.jsonl").splitlines()]
    inventory = json.loads(rfile("catalog.json"))["captures"]
    sources = catalog_for_comparison(inventory)
    bindings = json.loads(rfile("bindings.json"))
    summaries = json.loads(rfile("findings.json"))
    history = json.loads(blob(*HISTORY))
    fixture = json.loads(blob(FIX,"docs/fixtures/WP-0028/manifest.json"))
    fit = json.loads(blob(FIT,"docs/research/WP-0026/fit/fit.json"))
    raw_files = {"sources.json":pretty(sources)}
    findings, queries, counts = {}, {}, {}
    for tag, proof in summaries.items():
        arm, length = tag.split("/")
        name = arm+"-"+length
        converted = [pair_row(i,r,sources) for i,r in enumerate(x for x in series if x["run"]==tag)]
        raw_files[name+".json"] = b"[\n" + b",\n".join(encoded(obj) for obj in converted) + b"\n]\n"
        findings[name] = check_findings(converted,proof)
        old, = (p for p in history["arms"][arm] if p["horizon"]==int(length))
        pair, = (p for p in fixture["pairs"] if p["horizon"]==int(length))
        queries[name] = parity(converted,bindings[tag],old,fit,pair,arm)
        counts[name] = {"paired_observations":len(converted),"member_observations":2*len(converted),
                        "completed_writes_per_member":proof["writes"],"native_attempts":2,
                        "certified_member_boundaries":6,"strict_paired_wins":len(proof["wins"])}
    raw_files.update({"findings.json":pretty(findings),"parity.json":pretty(queries)})
    outputs = {}
    duplicate = json.loads(afile("replay.json"))
    for name, expected in raw_files.items():
        actual = afile(name)
        if actual != expected:
            raise AssertionError(f"Byte disagreement for {name}: expected {sha(expected)} actual {sha(actual)}")
        assert duplicate["byte_comparison"][name] == {"identical_bytes":True,"bytes":len(actual),"sha256":sha(actual)}
        for f in ("runtime.json","runtime-repeat.json"):
            assert json.loads(afile(f))["deterministic_files_sha256"][name] == sha(actual)
        outputs[name] = {"bytes":len(actual),"independent_transcription_sha256":sha(expected),
                         "author_git_sha256":sha(actual),"entire_blob_identical":True}
    summary = {"author_evidence":AUTHOR,"review_evidence":REVIEW,"comparator":candidate,"command":sys.orig_argv,
               "captures":len(sources),"catalogued_source_rows":sum(len(s["spans"]) for s in sources.values()),
               "counts":counts,"files":outputs,"disposition":"exact agreement across all seven deterministic files"}
    write(OUT / (candidate + "-comparison.json"),pretty(summary))
    print(summary["disposition"], sum(v["bytes"] for v in outputs.values()),"bytes")


if __name__ == "__main__":
    main(*sys.argv[1:])
