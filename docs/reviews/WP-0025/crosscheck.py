"""Compare the separately reconstructed numerical results with the published /002 artifact."""
from hashlib import sha256
import json
from pathlib import Path
import sys


def verify(independent,author,guard):
    own,result,resources=[json.loads(f.read_bytes()) for f in (independent,author,guard)]
    tags=result["tags_in_matrix_order"]
    labels={"baseline variation observed":"stock_within_mode_variation",
            "variation observed with capture enabled":"hooked_within_mode_variation_with_stable_stock",
            "mode-associated difference under both orders":"mode_associated_difference_under_both_orders",
            "mismatch not reproduced":"historical_mismatch_not_reproduced","incomplete":"incomplete"}
    verdict="incomplete" if resources["issues"] else own["verdict"]
    assert result["disposition"]==labels[verdict]
    assert result["through_eos_equal"]==[[own["agreement"][l][r] for r in tags] for l in tags]
    for row in result["pairs"]:
        k=row["left"]+"/"+row["right"]
        assert row["equal"]==(own["comparisons"][k]["equal"] if own["comparisons"][k] else None)
        if row["detail"] is None:
            continue
        check=own["comparisons"][k]
        assert (check["first_divergence"] if check["first_divergence"] is not None else "+infinity")==row["first_divergence"]
        assert len(check["edits"])==len(result["stream_pair_details"][row["detail"]]["edits"])
    for row in result["historical_comparisons"]:
        comp=own["comparisons"][row["tag"]+"/b01w01"+row["historical_mode"]]
        assert (comp["equal"] if comp else None)==row["equal"]
        if comp:
            assert (comp["first_divergence"] if comp["first_divergence"] is not None else "+infinity")==row["first_divergence"]
    for slot in result["slots"]:
        tag=slot["tag"]
        assert slot["verified"]==(tag in own["samples"])
        if slot["verified"]:
            s=own["samples"][tag]
            assert slot["stream"]==s["through_eos_le_u32_sha256"]
            assert slot["terminal"]==s["processed_terminal"]
            assert {w["kind"]:w["unique"] for w in slot["witnesses"]}=={k:v["unique"] for k,v in s["witnesses"].items()}
            if tag[-1]=="H":
                assert slot["hidden"]["rebuilt_exact_sha256"]==s["pooled_sha256"]
    for pair,other in result["hidden_pairs"].items():
        if other is None:
            continue
        x=own["hh"][pair.replace(":","/")]
        assert x["aligned_rows"]==other["hidden"]["count"] and x["aligned_spans"]==other["pooled"]["count"]
        assert x["rows_max_abs_fp32"]==other["hidden"]["max_abs_f32"] and x["pools_max_abs_fp32"]==other["pooled"]["max_abs_f32"]
        assert x["first_different_row"]==other["hidden"]["first_differing"] and x["first_different_pool"]==other["pooled"]["first_differing"]
        for a,b in zip(x["rows"],other["hidden_row_differences"],strict=True):
            assert a["i"]==b[0] and a["max_abs_fp32"]==b[-1] and a["byte_equal"]==(b[-2]==0)
        for a,b in zip(x["spans"],other["pool_differences"],strict=True):
            assert a["left"]==b[0] and a["right"]==b[1] and a["byte_equal"]==(b[-2]==0) and a["max_abs_fp32"]==b[-1]
    return {"author_artifact_sha256":sha256(author.read_bytes()).hexdigest(),"agreed_disposition":result["disposition"],
            "slots_compared":len(tags),"matrix_dimensions":[len(tags),len(tags)],"historical_comparisons":len(result["historical_comparisons"]),
            "all_28_pairs":len(result["pairs"]),"hh_row_and_pool_comparisons":sum(t is not None for t in result["hidden_pairs"].values()),
            "independent_resource_issues":resources["issues"]}


if __name__=="__main__":
    a,b,c,d=map(Path,sys.argv[1:])
    out=verify(a,b,c)
    with d.open("x",encoding="utf8",newline="\n") as f:
        f.write(json.dumps(out,indent=2)+"\n")
