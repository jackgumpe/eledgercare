"""CPU regression cases for scorer semantics. All records below are toy observations."""
from copy import deepcopy
from pathlib import Path
import runpy

impl=runpy.run_path(str(Path(__file__).with_name("score.py")))
ARMS=impl["ARMS"]


def block(i,text,cells=None):
    return dict(index=i,page=1,kind="row" if cells else "block",text=text,cells=cells or [],
                char_range=[i*100,i*100+len(text)],byte_range=[i*100,i*100+len(text)],
                token_indices=[i],bbox999=[20,20+i*30,300,45+i*30])


def toy():
    pairs,keys,routes,observations,rows=[],[],{},{},[]
    for sid,stratum in enumerate(("T1","T2","T3","T4")):
        for i in range(8):
            pid=f"{stratum}.{i}"
            pairs.append(dict(pair=pid,stratum=stratum,horizon=12 if i<4 else 30,match=f"{stratum}.{i%4}"))
            routes[pid]=[]
            for side in (0,1):
                binder=pid+"."+str(side)
                target=binder+".cell"
                routes[pid].append(binder)
                owner,unit,other_unit=(("A","U1","U2"),("B","U2","U1"))[side]
                schema=["Item",*(("Amount","Ref"),("Ref","Amount"))[side]]
                w1=dict(owner=owner,unit=unit,schema=schema)
                status=("BALANCED" if i%2==0 else "UNBALANCED") if stratum=="T3" else None
                truth=dict(pair=pid,binder=binder,target=target,stratum=stratum,ambiguous=stratum=="T4",
                           owner=owner,unit=other_unit if stratum=="T2" else unit,column=schema[1],
                           subtotal_status=status,literal="103",window1=w1)
                keys.append(truth)
                observations[binder]=dict(spans=[block(0,"Owners: A / B"),block(1,"Units: U1 / U2"),
                            block(2,"Schema: Item / Amount / Ref"),block(3,"Ledger: "+owner),
                            block(4,"Unit: "+unit),block(5," ".join(schema),schema)])
                for arm in ARMS:
                    sym=dict(choices=["A","B"])
                    can=dict(inputs=sym,sha256=impl["sha"](b'{"choices":["A","B"]}'),pair_equal=True)
                    r=dict(arm=arm,binder=binder,target=target,candidate_receipt=can)
                    flat_audit=dict(observed=[dict(kind="OPEN_LEDGER",value=owner,ptr=[1,1,3],literal="Ledger: "+owner)],
                                    encoded=dict(type="Posting",owner=owner,unit=unit,column=schema[1],subtotal_status=None),
                                    decoded_binding=dict(owner=owner,unit=unit,column=schema[1]),encoded_schema=schema)
                    if arm=="M0":
                        r["window1_audit"]=dict(source="suffix_only",observed=[],decoded_binding=None,encoded=dict(type="ABSTAIN",reason="suffix_only"))
                    elif arm=="M3-Zero":
                        r["window1_audit"]=flat_audit|dict(decoded_binding=None,encoded_schema=None,encoded=dict(type="ABSTAIN",reason="zero_state_tie"))
                    elif arm=="M3-Swap":
                        r["window1_audit"]=flat_audit|dict(source="original_receiver_before_swap")
                    else:
                        r["window1_audit"]=flat_audit
                    if arm in ("M3","M3-Swap"):
                        native=impl["sha"](binder.encode())
                        donor=impl["sha"]((pid+"."+str(1-side)).encode())
                        receiver=impl["sha"](("receiver."+binder).encode())
                        r["final_entry"]=dict(matrix_sha256=donor if arm=="M3-Swap" else native,
                           original_matrix_sha256=native,nonmatrix_sha256=receiver,receiver_nonmatrix_sha256=receiver)
                    if stratum=="T4" or arm in ("M0","M3-Zero") or (arm=="M1" and i<3) or (arm=="M2" and stratum=="T2" and i<2):
                        rows.append(r|dict(type="ABSTAIN",reason="toy"))
                    else:
                        output={field:truth[field] for field in impl["FIELDS"]}
                        if arm=="M3-Swap":
                            output.update(owner="AB"[1-side],unit=unit if stratum=="T2" else other_unit,column=schema[2])
                        rows.append(r|dict(type="Posting",**output))
    preds=impl["check_predictions"](rows,{k["binder"]:k["target"] for k in keys})
    resources=dict(h0_pass=True,c1_pass=True,independent_source_and_freeze_pass=True,probe_vram_mib=80,
                   cached_probe_ms_per_window=3.,m2_host_bytes=50000)
    return dict(binders=keys,pairs=pairs),routes,preds,observations,resources


