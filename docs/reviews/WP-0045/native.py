"""Join independently supplied Windows observations from the same protected interval."""
import hashlib
from common import BASE, HERE, OLD, read, sha, stream_inventory, worker_command
from observe import observe
from clauses import encoded, provenance


def collect(path, request, manifest, atoms):
    from common import save
    from pathlib import Path
    path.mkdir()
    save(path/"input.json",request)
    events=observe(path)
    s,w=read(path/"supervisor.json"),read(path/"worker.json")
    seal=s["seal"]["body"]
    trace=events["events"]
    starts=[e for e in trace if e["kind"]=="create"]
    ends=[e for e in trace if e["kind"]=="exit"]
    sup=next(e for e in starts if e["instance"]==events["anchor"])
    child=next(e for e in starts if e["instance"]==s["child"])
    closed=next(e for e in ends if e["pid"]==child["pid"])
    argv=worker_command(path,request["selection"])
    ordinary={"elevated":0,"integrity_rid":8192,"effective_admin":False}
    good_tokens=all(r["token"]==ordinary for r in (events,s,w))
    command_fields={"cwd":str(path), "argv":argv[4:], "orig_argv":argv,
                    "script":manifest["sources"]["worker.py"]}
    config={k:v for k,v in w["config"].items() if k not in command_fields}
    expected={k:True for k in atoms}
    got={}
    # Use omission for a missing witness. A directly measured disagreement is M.
    if sup["image"] is not None:
        got["L.image"]=sup["image"]==manifest["image"] and s["script"]==manifest["sources"]["supervisor.py"]
    if child["image"] is not None:
        got["I.image"]=child["image"]==manifest["image"]
    got["E.caller"]=(good_tokens and sup["instance"]==s["caller"] and
                     events["anchor"]==s["caller"] and s["selection"]==request["selection"] and
                     s["before"]<=s["returned"] and s["returned_process_handle"]>0 and
                     child["instance"]==s["child"] and s["tid"]==child["tid"])
    got["E.child"]=child["instance"]==s["child"]==w["instance"] and child["pid"]==s["child"][0]
    got["E.order"]=(sup["when"]<=s["before"]<=s["returned"]<=s["resumed"]<=w["start"] and
                    s["before"]<=child["instance"][1]<=s["returned"] and
                    child["when"]<=w["start"] and w["closed"]<=closed["when"]<=s["finish"] and
                    s["suspend_count"]==1 and len(starts)==len(ends)==2 and
                    all(x["code"]==0 for x in ends) and s["code"]==0)
    got["E.job"]=sup["job"] and child["job"] and events["job_flags"]==0
    got["A.command"]=(s["argv"]==argv and s["application"]==str(BASE) and
                      all(w["config"][k]==v for k,v in command_fields.items()))
    got["C.runtime"]=encoded(config)==encoded(manifest["runtime"])
    object_id=s["object_at_seal"]
    got["B.writer"]=(not s["inherited"] and w["instance"]==child["instance"] and
                     w["member"]==object_id and w["ntfs"]=="NTFS" and w["denied"]==32 and
                     w["start"]<=w["write"]<=w["transfer"]<=w["closed"]<=s["signed_at"] and
                     w["length"]==4)
    got["B.seal"]=s["authenticated"] and w["closed"]<=s["signed_at"]<=s["acquired_at"]
    got["B.protection"]=w["member"]==object_id==s["held_after"] and s["denied_after"]==32
    got["B.direct"]=got["B.protection"] and s["scored_object"]==object_id
    got["B.members"]=(seal["members"]==stream_inventory(bytes.fromhex(s["score"]))==
                      stream_inventory(bytes.fromhex(request["payload_hex"])))
    if got["B.seal"] and got["B.direct"]:
        got["B.origin"]=(seal["caller"]==sup["instance"] and seal["child"]==child["instance"]
                         and seal["object"]==s["scored_object"] and seal["nonce"]==s["nonce"]
                         and seal["selection"]==request["selection"])
    got["content.bytes"]=bytes.fromhex(s["score"])==bytes.fromhex(request["payload_hex"])
    rel=dict(expected=expected,observed=got,evidence=atoms)
    save(path/"relation.json",rel)
    # Dynamic values with IDs preserved for independent joins; omit private key and full ambient inventories.
    published=dict(observer=events,supervisor=s,worker=w)
    save(path/"public-witness.json",published)
    return provenance(rel,atoms)
