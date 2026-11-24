"""Compare pinned pre-existing tables. No model execution or new native read."""
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = "be72e777178fe627f355ad240598c14217e267e8"
AUTHOR = "f17396bf4d3915b53cff0e22a37e1b928cdf2919"
DATA = "8f31cc66c4878ca086fa5da1498c4a73ed6a6306"
AUTH = "docs/research/WP-0032/evidence/"
RV = "docs/reviews/WP-0032/evidence/"
NAMES = ("Alder","Cedar")
RECORDS = []
BYTES = []


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT)


def blob(rev, path):
    return git("cat-file","blob",rev+":"+path)


def obj(rev, path):
    return json.loads(blob(rev,path))


def digest(b):
    return hashlib.sha256(b).hexdigest()


def budget(x,y):
    return 2e-5*(1+max(abs(x),abs(y)))


def equal(cell, quantity, a, b):
    assert a == b, (cell,quantity,a,b)
    BYTES.append([cell,quantity])


def gate(cell,q,ref,rebuilt,limit=None):
    limit = budget(ref,rebuilt) if limit is None else limit
    residual = abs(rebuilt-ref)
    assert math.isfinite(residual) and residual <= limit,(cell,q,ref,rebuilt,limit)
    RECORDS.append(dict(cell=cell,quantity=q,reference=ref,author=rebuilt,absolute=residual,
                        limit=limit,fraction=residual/limit))


def nums(hexstring,code):
    raw = bytes.fromhex(hexstring)
    return struct.unpack(f"<{len(raw)//struct.calcsize(code)}{code}",raw)


def dots(x,y):
    return math.fsum(a*b for a,b in zip(x,y,strict=True))


def each_vec(cell, label, ref, record):
    assert record["shape"] == [len(ref)] and record["dtype_le"] == "torch.float64"
    assert digest(bytes.fromhex(record["bytes_le"])) == record["sha256"]
    for j,(a,b) in enumerate(zip(ref,nums(record["bytes_le"],"d"),strict=True)):
        gate(cell,f"{label}[{j}]",a,b)


def mapped(metrics,name):
    return metrics["scores"][{"alder_score":"Alder","cedar_score":"Cedar"}[name]] if name.endswith("_score") else metrics[name]


def original_inputs(pinned, owner):
    source = pinned["sources"][owner]
    q = nums(source["frozen_query_f32le"],"f")[:32]
    denom = math.sqrt(dots(q,q)) + 1e-8
    anchors = nums(source["ordered_anchors_f32le"],"f")
    return [x/denom for x in q], (anchors[:128],anchors[128:])


