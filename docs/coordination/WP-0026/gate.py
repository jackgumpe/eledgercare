"""Record a development entry decision against exact non-author evidence and primary bytes."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def evidence(path, rev):
    raw = subprocess.check_output(["git","-C",ROOT,"show",rev+":"+path.relative_to(ROOT).as_posix()])
    if raw != path.read_bytes():
        raise ValueError("Coordinator tree differs from evidence at "+rev)
    return {"path":path.relative_to(ROOT).as_posix(),"sha256":sha(path),"revision":rev}


def verify_primary(path, rev):
    proof = evidence(path,rev)
    inv = read(path)
    n = 0
    for name, summary in inv["parts"].items():
        archive = path.parent/name
        if sha(archive) != summary["sha256"]:
            raise ValueError("Primary archive digest")
        with ZipFile(archive) as z:
            keys = [k for k,v in inv["members"].items() if v["part"]==name]
            if sorted(z.namelist()) != sorted(keys):
                raise ValueError("Primary member set")
            for k in keys:
                raw = z.read(k)
                row = inv["members"][k]
                if len(raw) != row["bytes"] or sha256(raw).hexdigest() != row["sha256"]:
                    raise ValueError("Changed primary member "+k)
            n += len(keys)
    if n != len(inv["members"]) or inv["input_discrepancies"]:
        raise ValueError("Primary inventory or input discrepancy")
    return {**proof,"members":n,"parts":inv["parts"]}


def adjudicate(phase,release_path,report_path,runtime_path,inventory,review):
    release = read(release_path)
    report, runtime = read(report_path),read(runtime_path)
    digest = sha(release_path)
    result = {"stage":phase,"release_sha256":digest,"candidate":release["review_worktree_head"],
              "independent_evidence":evidence(report_path,review),"independent_runtime":evidence(runtime_path,review),
              "primary":verify_primary(inventory,review),"h0_accepted":False}
    if (release["operator"]!="eld-rd-reviewer" or report["candidate"]!=release["review_worktree_head"]
            or runtime["candidate"]!=report["candidate"] or runtime["release_sha256"]!=digest
            or read(inventory)["release_sha256"]!=digest):
        raise ValueError("Admission and return are from different releases")
    if phase=="h0":
        direct=[]
        for i in range(8):
            pairs=[]
            for order in release["orders"]:
                p=read(Path(order["plan"]))
                c=p["calls"][i]
                f=Path(p["output"])/"sensor"/c["tag"]/"through-eos.u32le"
                pairs.append((c, f.read_bytes()))
            (a,one),(b,two)=pairs
            if a["mode"]==b["mode"] or a["binder"]!=b["binder"] or a["window"]!=b["window"] or a["pages"]!=b["pages"]:
                raise ValueError("Unmatched H0 pair")
            direct.append(one==two)
        if report["release_sha256"]!=digest or sum(direct)!=report["streams_equal"]:
            raise ValueError("Independent and primary token comparisons disagree")
        all_ok=(report["gate"]=="PASS" and runtime["clean_return"] and all(direct)
                and report["unique_physical_witnesses"]=={"S":10,"H":10})
        result.update(h0_accepted=all_ok, exact_pairs=sum(direct), total_pairs=8, first_scored_equal=direct[0],
                      unique_witnesses=report["unique_physical_witnesses"],pools_reconstructed=report["pooled_vectors_reconstructed"],
                      consumed_positions_verified=report["consumed_positions_verified"])
    else:
        previous=read(HERE/"h0-gate.json")
        if not previous["h0_accepted"] or len(release["orders"])!=1:
            raise ValueError("Unqualified H0 or ambiguous C1 order")
        order=release["orders"][0]
        plan=read(Path(order["plan"]))
        if sha(Path(order["plan"]))!=report["plan_sha256"] or len(plan["calls"])!=28 or len(report["duplicates"])!=12:
            raise ValueError("C1 binding")
        eq = [all(value is True for value in pair["equal"].values()) for pair in report["duplicates"]]
        all_ok=(report["gate"]=="PASS" and runtime["clean_return"] and all(eq) and not report["failures"])
        result.update(h0_accepted=True,h0_gate_sha256=sha(HERE/"h0-gate.json"),accepted_split=plan["split"] if all_ok else None,
                      c1_plan_sha256=order["plan_sha256"], exact_duplicate_groups=sum(eq),total_duplicate_groups=len(eq),
                      development_c1_accepted=all_ok if phase=="train-c1" else True,split_c1_accepted=all_ok)
    result["gate_passed"]=all_ok
    return result


if __name__ == "__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("h0","train-c1","blind-c1"))
    for k in ("release","report","runtime","inventory","output"):
        parser.add_argument(k,type=Path)
    parser.add_argument("review_commit")
    a=parser.parse_args()
    result=adjudicate(a.phase,a.release.resolve(),a.report.resolve(),a.runtime.resolve(),a.inventory.resolve(),a.review_commit)
    with a.output.open("x",encoding="utf8",newline="\n") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    print(result)
