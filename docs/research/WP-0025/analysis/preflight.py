"""CPU tests on WP-0024 archive evidence and manufactured schedules. No new model outputs."""
import copy
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from analyze import assemble, read, schedule
from compare import compare_hidden, compare_streams, divergence, signature
from evidence import ARCHIVE, H_FILES, Reference, check, digest, reconstruct_pool


def main():
    check(sys.flags.isolated and sys.dont_write_bytecode and os.environ.get("CUDA_VISIBLE_DEVICES")=="-1","CPU flags")
    ref=Reference()
    stock,hook=ref.history.values()
    diff=compare_streams(stock,hook,ref)
    check(diff["first_shared_prefix_divergence"]==13 and [r["delta_right_minus_left_999"] for r in diff["source_box_changes"]]
          ==[[0,0,-4,0]]+[[0,0,-1,0]]*3 and not diff["page_block_table_cell_changes"], "Historical observation")
    check(all(w["unique"] for mode in ref.history.values() for w in mode["witnesses"]), "Historical PDF witnesses")
    check(divergence([3,1],[3,1,2]) == (2,"end_of_stream",2) and divergence([1],[1])[0]=="+infinity","Sentinels")
    changed=stock["ids"].copy()
    changed[13]=hook["ids"][13]
    check(signature(stock["ids"],changed,ref.history)["classification"]=="partial_original_transitions","Partial signature")
    with TemporaryDirectory(dir=HERE) as temp:
        scratch=Path(temp)
        with ZipFile(ARCHIVE) as z:
            for name in H_FILES|{"duration.json"}:
                (scratch/name).write_bytes(z.read("run/sensor/b01w01H/"+name))
        dur=read(scratch/"duration.json")
        trace=reconstruct_pool(scratch,hook,dur)
        h={**hook,"hidden":trace}
        same=compare_hidden(h,h)
        check(same["hidden"]["bit_equal"] and same["pooled"]["bit_equal"] and same["hidden"]["count"]==284
              and same["pooled"]["count"]==14,"Historical hook self-comparison")
        # Deliberately change a token and an associated hidden component in memory only.
        manufactured={**h,"ids":h["ids"].copy(),"hidden":copy.deepcopy(trace)}
        manufactured["ids"][13]=stock["ids"][13]
        manufactured["hidden"]["bits"]=trace["bits"].copy()
        manufactured["hidden"]["bits"][10,0]^=1
        manufactured["hidden"]["states"]=(manufactured["hidden"]["bits"].astype("<u4")<<16).view("<f4")
        partial=compare_hidden(h,manufactured)
        check(partial["hidden_shared_prefix"]["count"]==13 and partial["hidden"]["first_differing"]==10
              and partial["hidden_matched_after_divergence"]["count"]==270 and partial["hidden"]["count"]==283,
              "Post-divergence alignment and difference")
        # Links records to synthetic schedules solely to exercise the five-way disposition.
        for modes,expected,problems in (
                ("SHHSHSSH","mode_associated_difference_under_both_orders",[]),
                ("SSSSSSSS","historical_mismatch_not_reproduced",[]),
                ("HHHSHSSH","stock_within_mode_variation",[]),
                ("SSHHHHHS","stock_within_mode_variation",[]),
                ("SSHS HSSH".replace(" ",""),"hooked_within_mode_variation_with_stable_stock",[]),
                ("SHHSHSS","incomplete",[]),("SHHSHSSH","incomplete",["synthetic guard failure"])):
            slots=schedule()
            samples={}
            for s,m in zip(slots,modes):
                record=ref.history[m]
                samples[s["tag"]]={**record,"hidden":trace}
                s.update(stream=record["sha256"],verified=True,witnesses=record["witnesses"])
            out=assemble(ref,slots,samples,{},problems)
            check(out["disposition"]==expected,f"Schedule {modes}: {out['disposition']} expected {expected}")
            check(len(out["historical_comparisons"])==16 and len(out["pairs"])==28 and len(out["hidden_pairs"])==6,
                  "Comparison counts")
            if len(modes)<8:
                check(all(v is None for v in out["through_eos_equal"][-1]) and all(v is None for v in out["first_shared_prefix_divergence"][-1]),
                      "Incomplete slots never become disagreement")
        pool=bytearray((scratch/"pooled.f32").read_bytes())
        pool[0]^=1
        (scratch/"pooled.f32").write_bytes(pool)
        dur["capture"]["pooled_sha256"]=digest(pool)
        (scratch/"capture.json").write_text(json.dumps(dur["capture"]),encoding="utf8")
        try:
            reconstruct_pool(scratch,hook,dur)
        except ValueError as e:
            check("independent FP32" in str(e),"Wrong corrupted-pool failure")
        else:
            raise ValueError("Corrupted pool passed independent reconstruction")
    print("PASS: historical IDs, four 999-scale box edits, actual PDF glyphs, 284 hidden rows, 14 pooled means, corruption, partial alignments, 7 schedules, undefined/+infinity.")


if __name__=="__main__":
    main()