def test():
    keys,routes,preds,obs,resources=toy()
    def score(p=preds,o=obs,r=resources):
        return impl["score"](keys,routes,p,o,r)
    good=score()
    assert good["decision"]["disposition"].startswith("ADVANCE") and good["decision"]["c0_answerable"]==24
    assert good["slices"]["eligible"]["effects"]["T2+T3/M2"]["net"]==2
    assert good["slices"]["all"]["donor_directions"]=={"full_donor_posting":48,"abstention":16}
    assert not good["t1_failures"]
    w=deepcopy(preds)
    exposed=routes["T1.0"][0]
    w["M1"][exposed]["window1_audit"]["decoded_binding"]["unit"]="wrong-unit"
    acquisition=score(w)
    p=acquisition["pairs"][0]
    assert p["eligible"] and acquisition["decision"]==good["decision"]
    got={arm:p["arms"][arm]["window1_audit"][exposed] for arm in ARMS}
    assert got["M1"]["result"]=="encoding_failure" and not got["M1"]["measured_field_matches"]["unit"]
    assert all(got[a]["result"]=="encoding_success" for a in ("M2","M3"))
    assert got["M0"]["result"]=="structural_suffix_only" and got["M0"]["exposed_encoding_failure"] is None
    assert got["M3-Zero"]["result"]=="observed_zero_read" and got["M3-Zero"]["observation"]["encoded"]["reason"]=="zero_state_tie"
    assert got["M3-Swap"]["source_binder"]==exposed and got["M3-Swap"]["result"]=="receiver_reference" and got["M3-Swap"]["inherited_receiver_result"]=="encoding_success"
    assert acquisition["slices"]["eligible"]["window1_attribution"]["M1"]["outcomes"]["encoding_failure"]==1
    assert all(a["common_capture_binders"]==64 for a in acquisition["slices"]["all"]["window1_attribution"].values())
    w["M1"][exposed].pop("window1_audit")
    assert score(w)["pairs"][0]["arms"]["M1"]["window1_audit"][exposed]["result"]=="measurement_missing"
    # Directory alone cannot expose a ledger, and incorrect order is not a correct schema.
    unknown=deepcopy(obs)
    for r in routes:
        if r.startswith(("T1.","T2.")):
            for b in routes[r]:
                unknown[b]["spans"]=unknown[b]["spans"][:3]
    low=score(o=unknown)
    assert "C0_floor" in low["decision"]["entry_or_leakage_failures"]
    assert low["decision"]["c0_answerable"]==8
    b=routes["T1.0"][0]
    wrong=deepcopy(obs)
    wrong[b]["spans"][-1]["cells"]=["Item","Ref","Amount"]
    c0=score(o=wrong)["pairs"][0]["c0"][b]
    assert not c0["pass_c0"] and c0["miss_reasons"]==["schema_mismatch"]
    child_only=dict(spans=[block(0,"Owners: A / B"),block(1,"Supporting schedule"),
                           block(2,"Ledger: A"),block(3,"Unit: U1"),
                           block(4,"Item Amount Ref",["Item","Amount","Ref"])])
    hidden=impl["captured"](child_only,{"owner":"A","unit":"U1","schema":["Item","Amount","Ref"]})
    assert not hidden["pass_c0"] and hidden["miss_reasons"]==["owner_absent","unit_absent","schema_absent"]
    changed=deepcopy(preds)
    changed["M3"][b]["unit"]="wrong"
    bad=score(changed)
    assert set(bad["decision"]["safety_or_resource_vetoes"])=={"M3_new_silent_field","M3_silent_T1_or_T4","M3_lost_T1_pair"}
    assert bad["t1_failures"][0]["pair"]=="T1.0"
    changed=deepcopy(preds)
    changed["M3"][routes["T3.0"][0]].update(type="ABSTAIN",reason="low confidence")
    result=score(changed)
    assert result["slices"]["all"]["coverage_transitions_M3_vs_M2"]["formerly_correct_to_abstain"]==1
    assert result["slices"]["all"]["effects"]["T2+T3/M2"]["net"]==1
    assert not result["decision"]["safety_or_resource_vetoes"] and result["decision"]["disposition"]=="KEEP SIMPLER M2"
    changed=deepcopy(preds)
    changed["M3"][routes["T3.0"][0]]["subtotal_status"]="UNBALANCED"
    result=score(changed)
    assert result["pairs"][16]["newly_silent_vs_m2"]["M3"][0]["field"]=="subtotal_status"
    assert "M3_new_silent_field" in result["decision"]["safety_or_resource_vetoes"]
    changed=deepcopy(preds)
    changed["M3-Swap"][b].update(owner="A")
    assert "M3_Swap_receiver_owner_retention" in score(changed)["decision"]["entry_or_leakage_failures"]
    for arm in ("M0","M3-Zero"):
        changed=deepcopy(preds)
        for who in routes["T1.0"]:
            changed[arm][who]=changed["M3"][who]|{"arm":arm}
        assert any(arm.replace("-","_") in f for f in score(changed)["decision"]["entry_or_leakage_failures"])
    changed=deepcopy(preds)
    changed["M3"][routes["T4.0"][0]].update(type="Posting",owner="A",unit="U1",column="Amount",subtotal_status=None)
    assert "M3_silent_T1_or_T4" in score(changed)["decision"]["safety_or_resource_vetoes"]
    incomplete=[r for arm in preds.values() for r in arm.values()][:-1]
    try:
        impl["check_predictions"](incomplete,{k["binder"]:k["target"] for k in keys["binders"]})
    except ValueError as e:
        assert str(e)=="incomplete six-view freeze"
    else:
        raise AssertionError("partial predictions admitted")
    assert "M3_resource_budget" in score(r=resources|{"cached_probe_ms_per_window":5.01})["decision"]["safety_or_resource_vetoes"]
    print("PASS synthetic scorer regressions: C0, controls, all-arm completeness, donor directions, field errors, abstention coverage, matched gains, unsafe ambiguity, resource ceiling")


if __name__=="__main__":
    test()
