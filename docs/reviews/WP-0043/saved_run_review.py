"""Independent, read-only examination of a completed or stopped private native run."""
from collections import Counter, defaultdict
from hashlib import sha256
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys


ARCH = "f5e68668a5999a12ba399eb0f5103ffa835e4b30"
HIST = "docs/coordination/WP-0005/gpu-reviewer-release/author-run-snapshot/evidence/"
ARMS = ("untouched","observed")
CALLS = ("F01.warmup","F07.warmup","F01.warm1","F07.warm1")
PHASES = ("C0_raw","C1_post_rep","C2_post_page")


def arch(name):
    return subprocess.check_output(["git","show",f"{ARCH}:{HIST}{name}"])


def load(path):
    return json.loads(path.read_bytes()) if path.is_file() else {}


def signature(path):
    with path.open("rb") as src:
        return hashlib.file_digest(src,"sha256").hexdigest()


def mismatch(a,b):
    return next((j for j,p in enumerate(zip(a,b)) if p[0]!=p[1]),min(len(a),len(b)) if len(a)!=len(b) else None)


def main(root):
    done=load(root/"outcome.json")
    if done.get("status") not in ("partial","finished"):
        raise ValueError("completed or stopped run required")
    files={p.relative_to(root).as_posix():p for p in root.rglob("*") if p.is_file()}
    promised=done.get("files",{})
    r={"status":done["status"],"reason":done.get("reason"),"outcome_sha256":signature(root/"outcome.json"),
       "total_bytes":sum(p.stat().st_size for p in files.values()),"files":len(files),
       "manifest_entries":len(promised),"manifest_absent":sorted(set(promised)-files.keys()),
       "manifest_omitted":sorted(files.keys()-{"outcome.json"}-set(promised)),
       "manifest_byte_mismatches":[k for k,v in promised.items() if k in files and signature(files[k])!=v],
       "admission_present":(root/"admission.json").is_file(),"arms":{},"rows":{}}
    live={}
    historical={}
    for label in CALLS:
        ids=json.loads(arch(label+".token_ids.json"))
        obs=json.loads(arch(label+".observation.json"))
        historical[label]=(ids,arch(label+".raw.txt"),obs)
    for arm in ARMS:
        a={}
        r["arms"][arm]=a
        a["runtime_pid"]=load(root/arm/"runtime.json").get("pid")
        log=root/arm/"stderr.log"
        a["stderr_tail"]=log.read_bytes()[-3000:].decode("utf8",errors="replace").splitlines()[-10:] if log.exists() else []
        tm=root/arm/"phase"
        a["timing_marks"]=[]
        a["last_progress"]=None
        if tm.exists():
            for line in tm.read_bytes().splitlines():
                try:
                    ns,name,tokens=json.loads(line)
                except (ValueError,TypeError):
                    a["timing_marks"].append("incomplete")
                    break
                if tokens==0:
                    a["timing_marks"].append(name)
                else:
                    a["last_progress"]=[name,tokens]
        a["docs"]={}
        for label in CALLS:
            item=load(root/arm/(label+".json"))
            if not item:
                continue
            doc=item["document"]
            live[arm,label]=doc
            ids,text,obs=historical[label]
            n=obs["native"]
            d={k:doc.get(k)==n[s] for k,s in (("terminal","finish_reason"),("output_tokens","output_tokens"),
                        ("num_pages_out","num_pages_out"),("expected_pages","expected_pages"),("prompt","prompt"))}
            d.update(first_id=mismatch(ids,doc["ids"]),first_utf8=mismatch(text,doc["text"].encode()),
                     ids=len(doc["ids"]),bytes=len(doc["text"].encode()),kwargs_equal=item["kwargs"]==obs["call_kwargs"],
                     markers_equal=doc["markers"]==obs["page_markers"]["marker_token_positions"],
                     prompt_tokens=len(doc.get("prompt_token_ids",[])),expected_prompt_tokens=n["prompt_len"])
            a["docs"][label]=d
    r["paired_docs_exact"]={l:live["untouched",l]==live["observed",l] for l in CALLS
                            if ("untouched",l) in live and ("observed",l) in live}
    journal=root/"observed/observations.jsonl"
    tags=Counter()
    errors=[]
    appends=[]
    rows=defaultdict(dict)
    if journal.exists():
        with journal.open("rb") as stream:
            for serial,line in enumerate(stream,1):
                try:
                    x=json.loads(line)
                except ValueError:
                    errors.append({"journal_seq":serial,"event":"incomplete_json"})
                    continue
                tag,row,data=x["tag"],x["row"],x["data"]
                tags[tag]+=1
                if x["journal_seq"]!=serial:
                    errors.append({"serial":serial,"event":"serial_mismatch"})
                if tag=="append":
                    appends.append([data["index"],data["id"],data["pos"]])
                if row is not None and (tag in PHASES or tag in ("B","D")):
                    rows[row][tag]=data
    ids=historical[CALLS[-1]][0]
    r["observed_append_count"]=len(appends)
    r["first_wrong_retained_append"]=next((j for j,p in enumerate(appends) if j>=len(ids) or p!=[j,ids[j],827+j]),None)
    r["journal_tag_counts"]=dict(sorted(tags.items()))
    r["journal_errors"]=errors
    for i in range(5):
        x=rows[i]
        row={"phase_present":[tag for tag in ("B",*PHASES,"D") if tag in x]}
        r["rows"][i]=row
        for k in ("B","D"):
            if k in x:
                row[k]={"history_len":len(x[k].get("history",[])),"position":x[k].get("pos"),"y":x[k].get("y")}
        words={}
        for tag in PHASES:
            if tag in x:
                raw=bytes.fromhex(x[tag]["record"]["hex"])
                row[tag]={"length":len(raw),"sha256":sha256(raw).hexdigest(),"word1_le":raw[4:8].hex()}
                words[tag]=raw
        if all(len(words.get(t,b""))==129280*4 for t in PHASES):
            raw,post,final=(words[t] for t in PHASES)
            c0=list(struct.iter_unpack("<f",raw))
            c2=[v for v, in struct.iter_unpack("<f",final)]
            maxval=max(c2)
            row.update(raw_nonfinite=sum(not math.isfinite(a[0]) for a in c0),raw_vs_repeat=mismatch(raw,post),
                       expected_page_vs_final=mismatch(post[:4]+bytes.fromhex("000080ff")+post[8:],final),
                       raw_vs_final_first_dense_byte=mismatch(raw,final),
                       final_firstmax=next((j for j,v in enumerate(c2) if v==maxval),None),
                       historical_emission=ids[619+i])
    print(json.dumps(r,indent=2,allow_nan=False))


if __name__=="__main__":
    main(Path(sys.argv[1]))
