"""Reconcile auxiliary public rows and return exact execution-boundary counts. No model or tensors."""
import io
import itertools
import json
import math
import re
import sys
from hashlib import sha256
from collections import Counter
from zipfile import ZipFile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from compare import rows, index, equality, git, HERE, INDEPENDENT, KEY, POINT

AUTHOR="65df68e86fe540c4c61ec2deba813e8d95b10da9"
A=lambda name:rows(AUTHOR,"docs/research/WP-0035",name)[0]
R=lambda name:rows(INDEPENDENT,"docs/reviews/WP-0035",name)[0]


def eq(a,b):
    assert equality(a,b),(a,b)


def mapping(a,b,fields):
    for k,j in fields.items(): eq(a[k],b[j])


def same(a,b,fields):
    mapping(a,b,{k:k for k in fields.split()})


def decoded(h):
    return sha256(bytes.fromhex(h)).hexdigest()


def main():
    out={}
    scores=index(R("scores"),KEY+["binder"]+POINT)
    reports=A("scores")
    checks="actual_step depth scope eligible zero query_sha256 read_sha256 matrix_sha256 owner_columns_sha256 registry ptr leaders scores"
    labels={"root_declaration":"designated_declaration","OPEN_CHILD":"child_entry","CONFIRM_POP":"pop_commit",
            "post_target":"post_target_write","first_window_end":"opening_end"}
    for a in reports:
        b=scores[tuple(a[k] for k in KEY+["binder"]+POINT)]
        same(a,b,checks)
        mapping(a,b,{"expected_owner":"truth","directory":"candidates","signed_margin":"margin","gate_gap_f32":"fp32_gap"})
        eq(a["event_kinds"],[e["kind"] for e in b["events"]])
        eq(sorted(labels.get(k,k.replace("write_","write")) for k in a["checkpoints"]),sorted(b["checkpoint"]))
    out["score_auxiliary"]=dict(count=len(reports),fields=checks,checkpoint_aliases=labels)
    cols=index(R("contrasts"),KEY+POINT)
    for a in A("contrasts"):
        b=cols[tuple(a[k] for k in KEY+POINT)]
        same(a,b,"actual_steps full_directory_wins")
        eq(a["fp64le"],b["f64le"])
    geom=index(R("anchor_geometry"),["pair","binder","model"])
    anchor_signatures={}
    for a in A("anchors"):
        b=geom[a["pair"],a["binder"],a["model"]]["anchors"]
        eq(a["choices"],b["directory"])
        eq(a["raw_f32le"],b["projected_hex"])
        hashes=[decoded(h) for h in [a["raw_f32le"],a["anchors_f32le"]["R0"],a["anchors_f32le"]["R1"]]]
        eq(hashes,[b["raw_sha256"],b["native_sha256"],b["centered_sha256"]])
        marker=a["model"]
        assert anchor_signatures.setdefault(marker,hashes)==hashes
    out["anchor_rows"]=len(A("anchors"))
    out["anchor_raw_native_centered_sha256"]=anchor_signatures
    ws=index(R("writes"),["pair","binder","model","write"])
    extra=Counter()
    calibrated_runs=Counter()
    overlap=0
    phases=Counter()
    shared_per_role=Counter()
    for a in A("writes"):
        k=(a["pair"],a["binder"],a["model"],a["write"])
        obs=ws[k]["observations"]
        use=a["updates"][:len(obs)]
        tail=a["updates"][len(obs):]
        assert len(use)==len(obs)
        for l,r in zip(use,obs,strict=True):
            same(l,r,"step ptr alpha beta alpha_beta rho")
            mapping(l,r,dict(window_key="window",span_text="text",depth="depth_after",designated="designate",
                             downstream="downstream_root",effective_alpha="retention"))
            eq(l["events"],[e["kind"] for e in r["events"]])
        overlap+=len(use)
        shared_per_role[a["task"]]+=len(use)
        if tail:
            assert a["task"]=="B" and "TARGET" in tail[0]["events"] and all(u["after_target"] for u in tail)
            extra[a["binder"]]+=len(tail)
            calibrated_runs[a["binder"]]+=1
            phases["target_span_write"]+=1
            phases["later_span_write"]+=len(tail)-1
    out["updates"]=dict(common=overlap,common_per_task=shared_per_role,author_only=sum(extra.values()),
                        run_counts=calibrated_runs,after_target_per_binder=extra,after_target_by_phase=phases)
    terminals=index(R("terminals"),KEY+["binder"])
    per_field=0
    for a in A("terminals"):
        b=terminals[tuple(a[k] for k in KEY+["binder"])]
        same(a,b,"answerable expected target")
        eq(a["full_correct"],(b["typed_status"]=="C" if b["answerable"] else b["typed_status"]=="A"))
        eq(a["full_decision"],{"C":"correct","W":"wrong","A":"abstain"}[b["typed_status"]])
        if a["owner_decision"] not in (None,"unavailable"):
            eq(a["owner_decision"],{"C":"correct","W":"wrong","A":"abstain"}[b["owner_status"]])
        for x,y in zip(a["attempts"],b["attempts"],strict=True):
            if a["model"]=="M2":
                eq(x["typed"],y)
            else:
                same(x,y,"ptr reason typed summary_target summary_zero zero")
                eq(x["field_scores_hex"],{f:val["f32le"] for f,val in y["fields"].items()})
                eq(x["field_scores"],{f:val["scores"] for f,val in y["fields"].items()})
                per_field+=len(y["fields"])
    out["terminal_field_score_vectors"]=per_field
    effects=index(R("mechanism_differences"),KEY+POINT+["contrast"])
    for row in A("effects"):
        label="R1-R0" if row["base_read"]!=row["read"] else row["write"]+"-"+row["base_write"]
        r=effects[tuple(row[f] for f in KEY+POINT)+(label,)]
        eq(row["difference"],{k:r[k] for k in row["difference"]})
    out["effects"]=len(effects)
    apr=A("admission")
    rpr=R("parity")
    eq(len(apr["native_pairs"]),len(rpr["native224"]))
    for a in apr["write8"]:
        b=rpr["relative_half"][a["cell"]]
        same(a,b,"score_hex query_sha256 read_sha256")
        mapping(a,b,dict(result_matrix="matrix_sha256",signed_margin="margin"))
    out["crossed_score_read_matrix_query"]=4
    bindings=A("bindings")
    ours=json.loads(git("cat-file","blob",INDEPENDENT+":docs/reviews/WP-0035/bindings.json"))
    for case in bindings["routes"]:
        o,=[c for c in ours["cases"] if c["pair"]==case["pair"]]
        same(case,o,"task horizon")
        assert set(o["members"])=={m["binder"] for m in case["members"]}
        for m in case["members"]:
            mem=o["members"][m["binder"]]
            same(m,mem,"target expected")
            eq(m["tags"],mem["keys"])
            eq(case["answerable"],mem["answerable"])
    for k,item in bindings["development_inventory"].items():
        ref=ours["development_windows"][k]
        same(item,ref,"pages prefix")
        eq(item["members_sha256"],ref["members"])
    spec=bindings["calibration_archive"]
    archive=git("cat-file","blob",spec)
    assert sha256(archive).hexdigest()==ours["git_blobs"][spec]
    with ZipFile(io.BytesIO(archive)) as zip_file:
        for tag,a in bindings["physical"].items():
            b=ours["calibration_windows"][tag]
            eq(a["prefix"],b["archive_prefix"])
            eq([p["rgb_sha256"] for p in a["pages"]],b["ordered_rgb_sha256"])
            for name,h in a["hashes"].items():
                eq(sha256(zip_file.read(a["prefix"]+name)).hexdigest(),h)
    for path,h in bindings["git_sources_sha256"].items():
        eq(sha256(git("cat-file","blob",path)).hexdigest(),h)
    out["routes"]=len(bindings["routes"])
    out["git_source_blobs"]=len(bindings["git_sources_sha256"])
    out["cal_physical_members"]=sum(len(a["hashes"]) for a in bindings["physical"].values())
    out["development_members"]=sum(len(a["members_sha256"]) for a in bindings["development_inventory"].values())
    am=A("metrics")
    at=index(R("attenuation"),["pair","model","write","read"])
    for a in am["attenuation"]:
        b=at[a["pair"],a["model"],a["write"],a["read"]]
        same(a,b,"delta8 delta11")
        eq(a["fraction_abs_lost"],b["abs_delta_loss_fraction_8_to_11"])
    for a in am["dynamics"]:
        k=(a["pair"],a["binder"],a["model"],a["write"])
        obs=ws[k]["observations"]
        last=next((v["step"] for v in obs if "TARGET" in [e["kind"] for e in v["events"]]),math.inf)
        elig=[u for u in obs if u["step"]<last and u["downstream_root"]]
        eq(a["eligible_root_writes"],len(elig))
        eq(a["alpha_beta_over_one"],sum(u["alpha_beta"]>1 for u in elig))
        eq(a["native_alpha_product"],math.prod(u["alpha"] for u in elig))
        eq(a["effective_alpha_product"],math.prod(u["retention"] for u in elig))
        eq(a["declaration_steps"],[u["step"] for u in obs if u["designate"]])
    metrics=index(R("metrics"),["scope","model","write","read"])
    population_rows=0
    for scope,groups in am["by_population"].items():
        for key,a in groups.items():
            b=metrics[(scope.replace("-safety","").replace("-","/"),*key.split("/"))]
            safe="safety" in scope
            counts=b["safety"] if safe else b["typed"]
            eq(a["binders"],b["safety_binders"] if safe else b["answerable_binders"])
            eq(a["no_target"],b["safety_no_target"] if safe else 0)
            for field,s in (("correct","C"),("wrong","W"),("abstain","A")): eq(a["typed_"+field],counts[s])
            if b["owner"] and not safe:
                eq(a["both_ranked"],b["both_ranked"])
                eq(a["rank_pairs"],b["ranked_pairs"])
                for f,s in (("score_failed","score_only"),("gap_failed","gap_only"),("both_failed","both"),("neither_failed","pass")):
                    eq(a["cutoff_"+f],b["cutoff_breakdown"].get(s,0))
                for field,s in (("correct","C"),("wrong","W"),("abstain","A")): eq(a["owner_"+field],b["owner"][s])
            population_rows+=1
    out.update(attenuation_rows=len(at),dynamic_rows=len(am["dynamics"]),population_rows=population_rows,passed=True)
    (HERE/"evidence"/"auxiliary-cross-check.json").write_bytes((json.dumps(out,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps(out,sort_keys=True))


if __name__=="__main__":
    main()
