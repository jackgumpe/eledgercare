"""Recalculate trial summaries from committed local author measurements and unchanged scores."""
import hashlib
import json
from pathlib import Path

def read(path):
    return json.loads(path.read_bytes())

def summarize(folder):
    scored=read(folder/"scores/summary.json")
    cases={}
    for c in scored["cases"]:
        case=c["label"]
        mode=c["mode"]
        prefix=next(folder.glob("[0-9][0-9]-"+case+"-"+mode))
        winds=[]
        for p in sorted(prefix.glob("window-*.json")):
            w=read(p)
            if mode=="native":
                marks=w["clock_marks_ns"]
                winds.append(dict(first=w["first_page"],pages=w["pages"],kernel=w["kernel_path"],
                       ttft_s=w["prefill_time_s"],forward_count=w["forward_count"],eos=w["finish_reason"],
                       image_tokens=w["visual_tokens"],output_tokens=len(w["window_token_ids"]),
                       decode_first_last_s=(marks["last_token"]-marks["first_token"])/1e9,
                       vision_s=(marks["vision_end_end"]-marks["vision_start_start"])/1e9,
                       peak_reserved_bytes=w["vram"]["cuda_max_reserved_bytes"]))
            else:
                winds.append(dict(first=w["first_page"],pages=w["pages"],reader_ms=w["recognize_ms"],words=w["windows_ocr_words"]))
        cases.setdefault(case,{})[mode]=dict(elapsed_s=c["elapsed_s"],first_page_s=c["first_page_s"],counts=c["counts"],
               complete=c["complete"],complete_pages_min=60*len(c["pages"])/c["elapsed_s"] if c["complete"] else None,
               pages=c["pages"],windows=winds,prediction_sha=c["prediction_sha256"])
    return dict(cases=cases,comparisons=scored["comparisons"],process=read(folder/"process.json")["elapsed_s"])

def main():
    evidence=Path(__file__).resolve().parent/"evidence"
    sessions={run:summarize(evidence/run) for run in ("native-initial-02","dev-ab-01","dev-ba-01")}
    outcomes={}
    for family in ("short","dense","boundary"):
        ab,ba=[sessions[name]["cases"][family] for name in ("dev-ab-01","dev-ba-01")]
        comp=[sessions[name]["comparisons"][family] for name in ("dev-ab-01","dev-ba-01")]
        noise=abs(ab["native"]["elapsed_s"]-ba["native"]["elapsed_s"])
        savings=[row["native"]["elapsed_s"]-row["windows"]["elapsed_s"] for row in (ab,ba)]
        ratios=[row["native"]["elapsed_s"]/row["windows"]["elapsed_s"] for row in (ab,ba)]
        outcomes[family]=dict(control_spread_s=noise,paired_savings_s=savings,paired_speed_ratios=ratios,
              both_savings_exceed_noise=all(v>noise for v in savings),
              windows_inside_budget_each=[c["inside_quality_budget"] for c in comp],
              new_or_changed_critical_errors_each=[c["new_or_changed_critical_errors"] for c in comp],
              windows_unattended_each=[c["unattended_quality_gate"] for c in comp],
              predictions_repeat={m:ab[m]["prediction_sha"]==ba[m]["prediction_sha"] for m in ("native","windows")})
    print(json.dumps(dict(protocol="AB and BA source regeneration; spread between the two paired controls",sessions=sessions,outcomes=outcomes),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
