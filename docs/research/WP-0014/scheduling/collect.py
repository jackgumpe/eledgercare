"""Collect scoped public synthetic scheduling receipts and compute all intervals from matched identities."""
import argparse
import datetime
import hashlib
import json
import shutil
from pathlib import Path

UTC = datetime.timezone.utc
PHASES = ["stock","demandfirst","demand","immediate","ready"]
EXPECTED = {
    "A": "The garden crew left a clean watering can beside the greenhouse door. A gray rabbit crossed the gravel path before the morning bell. When the sun reached the bench, two sparrows landed near the empty basket.",
    "B": "The print shop set a blue notebook on the counter near the window. A bicycle courier rang the silver bell just before lunch. After the rain passed, the clerk carried the parcels to the yellow van."
}
def read(p):
    return json.loads(p.read_text(encoding="utf8"))
def lines(p):
    return [json.loads(x) for x in p.read_text(encoding="utf8").splitlines()]
def dump(p,data):
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
def event(records,k,v):
    matches = [r for r in records if r[k]==v]
    assert len(matches)==1, (k,v,len(matches))
    return matches[0]
def iso_ms(s):
    return datetime.datetime.fromisoformat(s).timestamp()*1000
def filetime_ms(s):
    return (s-116444736000000000)/10000

def analyze(run,out):
    out.mkdir(parents=True,exist_ok=False)
    db=read(run/"database.json")
    attempts=read(run/"attempts.json")
    gpu=lines(run/"gpu.jsonl")
    for f in ["database.json","attempts.json","run.json","gpu.jsonl"]:
        shutil.copyfile(run/f,out/f)
    rows=[]
    pairs=[]
    lifetimes=[]
    for phase in PHASES:
        source=run/phase
        dest=out/phase
        dest.mkdir()
        b=lines(source/"browser.jsonl")
        mgr=lines(source/"manager.jsonl")
        resident=lines(source/"engine.jsonl") if (source/"engine.jsonl").exists() else []
        for f in ["browser.jsonl","manager.jsonl","engine.jsonl"]:
            if (source/f).exists():shutil.copyfile(source/f,dest/f)
        warm=source/"runs/warmup/output/envelope.json"
        if warm.is_file():
            shutil.copyfile(warm,dest/"warmup-envelope.json")
            shutil.copyfile(warm.parent/"raw_output.utf8.bin",dest/"warmup-output.txt")
        cfg=read(source/"config.json")
        ids=cfg["inputs"]
        for key in ids:
            saved=read(source/f"saved-{key}.json")
            kept=event([r for r in b if r.get("key")==key],"name","reopened")
            doc=saved["documentId"]
            result=saved["result"]
            attempt=result["attemptId"]
            assert kept["doc"]==doc and kept["attempt"]==attempt and kept["original"]==cfg["hashes"][key]
            assert kept["raw"]==result["rawSha256"]==hashlib.sha256(result["rawText"].encode()).hexdigest()
            pdf_out=source/"runs"/("attempt-"+attempt)/"output"
            env=read(pdf_out/"envelope.json")
            assert env["output"]["sha256"]==result["rawSha256"] and env["status"]=="completed"
            assert result["rawText"].encode()==(pdf_out/"raw_output.utf8.bin").read_bytes()
            assert env["input"]["sha256"]==cfg["hashes"][key] and env["output"]["output_page_count"]==1
            shutil.copyfile(pdf_out/"envelope.json",dest/(key+"-envelope.json"))
            shutil.copyfile(pdf_out/"raw_output.utf8.bin",dest/(key+"-raw.txt"))
            projections=saved.copy()
            projections["result"]={k:v for k,v in result.items() if k not in ("pages","rawText")}
            dump(dest/(key+"-saved-identities.json"),projections)
            a=event(attempts,"attempt_id",attempt)
            db_doc=[d for d in db if d["document_id"]==doc]
            ts={d["status"]:d["commit_ms"] for d in db_doc}
            assert set(ts)=={"queued","running","completed"}
            events={r["name"]:r["browser_ms"] for r in b if r.get("key")==key and "browser_ms" in r}
            assert event([r for r in b if r.get("key")==key],"name","result_viewport_frame")["inViewport"]
            intake=events["intake_open"]
            click=events["request-extraction"]
            layout=events["result_layout"]
            visible=events["result_viewport_frame"]
            request_ms=iso_ms(env["timings"]["started_at_utc"])
            end_ms=iso_ms(env["timings"]["completed_at_utc"])
            bridge_path=source/"control"/(attempt+".job")
            bridge=read(bridge_path) if bridge_path.exists() else None
            if bridge:shutil.copyfile(bridge_path,dest/(key+"-bridge.json"))
            entry=bridge["worker_start_ms"] if bridge else request_ms
            plain=" ".join(" ".join(i["text"] for i in result["pages"][0]["blocks"]).split())
            row={"phase":phase,"key":key,"document":doc,"attempt":attempt,"clock_ms":{"intake":intake,"selection":events["select"],
                "click":click,"queue_commit":ts["queued"],"claim_commit":ts["running"],"launcher_creation":filetime_ms(a["launcher_create_filetime"]),
                "worker_entry":entry,"request_in_engine":request_ms,"envelope_completed":end_ms,"result_commit":ts["completed"],"first_layout":layout,"visible":visible},
                "interval_s":{},"queue_snapshot":[[r["status"],r["queued"],r["active"]] for r in db_doc],
                "expected_exact_after_whitespace":plain==EXPECTED[key],"raw_sha":result["rawSha256"],"source_sha":env["input"]["sha256"],
                "rgb_sha":env["diagnostics"]["rendered_pages"][0]["rgb_sha256"],"output_tokens":env["output"]["output_token_count"],"prompt_tokens":env["diagnostics"]["prompt_token_count"],
                "worker_ms":env["timings"],"torch_peak_alloc":env["diagnostics"]["cuda_max_allocated_bytes"],"torch_peak_reserved":env["diagnostics"]["cuda_max_reserved_bytes"]}
            for name,delta in {"intake_to_click":click-intake,"intake_to_viewport":visible-intake,"click_to_queue":ts["queued"]-click,
                "queue_to_claim":ts["running"]-ts["queued"],"claim_to_launcher":filetime_ms(a["launcher_create_filetime"])-ts["running"],
                "launcher_to_entry":entry-filetime_ms(a["launcher_create_filetime"]),"worker_entry_to_request":request_ms-entry,
                "request_to_envelope_end":end_ms-request_ms,"envelope_end_to_result_commit":ts["completed"]-end_ms,"commit_to_layout":layout-ts["completed"],
                "commit_to_viewport":visible-ts["completed"],"click_to_visible":visible-click,"click_to_layout":layout-click}.items():
                row["interval_s"][name]=round(delta/1000,4)
            rows.append(row)
        phase_rows=[r for r in rows if r["phase"]==phase]
        c=[r["clock_ms"] for r in phase_rows]
        if len(c)==2:
            pairs.append({"phase":phase,"click_separation_s":round((c[1]["click"]-c[0]["click"])/1000,3),
                "first_commit_from_first_click_s":round((min(x["result_commit"] for x in c)-min(x["click"] for x in c))/1000,3),
                "both_committed_from_first_click_s":round((max(x["result_commit"] for x in c)-min(x["click"] for x in c))/1000,3),
                "first_visible_from_first_click_s":round((min(x["visible"] for x in c)-min(x["click"] for x in c))/1000,3),
                "both_visible_from_first_click_s":round((max(x["visible"] for x in c)-min(x["click"] for x in c))/1000,3),
                "both_visible_from_first_intake_s":round((max(x["visible"] for x in c)-min(x["intake"] for x in c))/1000,3)})
        t0=min(x["intake"] for x in c)
        t1=max(x["visible"] for x in c)
        pool=[g for g in gpu if t0<=g["t_ms"]<=t1]
        ready=next((e["t_ms"] for e in resident if e["event"]=="ready_after_warmup"),None)
        launch=next((e["t_ms"] for e in mgr if e["event"]=="launch_requested"),None)
        lifetimes.append({"phase":phase,"resident_pids":sorted({e["pid"] for e in resident}),"resident_model_loads":sum(e["event"]=="model_load_start" for e in resident),
            "resident_calls":[e["item"] for e in resident if e["event"]=="infer_start"],"ready_after_launch_s":round((ready-launch)/1000,3) if ready else None,
            "ready_from_first_intake_s":round((ready-t0)/1000,3) if ready else None,
            "ready_minus_first_click_s":round((ready-min(x["click"] for x in c))/1000,3) if ready else None,
            "device_peak_mib":max(int(g["device"].split(", ")[1]) for g in pool),
            "max_nondesktop_gpu_clients":max(len(g["compute"]) for g in pool),"rendered_pages":1})
    assert len(rows)==7 and len(attempts)==7 and len(db)==21
    dump(out/"summary.json",{"rows":rows,"pairs":pairs,"lifetimes":lifetimes})
    print(json.dumps({"rows":[[r["phase"],r["key"],r["expected_exact_after_whitespace"],r["interval_s"]] for r in rows],"pairs":pairs,"lifetimes":lifetimes},indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("run",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    analyze(a.run,a.out)
