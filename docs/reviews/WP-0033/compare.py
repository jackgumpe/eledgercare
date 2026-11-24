"""Read the independently sealed blobs. This comparison contains no model or write operation."""
import gzip
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

AUTHOR="8849be2f8f7fb83559d944e2db5527d9929aa8b7"
REVIEW="b65574714e8ffa3731a0f7f7c1f1fb560214adbb"
ROOT=Path(__file__).resolve().parents[3]
METRICS={}
COUNTS={}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def raw(side,name):
    revision,path=(AUTHOR,"research") if side=="author" else (REVIEW,"reviews")
    return subprocess.check_output(["git","cat-file","blob",f"{revision}:docs/{path}/WP-0033/evidence/{name}"],cwd=ROOT)


def data(side,name):
    b=raw(side,name)
    return json.loads(gzip.decompress(b) if name.endswith(".gz") else b)


def eq(label,a,b):
    if a!=b:
        raise ValueError((label,a,b))
    COUNTS[label]=COUNTS.get(label,0)+1


def unpack(hexstr):
    buf=bytes.fromhex(hexstr)
    return struct.unpack(f"<{len(buf)//8}d",buf)


def number(label,a,b,budget=None):
    assert math.isfinite(a) and math.isfinite(b)
    d=abs(a-b)
    limit=2e-5*(1+max(abs(a),abs(b))) if budget is None else budget
    assert d<=limit,(label,a,b,limit)
    result=dict(author=a,reviewer=b,residual=a-b,budget=limit)
    state=METRICS.setdefault(label,dict(count=0,max_absolute=0.,max_fraction=-1))
    state["count"]+=1
    state["max_absolute"]=max(state["max_absolute"],d)
    if d/limit > state["max_fraction"]:
        state.update(max_fraction=d/limit,worst=result)
    return result


def coordinates(label,a,b):
    for x,y in zip(unpack(a),unpack(b),strict=True):
        number(label,x,y)


def verify_packs(obj):
    if isinstance(obj,dict):
        if set(("shape","dtype","bytes","sha256")).issubset(obj):
            binary=bytes.fromhex(obj["bytes"])
            eq("packed vector digest",sha(binary),obj["sha256"])
            eq("packed vector length",len(binary),math.prod(obj["shape"])*{"f32le":4,"f64le":8}[obj["dtype"]])
        for v in obj.values():
            verify_packs(v)
    if isinstance(obj,list):
        for v in obj:
            verify_packs(v)


def key(row):
    return row["mode"],row["point"],row["cell"]


def archive_checks(arm,table):
    checks=data("author",arm+"-checks.json.gz")
    verify_packs(checks)
    n=0
    for x in checks:
        if "compared" in x:
            arrays=[unpack(x[field]["bytes"]) for field in ("observed","predicted","residual","budget")]
            for a,b,residual,budget in zip(*arrays,strict=True):
                eq("author vector residual",a-b,residual)
                eq("author vector T",2e-5*(1+max(abs(a),abs(b))),budget)
                assert abs(residual)<=budget
            n+=len(arrays[0])
        else:
            a,b,r,lim=(x[f] for f in ("observed","predicted","residual","budget"))
            eq("author scalar residual",a-b,r)
            assert abs(r)<=lim
            n+=1
        assert x["passed"]
    eq("author scalar check count",n,table["checks"]["scalars"])
    eq("author check failures",0,table["checks"]["failures"])
    return n


def m1(a,r):
    x,y=a["operands"],r["analysis"]["coefficients"]
    for s in x:
        for term in ("R","V","E"):
            coordinates("M1 term",x[s][term]["bytes"],y[s]["archived_terms"][term]["observed_f64le"])
        for term,alias in (("old_k","recipient_times_full_key"),("h","margin_axis_f64le")):
            coordinates("M1 "+term,x[s][term]["bytes"],y[s][alias])
        coordinates("M1 u",x[s]["u"]["bytes"],y[s]["u_f64le"][:32*16])
        for name in ("P","L"):
            number(name,x[s][name],y[s][name]["observed"])
        for name in ("relative","absolute"):
            eq("exact "+name+" root",x[s][name+"_root"],r["analysis"]["roots"][name][s])
    eq("raw donor roots",a["raw_donor_relative_roots"],r["analysis"]["roots"]["raw_donor_contrast_roots_relative"])
    for mode in ("relative","absolute"):
        p,q=a[mode+"_intervals"],r["analysis"]["roots"][mode+"_intervals"]
        eq("four cell interval",p["all_four_open"],q["four_cell_open"])
        eq("original twin interval",p["original_twins_open"],q["original_twins_open"])
    effects={}
    for group in a["summary"]:
        name=group["mode"]+"/"+group["point"]
        y=r["analysis"]["rank_decisions"][name]
        eq("four ranks correct",group["four_donor_ranks"],y["four_cells_correct"])
        eq("two twins correct",group["both_original_twins"],y["original_twins_correct"])
        effects[name]={}
        for prefix,fields in group["contrasts"].items():
            pair={}
            for name2,o in fields.items():
                v=r["analysis"]["fixed_prefix_contrasts"][name][prefix][name2]
                eq("M1 donor contrast sign",o["sign"],v["sign"])
                number("M1 predicted donor contrasts",o["predicted"],v["predicted"],v["budget"])
                pair[name2]=dict(**number("M1 donor contrasts",o["value"],v["observed"],v["budget"]),
                      author_signed_zero_budget=o["zero_budget"],reviewer_signed_zero_budget=v["budget"],sign=v["sign"])
            effects[name][prefix]=pair
    return effects


