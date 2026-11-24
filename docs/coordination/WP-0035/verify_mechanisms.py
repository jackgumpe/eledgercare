"""Verify independent state and anchor witnesses and account for every common write."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess

HERE=Path(__file__).resolve().parent
MODELS=("M1","M3")
KEYS=("task","pair","binder","model","write","read","phase","step")


def require(ok, label):
    if not ok:
        raise ValueError(label)


def artifact(rev,area,path):
    data=subprocess.check_output(["git","cat-file","blob",rev+":docs/"+area+"/WP-0035/evidence/"+path])
    return json.loads(gzip.decompress(data) if path.endswith(".gz") else data)


def index(rows, fields):
    result={tuple(r[f] for f in fields):r for r in rows}
    require(len(result)==len(rows), "Duplicate keys")
    return result


def equal(left,right,fields,key):
    for a,b in fields:
        require(left[a]==right[b], (key,a,b,left[a],right[b]))


def sha_hex(raw_hex):
    return hashlib.sha256(bytes.fromhex(raw_hex)).hexdigest()


def verify(author, reviewer):
    def a(name):return artifact(author,"research",name)
    def r(name):return artifact(reviewer,"reviews",name)
    hist=json.loads((HERE.parent/"WP-0033/reconciliation.json").read_bytes())["rows"]
    ac=a("admission.json.gz")["write8"]
    rc=r("parity.json")["relative_half"]
    require(set(rc)=={x["cell"] for x in ac}=={"AA","AC","CA","CC"},"Four declaration controls")
    cross={}
    for row in ac:
        cell=row["cell"]
        control=rc[cell]
        equal(row,control,[("full_score_hex","score_hex"),("result_matrix","matrix_sha256"),("query_sha256","query_sha256"),
                           ("read_sha256","read_sha256")],cell)
        require(row["full_score_hex"]==hist["M1/relative/0.50/"+cell]["score_f32le"],cell)
        cross[cell]=control
    score_rows=index(a("scores.json.gz"),KEYS)
    other=index(r("scores.json.gz"),KEYS)
    fields=("actual_step","ptr","depth","registry","eligible","leaders","zero","scope","matrix_sha256","owner_columns_sha256","read_sha256","query_sha256")
    require(score_rows.keys()==other.keys(),"State keys")
    for key,row in score_rows.items():
        equal(row,other[key],[(k,k) for k in fields]+[("directory","candidates")],key)
    axe=index(r("anchor_geometry.json.gz"),("pair","binder","model"))
    geometry={}
    anchors=0
    for row in a("anchors.json.gz"):
        key=(row["pair"],row["binder"],row["model"])
        theirs=axe[key]["anchors"]
        require(row["choices"]==theirs["directory"] and row["raw_f32le"]==theirs["projected_hex"], key)
        for code,field in (("R0","native_sha256"),("R1","centered_sha256")):
            require(sha_hex(row["anchors_f32le"][code])==theirs[field],(key,code))
        geom={"raw_fp64_norms":row["norms"],"angle_radians":row["angle_radians"],"measured_axis_norm_ratio":row["measured_axis_gain"],
              "native_centered_axis_cosine":theirs["native_centered_axis_cos"],"centered_antipodal_max_abs":theirs["centered_antisymmetry_max"],
              "equal_norm_scaling_axis_residual":row["predicted_equal_norm_axis_residual"],
              "raw_sha256":sha_hex(row["raw_f32le"]),"native_sha256":theirs["native_sha256"],"centered_sha256":theirs["centered_sha256"]}
        model=row["model"]
        if model in geometry:require(geometry[model]==geom,("Geometry varies by binder",key))
        geometry[model]=geom
        anchors+=1
    ar=index(a("writes.json.gz"),("pair","binder","model","write"))
    rr=index(r("writes.json.gz"),("pair","binder","model","write"))
    require(ar.keys()==rr.keys(),"Write series keys")
    matched=0
    trailing=[]
    designations=[]
    parent_exposure=[]
    fields=[("step","step"),("ptr","ptr"),("depth","depth_after"),("designated","designate"),("downstream","downstream_root"),
            ("rho","rho"),("effective_alpha","retention"),("alpha","alpha"),("beta","beta"),("alpha_beta","alpha_beta")]
    for key,record in ar.items():
        left=record["updates"]
        right=rr[key]["observations"]
        require(len(right)<=len(left),("Expected common prefix",key))
        for x,y in zip(left,right):
            equal(x,y,fields,(key,x["step"]))
            require(x["events"]==[e["kind"] for e in y["events"]], (key,x["step"],"events"))
            matched+=1
        extra=left[len(right):]
        if extra:
            require(record["task"]=="B" and all(x["after_target"] for x in extra) and "TARGET" in extra[0]["events"],
                    ("Unexpected extra writes",key))
            trailing.append({"pair":key[0],"binder":key[1],"model":key[2],"write":key[3],"count":len(extra),
                             "first_step":extra[0]["step"],"last_step":extra[-1]["step"]})
        if record["model"]=="M1" and record["write"]=="W1":
            tagged=[{"step":x["step"],"ptr":x["ptr"],"literal":x["span_text"]} for x in left if x["designated"]]
            require(len(tagged)<=1,("Repeat designation",key))
            designations.append({"task":record["task"],"pair":key[0],"binder":key[1],"horizon":record["horizon"],"designations":tagged})
        if record["task"]=="A" and record["write"]=="W0":
            downstream=[x for x in left if x["downstream"] and not x["after_target"]]
            parent_exposure.append({"model":key[2],"pair":key[0],"binder":key[1],"horizon":record["horizon"],
                                    "eligible_parent_writes":len(downstream),
                                    "retention_product":math.prod(x["alpha"] for x in downstream),
                                    "alpha_beta_above_one":sum(x["alpha_beta"]>1 for x in downstream),
                                    "min_alpha_beta":min(x["alpha_beta"] for x in downstream),"max_alpha_beta":max(x["alpha_beta"] for x in downstream),
                                    "writes_9_to_12":[{k:x[k] for k in ("step","alpha","beta","alpha_beta")} for x in downstream if 9<=x["step"]<=12]})
    return {"author":author,"reviewer":reviewer,"checked_state_and_directory_rows":len(score_rows),"state_fields":fields_description(),
            "observed_anchors_checked":anchors,"geometry":geometry,"write8_controls":cross,"common_write_events":matched,
            "author_after_read_only_writes":sum(row["count"] for row in trailing),"after_read_breakdown":trailing,
            "declarations":designations,"task_A_downstream_native":parent_exposure}


def fields_description():
    return ["actual step","source pointer","controller depth/scope","registry and eligible directory","leaders and zero-read flag",
            "full matrix, owner columns, read and target query SHA-256"]


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("author");cli.add_argument("reviewer");cli.add_argument("output",type=Path)
    args=cli.parse_args()
    result=verify(args.author,args.reviewer)
    with args.output.open("x",encoding="utf8",newline="\n") as out:
        json.dump(result,out,indent=2,allow_nan=False)
        out.write("\n")
    print(result["checked_state_and_directory_rows"],"state rows;",result["common_write_events"],"common writes;",
          result["author_after_read_only_writes"],"trailing writes")