def compare_cell(arm,label,row,auth,pinned):
    cell = f"{arm}/{label}"
    rb,ab = row["binding"],auth["binding"]
    equal(cell,"native_ordered_scores",rb["score_f32le"],ab["native_score_f32le"])
    for k in ("archived_score_f32le","independent_archived_score_f32le","closure_score_f32le"):
        equal(cell,k,rb["score_f32le"],ab[k])
    equal(cell,"native_read",rb["native_read_f32le"],auth["native_read"]["bytes_le"])
    for k,v in (("query_sha256","query_sha256"),("anchor_sha256","ordered_anchor_sha256"),
                ("updated_sha256","matrix_sha256"),("native_read_sha256","read_sha256")):
        equal(cell,k,rb[k],ab["updated"][v])
    for k,v in (("discrete_sha256","discrete_sha256"),("recipient_sha256","matrix_sha256")):
        equal(cell,k,rb[k],ab["recipient_before"][v])
    for k,v in (("donor_projection_sha256","donor_projection_sha256"),("donor_bundle_sha256","bundle_sha256")):
        equal(cell,k,rb[k],ab[v])
    src = pinned["sources"][rb["donor"]]
    projection = src["donor"]["projected_f32le"]
    for k in ("key","value","alpha","beta"):
        equal(cell,k,projection[k],ab["projected_f32le"][k])
    for k,v in (("alpha","alpha"),("beta","beta"),("z","owner_key_dot"),("scale","beta_times_owner_key_dot")):
        gate(cell,k,row[k],auth[v])
    u,anchors = original_inputs(pinned,rb["control_from"])
    each_vec(cell,"owner_query_direction",u,auth["u"])
    assert (rb["recipient"],rb["donor"],rb["control_from"],rb["shape"]) == (
        ab["recipient"],ab["donor"],ab["discrete_from"],ab["matrix_shape"])
    native = nums(rb["native_read_f32le"],"f")

    for field in ("norm","denominator","numerator","margin","alder_score","cedar_score"):
        equal(cell,"native_fp32_"+field,mapped(row["native32"],field),auth["native_fp32"][field])
    if arm == "M1":
        vecs = {}
        for key,part in row["components"].items():
            va = auth["terms"][key]
            vecs[key] = nums(part["vector_f64le"],"d")
            each_vec(cell,"term_"+key,vecs[key],va["vector"])
            for f,af in (("norm","norm"),("numerator","numerator"),
                         ("common_denominator_contribution","numerator_over_common_native_denominator"),
                         ("fp32_denominator_contribution","numerator_over_native_fp32_denominator")):
                gate(cell,key+"_"+f,part[f],va[af])
        gate(cell,"common_den",row["native"]["denominator"],auth["common_native_read_denominator_fp64"])
        omitted = [a+v for a,v in zip(vecs["R"],vecs["V"],strict=True)]
        restored = [a+e for a,e in zip(omitted,vecs["E"],strict=True)]
        each_vec(cell,"omitted",omitted,auth["omitted"]["read"])
        stages = [("omitted",omitted),("restored",restored)]
        for f in ("numerator","margin"):
            r,o = row["restored"][f],row["omitted"][f]
            ar,ao = auth["restored"]["metrics"][f],auth["omitted"]["metrics"][f]
            gate(cell,"restored_minus_omitted_"+f,r-o,auth["restored_minus_omitted"][f],budget(r,ar)+budget(o,ao))
    else:
        value = nums(projection["value"],"f")
        each_vec(cell,"value",value,auth["value"]["vector"])
        assert auth["gain_sign"]["sign"] == "positive" and row["scale"] > budget(row["scale"],row["scale"])
        gate(cell,"value_norm",row["value_norm"],auth["value"]["norm"])
        gate(cell,"epsilon_factor",row["finite_epsilon_multiplier"],auth["value"]["finite_epsilon_factor"])
        gate(cell,"effective_norm",row["factorized_read_norm"],auth["restored"]["metrics"]["norm"])
        gate(cell,"effective_denominator",row["factorized_denominator"],auth["restored"]["metrics"]["denominator"])
        for owner,ai in row["alignments"].items():
            b = auth["value"]["alignment"][owner]
            for k,v in (("raw_dot","raw_dot"),("anchor_norm","anchor_norm"),("cosine","cosine"),
                        ("recovered_score","recovered_score_via_value"),("value_direction_dot","dot_with_unit_value"),
                        ("eps_normalized_value_dot","dot_with_epsilon_normalized_value")):
                gate(cell,owner+"_"+k,ai[k],b[v])
            gate(cell,owner+"_epsilon_effect",ai["recovered_score"]-ai["value_direction_dot"],b["finite_epsilon_score_change"])
        restored = [row["scale"]*vi for vi in value]
        stages = [("restored",restored)]
    each_vec(cell,"restored",restored,auth["restored"]["read"])
    for stage,vec in [("native",native),*stages]:
        metrics = auth["fp64_on_promoted_native_read"] if stage=="native" else auth[stage]["metrics"]
        for field in ("norm","denominator","numerator","margin","alder_score","cedar_score"):
            gate(cell,stage+"_"+field,mapped(row[stage],field),metrics[field])
        for name,anchor in zip(NAMES,anchors,strict=True):
            f = name.lower()+"_numerator"
            gate(cell,stage+"_"+f,dots(vec,anchor),metrics[f])
        if stage != "native":
            gate(cell,stage+"_hmargin",row[stage]["margin"],auth[stage]["h_margin"])


def compare_contrasts(arm,theirs,own,rows):
    for pre,entry in theirs["alder_donor_minus_cedar_donor"].items():
        cell = arm+"/"+pre
        theirs_a,theirs_c = (theirs["cells"][pre+d] for d in "AC")
        ours_a,ours_c = (rows[pre+d] for d in "AC")
        merged = own[cell]
        for prop,key in (("alder_score","Alder"),("cedar_score","Cedar"),("margin","margin"),("numerator","numerator")):
            sr = entry[prop]
            allowances = {}
            for stage in ("omitted","restored"):
                if stage not in sr:
                    continue
                oo = merged[stage][key]["value"]
                f = sr[stage]["value"]
                ab,cb = (budget(mapped(ours[stage],prop),theirs_[stage]["metrics"][prop])
                         for ours,theirs_ in ((ours_a,theirs_a),(ours_c,theirs_c)))
                allowances[stage]=ab+cb
                gate(cell,"donor_"+stage+"_"+key,oo,f,ab+cb)
                assert abs(oo)>ab+cb and sr[stage]["sign"] == ("positive" if oo>0 else "negative")
            if "restored_minus_omitted" in sr:
                gate(cell,"donor_effect_"+key,merged["restored_minus_omitted"][key]["value"],
                     sr["restored_minus_omitted"]["value"],sum(allowances.values()))
            ours_native = mapped(ours_a["native32"],prop)-mapped(ours_c["native32"],prop)
            equal(cell,"original_donor_"+key,ours_native,sr["native"])
        for name in NAMES:
            prop = name.lower()+"_numerator"
            # Independently derive candidate numerators from our restored FP64 scores and denominators.
            a,c = (r["restored"]["scores"][name]*r["restored"]["denominator"] for r in (ours_a,ours_c))
            aa,cc = (r["restored"]["metrics"][prop] for r in (theirs_a,theirs_c))
            gate(cell,"donor_restored_"+prop,a-c,entry[prop]["restored"]["value"],budget(a,aa)+budget(c,cc))


