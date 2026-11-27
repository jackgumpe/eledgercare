"""Offline, read-only audit. Git-archive the pinned fixture, direct and edition trees as in report."""
import hashlib
import hmac
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from common import HOME, BASE, read, save, sha
from expect import compare, predicted

WORK=HOME/"opened"
PUBLIC=HERE/"blind"
AUTH=WORK/"author"/"docs"/"research"/"WP-0045"
ED=WORK/"edition"/"docs"/"editions"/"WP-0045"
FIX=WORK/"fixture"/"docs"/"fixtures"/"WP-0045"
EX=HOME.parent/"eld-fixture-claude"/"oracle"
RAW=HOME.parent/"eld-owner-probe"/"decisive-01"
MED={"elevated":0,"integrity_rid":8192,"effective_admin":False}
IMAGE="4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
OUTPUT=HERE/"opening"
canonical=lambda x:json.dumps(x,sort_keys=True,allow_nan=False,separators=(",",":"))
digest=lambda x:hashlib.sha256(x).hexdigest()


def frozen_map(files,root):
    for filename,expected in files.items():
        assert sha(root/filename)==expected,(filename,expected)
    return len(files)


def mac(root, body, result):
    actual=hmac.digest((root/"key.bin").read_bytes(),canonical(body).encode(),"sha256").hex()
    assert hmac.compare_digest(result,actual)


def author_native(j):
    arm=RAW/f"arm-{j}"
    raw_count=frozen_map(read(arm/"raw-commitments.json"),arm)
    outer,child,s,w,mid,end,sc=[read(arm/(f+".json")) for f in
            ["supervisor-call","child-call","supervisor","worker","supervisor-held","scorer-held","scorer"]]
    manifest=read(AUTH/"manifest.json")
    for c,role,m in [(outer,"supervisor",s),(child,"worker",w)]:
        recorded=c["image"]
        assert c["returned_instance"]==recorded["event_instance"]==m["instance"]
        assert c["child_pid"]==recorded["event_pid"] and c["child_tid"]==recorded["event_tid"]
        assert recorded["returned_same_object"] and recorded["event_file"]
        assert recorded["sha256"]==IMAGE and Path(recorded["image_path"])==BASE
        assert recorded["object"]==sc["initial_image_object"] and recorded["member"]
        assert c["caller"]==c["caller_after"] and c["caller_tid"]==c["caller_tid_after"]
        assert Path(c["application"])==BASE and c["argv"][-2:]==[role,str(j)] and not c["inherit_handles"]
        assert c["call"]<=c["returned"]<=c["assigned"]<=c["resumed"]<=recorded["at"]<=c["creation_continue"]
        assert c["creation_continue"]<=m["snapshot"]["command_start"]<=m["snapshot"]["cut"]<=c["exit"][1]
        assert c["exit"][0]==0 and c["policy"]==0x2000
        assert m["token"]==MED
        for cut in ["command","runtime"]:
            assert m["snapshot"][cut]==manifest["roles"][role+str(j)][cut]
    assert sc["outer_token"]==MED
    assert outer["returned_instance"]==child["caller"]==s["instance"]
    assert sc["script_hashes"]==manifest["source"] and all(sha(AUTH/k)==v for k,v in sc["script_hashes"].items())
    assert s["snapshot"]["cut"]<=child["call"] and w["snapshot"]["cut"]<=w["created"]<=w["written"]<=w["duplicated"]<w["closed"]<mid["at"]<child["exit"][1]<s["signed"]
    assert s["signed"]<=end["at"]<=sc["verified"]<=sc["direct"]["at"]<outer["exit"][1]
    assert w["requested_access"]==0xc0000000 and w["share"]==1 and w["disposition"]==1 and not w["inherit"]
    assert w["duplicated_access"]==mid["desired"]==end["desired"]==0x80000000
    obj=w["created_object"]
    assert all(x==obj for x in (w["view_object"],mid["object"],s["view_object"],s["receipt"]["object"],
                                end["object"],sc["guard_id"],sc["direct"]["object"]))
    data=(arm/"members"/"original.bin").read_bytes()
    assert list(p.name for p in (arm/"members").iterdir())==["original.bin"]
    assert s["receipt"]["selection"]==j and s["receipt"]["supervisor"]==s["instance"] and s["receipt"]["child"]==w["instance"]
    assert sc["members"]==s["receipt"]["members"]==[dict(name="original.bin",sha256=digest(data),size=4)]
    assert w["writes"]==[dict(object=obj,size=4,bytes=data.hex())] and data==b"F07\n"
    assert sc["direct"]["bytes"]==data.hex() and sc["direct"]["eof"] and sc["direct"]["filesystem"]=="NTFS"
    mac(arm,s["receipt"],s["mac"])
    assert sc["authentic"]
    return dict(raw_files=raw_count,original_sha256=digest(data),object=obj,creator=s["instance"],
                child=w["instance"],outer_job_processes=outer["job_total_processes"],
                case_seconds=(outer["exit"][1]-outer["call"])/1e9)