def m3(a,r):
    names={"pooled_at_A":"pooled_at_A_box","pooled_at_C":"pooled_at_C_box",
           "box_at_A":"box_at_A_pooled","box_at_C":"box_at_C_pooled","diagonal":"diagonal","interaction":"interaction"}
    effects={}
    for target in ("Alder","Cedar","margin"):
        key="h" if target=="margin" else target
        effects[target]={}
        for mode in ("raw","normalized"):
            auth=a[mode+"_effects"][key]
            rev=r["analysis"]["conditional_effects"][target][mode]
            effects[target][mode]={}
            for k,v in names.items():
                one,two=auth["effects"][k],rev[v]
                eq("M3 conditional signed conclusion",one["sign"],two["sign"])
                number("M3 predicted "+mode+" effects",one["predicted"],two["predicted"],two["budget"])
                effects[target][mode][k]=dict(**number("M3 "+mode+" effects",one["value"],two["observed"],two["budget"]),
                        author_signed_zero_budget=one["zero_budget"],reviewer_signed_zero_budget=two["budget"],sign=two["sign"])
            if mode=="raw":
                number("M3 independent F",auth["independent_pooled_F"],rev["pooled_at_A_box_split"]["predicted"],rev["pooled_at_A_box"]["budget"])
                number("M3 independent B",auth["independent_box_B"],rev["box_at_A_pooled_split"]["predicted"],rev["box_at_A_pooled"]["budget"])
            else:
                for f,path in (("pooled_then_box","via_CA"),("box_then_pooled","via_AC")):
                    number("M3 normalized path sum",auth[f],rev[path]["observed"],rev["diagonal"]["budget"])
    return effects


def compare(case,a,r):
    native=a["native"]
    p=r["parity"]
    for n,m in (("read_f32le","native_read_f32le"),("top","rank"),("zero_read","zero_read"),
                ("top_score_pass","top_pass"),("top_gap_pass","gap_pass"),("gap_f32","native_gap"),("scores","scores")):
        eq(n,native[n],r[m])
    eq("native threshold decision",native["owner_thresholds_met"],r["owner_threshold_result"]["type"]!="ABSTAIN")
    eq("native32 numerator",native["scalar_f32"]["numerator"]["bytes"],r["native_numerator_f32le"])
    eq("native32 norm",native["scalar_f32"]["read_norm"]["bytes"],r["native_norm_f32le"])
    eq("event",a["discrete"]["event"],r["routing"]["event"])
    eq("incoming matrix",a["discrete"]["before_event"]["matrix_sha256"],r["routing"]["incoming_matrix_sha256"])
    eq("post-event discrete",a["discrete"]["after_event"]["discrete_sha256"],r["routing"]["discrete_sha256"])
    case["exact"]={field:p[field] for field in ("score_f32le","read_sha256","matrix_sha256","margin")}
    for field,x in case["exact"].items():
        eq(field,native[field],x)
    case["scalar_comparisons"]={}
    for n,v in (("numerator",r["checks"]["numerator"]),("read_norm",r["checks"]["norm"]),
                ("denominator",r["checks"]["denominator"]),*r["checks"]["scores"].items()):
        case["scalar_comparisons"][n]=number("prediction "+n,a["prediction"][n],v["predicted"])
    if a["arm"]=="M1":
        for x,y in (("gain_requested_f64","requested"),("gain_executed","executed"),("realized_relative","realized_rho"),
                    ("realized_absolute","realized_eta"),("donor_truth","truth"),("correct_resolved_rank","donor_correct")):
            eq(x,a[x],r[y])
        eq("signed numerator outcome",a["sign"]["sign"],r["signed_rank"])
        coordinates("M1 predicted read",a["predicted_vector"]["bytes"],r["checks"]["read"]["predicted_f64le"])
        number("affine numerator",a["executed_affine_numerator"],r["affine"]["predicted"])
    else:
        o,v=a["input_binding"],r["inputs"]
        for field,rev in (("all_pooled_rows_sha256","pooled_window_sha256"),("full_block_sha256","blocks_f32le_sha256"),
                          ("full_spans_sha256","span_records_sha256"),("box999","box_i32le")):
            eq(field,o[field],v[rev])
        eq("declaration feature",o["pooled_row"]["sha256"],v["declaration_feature_sha256"])
        eq("encoded box",o["encoded_box"]["bytes"],v["encoded_box_f32le"])
        for name,alias in (("key","k"),("value","v"),("alpha","alpha"),("beta","beta")):
            eq("projected "+name,a["projected"][name]["bytes"],v["projection_f32le"][alias])
        for field,rev in (("pooled_value","feature_projection_f64le"),("box_value","box_projection_f64le")):
            coordinates(field,a[field]["bytes"],r["m3"][rev])
        coordinates("M3 predicted read",a["fp64_predicted_read"]["bytes"],r["checks"]["read"]["predicted_f64le"])
        for n,v in (("z","z"),("value_norm","value_norm"),("denominator","denominator"),("alpha","alpha"),("beta","beta"),
                    ("effective_epsilon_in_value_units","epsilon_over_abs_t"),("epsilon_shrink_magnitude","attenuation"),
                    ("signed_multiplier_on_raw_dot","signed_scale_factor")):
            number("M3 "+n,a[n],r["m3"][v])
        eq("scale sign",a["t"]["sign"],r["m3"]["t"]["sign"])
        for k,v in a["alignments"].items():
            rr=r["m3"]["axes"]["margin" if k=="h" else k]
            for name,reval in (("pooled",rr["feature"]),("box",rr["box"]),("total",rr["raw"]["observed"]),
                               ("finite_epsilon_score",rr["normalized"]["predicted"])):
                number("M3 "+name,v[name],reval)


