"""Pass real six-view code's public toy outputs to the separate scorer's W1 attribution."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from matrix_audit import isolated_environment


def run(probe,scorer):
    isolated_environment()
    workspace=Path("C:/Users/jackg/eLedgerCare-Speed/WP-0024/review/cpu")/probe
    for name in ("matrix.py","online.py","views.py","preflight.py","run.py"):
        assert (workspace/name).read_bytes()==subprocess.check_output(["git","show",probe+":docs/research/WP-0024/probe/"+name])
    code=runpy.run_path(str(workspace/"preflight.py"))
    code["setup"]()
    arms=("M0","M1","M2","M3-Zero","M3","M3-Swap")
    m1,m3=code["Memory"](True),code["Memory"](False)
    twins=code["histories"]()
    cuts={"M1":(-1,0),"M3":(-1,0)}
    produced=code["predict_pair"](m1,m3,cuts,*twins)
    indexed={arm:{str(i):d[arm] for i,d in enumerate(produced)} for arm in arms}
    impl={}
    exec(compile(subprocess.check_output(["git","show",scorer+":docs/fixtures/WP-0024/score.py"]),"custody/score.py","exec"),impl)
    checks={}
    for i in ("0","1"):
        owner,unit,schema=(("Oak","U4",["Item","Amount","Ref"]),("Palm","U7",["Item","Ref","Amount"]))[int(i)]
        expected=dict(owner=owner,unit=unit,schema=schema)
        info={arm:impl["window1_attribution"](arm,i,indexed,True,expected) for arm in arms}
        assert set(info[a]["mode"] for a in ("M1","M2","M3"))=={"measured"}
        assert info["M2"]["result"]=="encoding_success"
        assert info["M0"]["result"]=="structural_suffix_only" and info["M3-Zero"]["result"]=="observed_zero_read"
        assert info["M3-Swap"]["inherited_receiver_result"]==info["M3"]["result"]
        assert info["M3-Swap"]["source_binder"]==i
        assert all(info[a]["result"] in ("encoding_failure","encoding_success") for a in ("M1","M3"))
        # A fresh M1 corruption must be an M1-specific failure, with the other five observations invariant.
        altered=deepcopy(indexed)
        altered["M1"][i]["window1_audit"]["decoded_binding"]={"owner":owner,"unit":"wrong_independent_unit","column":schema[1]}
        altered["M1"][i]["window1_audit"]["encoded_schema"]=schema
        defect=impl["window1_attribution"]("M1",i,altered,True,expected)
        assert defect["exposed_encoding_failure"] and not defect["measured_field_matches"]["unit"]
        for a in arms:
            if a!="M1":
                assert impl["window1_attribution"](a,i,altered,True,expected)==info[a]
        checks[i]={a:{"mode":r["mode"],"result":r["result"]} for a,r in info.items()}
    return {"probe":probe,"scorer":scorer,"public_toy_only":True,"six_arms_both_directions":checks,
            "observed_mutation_confined_to_M1":True}


if __name__=="__main__":
    assert sys.flags.isolated and sys.dont_write_bytecode
    print(json.dumps(run(sys.argv[1],sys.argv[2]),indent=2))