def recheck_author_gates(gates, tables):
    count=0
    for group,items in gates["groups"].items():
        for i in items:
            a,b = i["reference"],i["reconstructed"]
            if "_donor_" in group:
                arm,tags = i["at"].split("/")
                prop=group.split("_donor_")[1]
                cells=[tables[arm]["cells"][k] for k in tags.split("-")]
                limit=sum(budget(r["native_fp32"][prop],r["restored"]["metrics"][prop]) for r in cells)
            else:
                limit=budget(a,b)
            assert i["limit"]==limit and i["residual"]==b-a
            assert i["fraction_of_limit"]==abs(b-a)/limit and abs(b-a)<=limit and i["pass"]
            count+=1
        summary=gates["maxima"][group]
        assert summary["failed"]==0 and summary["scalars"]==len(items)
        assert summary["max_absolute_residual"]==max(items,key=lambda r:abs(r["residual"]))
        assert summary["max_fraction_of_limit"]==max(items,key=lambda r:r["fraction_of_limit"])
    return count


def main(author_data,candidate):
    assert Path.cwd().resolve()==ROOT and git("rev-parse","HEAD").decode().strip()==candidate
    assert git("merge-base",author_data,AUTHOR).decode().strip()==AUTHOR and git("merge-base",candidate,OWN).decode().strip()==OWN
    assert Path(__file__).read_bytes().replace(b"\r\n",b"\n")==blob(candidate,"docs/reviews/WP-0032/compare.py")
    own=obj(OWN,RV+"tables.json")
    tables={}
    runtime=obj(author_data,AUTH+"runtime.json")
    assert runtime["candidate"]==AUTHOR and runtime["status"]=="passed" and runtime["threads_intra_inter"]==[1,1]
    for path,h in runtime["evidence_sha256"].items():
        assert digest(blob(author_data,AUTH+path))==h
    for arm,tags in (("M1",("AA","AC","CA","CC")),("M3",("0A","0C"))):
        t=tables[arm]=obj(author_data,AUTH+arm+".json")
        ours=own["cells"][arm]
        assert t["literal_order"]==list(NAMES) and t["thresholds"]==[1.,.1] and list(t["cells"])==list(ours)==list(tags)
        old=obj(DATA,"docs/research/WP-0031/evidence/"+arm+".json")
        for k in tags:
            compare_cell(arm,k,ours[k],t["cells"][k],old)
        compare_contrasts(arm,t,own["donor_Alder_minus_Cedar"],ours)
    count=recheck_author_gates(obj(author_data,AUTH+"gates.json"),tables)
    groups={}
    for r in RECORDS:
        cat=r["quantity"].split("[")[0]
        entry=groups.setdefault(cat,dict(count=0,max_absolute=r,max_fraction=r))
        entry["count"]+=1
        for key,field in (("max_absolute","absolute"),("max_fraction","fraction")):
            if r[field]>entry[key][field]:
                entry[key]=r
    result=dict(agreement=True,author_source=AUTHOR,author_evidence=author_data,review_evidence=OWN,
                comparison_source=candidate,scalar_comparisons=len(RECORDS),exact_checks=len(BYTES),
                evaluated_author_gates=count,largest_cross_residual=max(RECORDS,key=lambda r:r["absolute"]),
                largest_cross_fraction=max(RECORDS,key=lambda r:r["fraction"]),quantities=groups,exact=BYTES)
    out=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0032/review")/candidate
    out.mkdir(exist_ok=False)
    (out/"comparison.json").write_bytes((json.dumps(result,indent=2,allow_nan=False)+"\n").encode())
    print(len(RECORDS),len(BYTES),count,result["largest_cross_residual"])


if __name__=="__main__":
    main(*sys.argv[1:])
