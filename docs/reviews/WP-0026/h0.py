"""Compare actual S/H artifacts on their eight matched post-W0 ordinals and every physical witness."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import BASE, HOST, MODEL, ROOT, SCRATCH, H0_PLAN, WITNESS, blob, cpu, pinned, read, reference, sample, save, sha, stream

def originals():
    plan = blob(BASE, "docs/coordination/WP-0024/h0-r1-plan.json")
    witnesses = blob(BASE, "docs/fixtures/WP-0024/h0/source-witness.json")
    assert sha(plan) == H0_PLAN and sha(witnesses) == WITNESS
    return json.loads(plan), json.loads(witnesses)

def expected(order, history):
    tags = []
    for b in range(1,3):
        half = (order == "p1") == (b == 1)
        for w in range(1,5):
            tags.append(f"b{b:02d}w{w:02d}"+("S" if half else "H"))
    return [next(c for c in history["calls"] if c["tag"] == t) for t in tags]

def compare(directories, plans, explicit):
    from h0_audit import align
    from h0_full_audit import change
    history, witnesses = originals()
    assert len(witnesses["witnesses"]) == 10
    prompt = reference()
    pairs, samples = [], {}
    source = {}
    expected_orders = {k:expected(k,history) for k in ("p1","p2")}
    for order in expected_orders:
        for c, old in zip(plans[order]["calls"], expected_orders[order], strict=True):
            for key in ("tag","hooked","retain_hidden","binder","window","pages"):
                assert c[key] == old[key], (order,key,c["tag"])
    for j in range(8):
        info = {"ordinal_after_load":j+2}
        folders = {}
        for order in ("p1","p2"):
            c = plans[order]["calls"][j]
            tag = c["tag"]
            d = directories[order]/tag
            samples[tag] = sample(d, c["hooked"], prompt, explicit)
            mode = "H" if c["hooked"] else "S"
            folders[mode] = d
            assert tag.endswith(mode)
            info[mode] = {"order":order, "tag":tag, "sha256":samples[tag]["through_eos_sha256"],
                          "emitted_before_eos":samples[tag]["emitted"]}
            source[c["binder"],c["window"],mode] = d
        left,right = [read(folders[m]/"native.json") for m in ("S","H")]
        info["through_eos_equal"] = stream(folders["S"],explicit) == stream(folders["H"],explicit)
        info["edits"] = change(left,right)
        assert (info["edits"] == []) == info["through_eos_equal"]
        comparable = ("prompt","prompt_token_ids","text","token_ids","terminal_observation","num_pages_out",
                      "expected_pages","finish_reason","eos_id","eos_observed","stop_cause")
        info["differing_native_fields"] = [k for k in comparable if left[k] != right[k]]
        metas = [read(folders[m]/"metadata.json") for m in ("S","H")]
        info["source_metadata_equal"] = metas[0] == metas[1]
        info["page_text_equal"] = [a["text"]==b["text"] for a,b in zip(metas[0]["pages"],metas[1]["pages"],strict=True)]
        info["page_grid_equal"] = [[t["rows"] for t in a["tables"]]==[t["rows"] for t in b["tables"]]
                                   for a,b in zip(metas[0]["pages"],metas[1]["pages"],strict=True)]
        pairs.append(info)
    alignments = []
    for witness in witnesses["witnesses"]:
        b,window = witness["binder"],witness["window"]
        pdf = next(Path(r["pdf"]) for r in history["requests"] if Path(r["pdf"]).stem == b)
        assert sha(pdf.read_bytes()) == witnesses["documents"][b]
        row = {mode:align(witness,read(source[b,window,mode]/"metadata.json"),pdf) for mode in ("S","H")}
        alignments.append(row)
    equal = sum(r["through_eos_equal"] for r in pairs)
    unique = {mode:sum(r[mode]["unique_literal_and_geometry"] for r in alignments) for mode in ("S","H")}
    passed = (equal == 8 and unique == {"S":10,"H":10} and
              all(not r["differing_native_fields"] and r["source_metadata_equal"] for r in pairs))
    return {"gate":"PASS" if passed else "FAIL","streams_equal":equal, "first_scored_pair":pairs[0],
            "samples":samples, "matched_windows":pairs, "unique_physical_witnesses":unique,
            "physical_witness_archive_sha256":WITNESS, "alignments":alignments,
            "pooled_vectors_reconstructed":sum(r.get("pooled_bit_exact",0) for r in samples.values()),
            "consumed_positions_verified":sum(r.get("positions",0) for r in samples.values())}

def archival_control():
    history, _ = originals()
    plans = {k:{"calls":expected(k, history)} for k in ("p1","p2")}
    archive = ROOT/"docs/reviews/WP-0024/h0-r1.zip"
    assert sha(archive.read_bytes()) == "37670af4116f543e2d0104b5d3599d88f2e2d06fc092418ee1cf839769430fc6"
    with TemporaryDirectory(dir=SCRATCH) as tmp, ZipFile(archive) as z:
        directories = {k:Path(tmp)/k for k in plans}
        for order, plan in plans.items():
            for c in plan["calls"]:
                tag = c["tag"]
                d = directories[order]/tag
                d.mkdir(parents=True)
                prefix = "run/sensor/"+tag+"/"
                for name in z.namelist():
                    if name.startswith(prefix):
                        (d/name.removeprefix(prefix)).write_bytes(z.read(name))
        result = compare(directories,plans,explicit=False)
    assert result["gate"] == "FAIL" and result["streams_equal"] == 7
    assert [e["stock_index"][0] for e in result["first_scored_pair"]["edits"]] == [13,77,100,146]
    assert result["unique_physical_witnesses"] == {"S":10,"H":10}
    assert result["pooled_vectors_reconstructed"] == 72 and result["consumed_positions_verified"] == 1412
    return {"purpose":"CPU regression test using previously published unconditioned WP24 artifacts only",
            **{k:result[k] for k in ("gate","streams_equal","first_scored_pair","unique_physical_witnesses",
                                      "pooled_vectors_reconstructed","consumed_positions_verified")}}

def live(release_file,pin):
    release = pinned(release_file,pin)
    assert release["packet"] == "WP-0026" and release["operator"] == "eld-rd-reviewer"
    assert [o["run"] for o in release["orders"]] == ["p1","p2"]
    plans, dirs = {}, {}
    for order in release["orders"]:
        k = order["run"]
        plan = pinned(Path(order["plan"]),order["plan_sha256"])
        assert plan["candidate"] == release["review_worktree_head"] and plan["model_revision"] == MODEL
        assert plan["phase"] == "h0" and plan["process_id"].lower() == k
        d = Path(order["output"])/"sensor"
        assert d == Path(plan["output"])/"sensor" == HOST/"review/runs"/k/"sensor"
        assert read(d/"binding.json")["plan_sha256"] == order["plan_sha256"]
        plans[k], dirs[k] = plan,d
    return compare(dirs,plans,True) | {"release_sha256":pin,"candidate":release["review_worktree_head"],
                                        "plan_pins":{o["run"]:o["plan_sha256"] for o in release["orders"]}}

if __name__ == "__main__":
    cpu()
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output",type=Path)
    cli.add_argument("--release",type=Path)
    cli.add_argument("--sha")
    args = cli.parse_args()
    if args.release:
        assert args.sha
        result = live(args.release,args.sha)
        save(args.output,result)
        sys.exit(0 if result["gate"] == "PASS" else 2)
    save(args.output,archival_control())