def main():
    output=Path(sys.argv[1])
    records=[]
    manifests={}
    for side,runtime,field in (("author","runtime.json","digest_before_runtime"),("review","run.json","evidence_sha256")):
        doc=data(side,runtime)
        assert not doc["failures"]
        manifests[side]=doc[field]
        for file,digest in doc[field].items():
            eq("evidence SHA-256",sha(raw(side,file)),digest)
    p1,p2=(data(s,"parity.json") for s in ("author","review"))
    assert len(p1)==len(p2)==len({(p["arm"],*key(p)) for p in p1})==52
    for a,r in zip(p1,p2,strict=True):
        for k in ("arm","mode","point","cell","score_f32le","read_sha256","matrix_sha256","margin"):
            eq("parity "+k,a[k],r[k])
        d={k:r[k] for k in ("arm","mode","point","cell")}
        d["parity_fp64"]={k:number("parity "+k,a[k],r[k]) for k in ("numerator","read_norm")}
        records.append(d)
    details={}; counts={}
    sources=data("review","inputs.json")["arms"]
    for arm in ("M1","M3"):
        a,r=(data(s,arm+".json") for s in ("author","review"))
        verify_packs(a)
        joined={key(x):x for x in r["rows"]}
        cases={key(x):x for x in records if x["arm"]==arm}
        assert set(cases)==set(joined)=={key(x) for x in a["rows"]}
        for x in a["rows"]:
            compare(cases[key(x)],x,joined[key(x)])
        controls=data("author",arm+"-controls.json")
        for o,v in r["controls"].items():
            aa=controls[v["archive_key"]]["native"]
            for fld in ("score_f32le","matrix_sha256","read_sha256"):
                eq("control "+fld,aa[fld],v["observed"][fld])
        b=data("author",arm+"-bindings.json")
        for owner,info in b.items():
            src=sources[arm][owner[0]]
            for k,v in (("snapshot","snapshot"),("all_rows_sha256","pooled_row_sha256"),("full_pooled_sha256","pooled_window_sha256")):
                eq("source "+k,info[k],src[v])
            eq("eventual query",info["eventual_query"]["bytes"],src["query_f32le"])
            eq("literal anchors",info["anchor"]["bytes"],src["anchor_f32le"])
        details[arm]=m1(a,r) if arm=="M1" else m3(a,r)
        counts[arm]=archive_checks(arm,a)
    obj=dict(author=AUTHOR,review=REVIEW,rows=records,effects=details,exact_comparisons=COUNTS,
             numerical_comparisons=METRICS,author_check_scalars_reaudited=counts,manifest_digests=manifests)
    with output.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(obj,f,indent=2,allow_nan=False)
        f.write("\n")
    print(len(records),sum(COUNTS.values()),sum(x["count"] for x in METRICS.values()),counts)


if __name__=="__main__":
    main()