def reviewer_native(j):
    arm=HOME/"decisive01"/f"native-{j}"
    s,w,o=[read(arm/(f+".json")) for f in ["supervisor","worker","events"]]
    assert read(PUBLIC/f"native-{j}.json")==dict(supervisor=s,worker=w,observer=o)
    first,second=[e for e in o["events"] if e["kind"]=="create"]
    assert first["instance"]==s["caller"]==o["anchor"] and second["instance"]==s["child"]==w["instance"]
    assert s["tid"]==second["tid"] and s["returned_process_handle"] and s["suspend_count"]==1
    assert s["before"]<=second["instance"][1]<=s["returned"]<=s["resumed"]<=w["start"]<=w["write"]<=w["transfer"]<=w["closed"]<=s["finish"]<=s["signed_at"]<=s["acquired_at"]
    assert all(e["image"]["sha256"]==IMAGE and e["image"]==read(HERE/"manifest.json")["image"] and e["job"] for e in (first,second))
    assert len(o["events"])==4 and all(e["code"]==0 for e in o["events"] if e["kind"]=="exit")
    assert all(msg["token"]==MED for msg in (s,o,w))
    assert w["ntfs"]=="NTFS" and w["denied"]==s["denied_after"]==32 and not s["inherited"]
    obj=w["member"]
    seal=s["seal"]["body"]
    assert all(x==obj for x in (s["object_at_seal"],s["scored_object"],s["held_after"],seal["object"]))
    assert seal["selection"]==s["selection"]==j and seal["caller"]==s["caller"] and seal["child"]==s["child"]
    data=(arm/"original.bin").read_bytes()
    assert s["score"]==data.hex() and data==b"F07\n" and w["length"]==4
    assert seal["members"]==[dict(name="original.bin",sha256=digest(data),length=4)]
    assert w["config"]["cwd"]==str(arm) and w["config"]["orig_argv"]==s["argv"]
    command={"argv","script","orig_argv","cwd"}
    assert {k:v for k,v in w["config"].items() if k not in command}==read(HERE/"manifest.json")["runtime"]
    mac(arm,seal,s["seal"]["tag"])
    return dict(object=obj,creator=s["caller"],child=s["child"],original_sha256=digest(data),
                event_processes=len([e for e in o["events"] if e["kind"]=="create"]),
                case_seconds=(max(e["when"] for e in o["events"])-first["when"])/1e7)


def main():
    fixture=read(FIX/"manifest.json")
    sealed=read(FIX/"oracle-commitment.json")
    for k,meta in sealed["sealed_files"].items():
        p=EX/k
        assert p.stat().st_size==meta["bytes"] and sha(p)==meta["sha256"]
    assert sha(FIX/"manifest.json")==sealed["fixture_manifest"]["sha256"]
    expected_manifest=read(EX/"expected-manifest.json")
    assert (WORK/"oracle-rerun"/"expected-manifest.json").read_bytes()==(EX/"expected-manifest.json").read_bytes()
    expected,digests,own={}, {}, {}
    routes={"direct": (read(AUTH/"results.json"),read(AUTH/"input-sha256.json")),
            "edition":(read(ED/"evidence/blind/returns.json"),read(ED/"evidence/blind/input-sha256.json")),
            "reviewer":(read(PUBLIC/"rows.json"),read(PUBLIC/"input-sha256.json"))}
    assert not set(routes["direct"][0])&set(routes["edition"][0])
    author_rows=routes["direct"][0]|routes["edition"][0]
    author_dig=routes["direct"][1]|routes["edition"][1]
    replay_counts={"direct_finite":0,"edition_finite":0,"reviewer_finite":0}
    for row in fixture["rows"]:
        case,meta=row["id"],row["input"]
        staged=HOME/"blind"/(case+".json")
        raw=(FIX/meta["path"]).read_bytes()
        assert raw==staged.read_bytes() and sha(staged)==meta["sha256"] and len(raw)==meta["bytes"]
        expected_meta=expected_manifest["rows"][case]
        want=EX/expected_meta["path"]
        assert want.read_bytes()==(WORK/"oracle-rerun"/expected_meta["path"]).read_bytes()
        assert sha(want)==expected_meta["sha256"] and want.stat().st_size==expected_meta["bytes"]
        expected[case]=read(want)
        digests[case]=meta["sha256"]
        own[case]=predicted(case,json.loads(raw))
        if row["family"]=="Q1.live":
            continue
        if case in routes["direct"][0]:
            peer=[str(AUTH/"run.py"),"record",str(staged)]
            replay_counts["direct_finite"]+=1
        else:
            peer=[str(ED/"clauses.py")]
            replay_counts["edition_finite"]+=1
        for args, expected_result in ((peer,author_rows[case]),([str(HERE/"route.py"),"evaluate"],routes["reviewer"][0][case])):
            got=json.loads(subprocess.check_output([str(BASE),"-I","-B",*args],input=raw,timeout=5))
            assert canonical(got)==canonical(expected_result),case
        replay_counts["reviewer_finite"]+=1
    results={k:compare(expected,r,digests,h) for k,r,h in [
                ("combined_disjoint_authors",author_rows,author_dig),("reviewer",*routes["reviewer"]),
                ("reviewer_preexposure_reference",own,digests)]}
    save(OUTPUT/"comparison.json",results)
    a=[author_native(i) for i in (0,1)]
    b=[reviewer_native(i) for i in (0,1)]
    for group in (a,b):
        assert all(group[0][k]!=group[1][k] for k in ("object","creator","child"))
    af=frozen_map(read(RAW/"private-commitments.json"),RAW)
    bf=frozen_map(read(HOME/"decisive01"/"archive.json")["files"],HOME/"decisive01")
    save(OUTPUT/"audit.json",dict(author=a,reviewer=b,committed_files_verified=[af,bf],
            replay_counts=replay_counts,historical=read(WORK/"historical"/"historical.json"),
            expected_manifest_sha256=sha(EX/"expected-manifest.json"),input_digests=digests))
    print("per-method complete rows", {role:sum(v["input_digest"] and v["full_row"] for v in entries.values())
                                      for role,entries in results.items()})
    print("native file commitments",af,bf,"offline entry returns",replay_counts)


if __name__=="__main__":
    main()
