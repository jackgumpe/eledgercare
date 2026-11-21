"""Score WP-0024 after reviewer/coordinator prediction freeze. No training or model loading."""
import argparse
from collections import Counter
import html
import hashlib
import json
import math
from pathlib import Path
import re

ARMS=("M0","M1","M2","M3-Zero","M3","M3-Swap")
FIELDS=("owner","unit","column","subtotal_status")
BIND=FIELDS[:3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def require(condition,description):
    if not condition:
        raise ValueError(description)


def exact_json(path,expected):
    data=Path(path).read_bytes()
    require(sha(data)==expected,f"SHA-256 mismatch: {path}")
    return json.loads(data)


def pred_value(row,field):
    return row.get(field) if row["type"]=="Posting" else None


def semantic(row):
    return (row["type"],*(pred_value(row,f) for f in FIELDS))


def check_predictions(rows,targets):
    predictions={arm:{} for arm in ARMS}
    for row in rows:
        arm,binder=row["arm"],row["binder"]
        require(arm in ARMS and binder in targets and targets[binder]==row["target"],"bad prediction identity")
        require(binder not in predictions[arm],"duplicate prediction")
        require(row["type"] in ("Posting","ABSTAIN"),"unknown decision type")
        if row["type"]=="Posting":
            require(all(isinstance(row.get(f),str) and row[f] for f in BIND),"posting lacks binding")
            require("subtotal_status" in row and row["subtotal_status"] in (None,"BALANCED","UNBALANCED"),"bad status")
        else:
            require(isinstance(row.get("reason"),str) and row["reason"],"abstention without reason")
        predictions[arm][binder]=row
    require(all(set(arm)==set(targets) for arm in predictions.values()),"incomplete six-view freeze")
    return predictions


def norm(text):
    return " ".join(html.unescape(text).casefold().split())


def same(a,b):
    return a==b if a is None or b is None else norm(a)==norm(b)


def evidence(span):
    return {key:span[key] for key in ("index","page","kind","text","cells","char_range","byte_range","token_indices","bbox999") if key in span}


def captured(metadata, expected):
    """Only active declarations after the page-one directory can satisfy a witness."""
    spans=sorted((s for s in metadata["spans"] if s["page"]==1),
                 key=lambda s:(s["char_range"][0],s["char_range"][1]))
    found={"owner":None,"unit":None,"schema":None}
    visible={"owner":None,"unit":None,"schema":None}
    ledger=False
    child_open=False
    # Match complete natural lines. A directory label or child lookup cannot satisfy this rule.
    for s in spans:
        if child_open:
            break
        text=s["text"]
        for line in text.splitlines():
            if norm(line)=="supporting schedule":
                child_open=True
                break
            owner=re.search(r"(?:^|\s)ledger\s*:\s*([\w-]+)\b",line,flags=re.I)
            if owner:
                ledger=True
                visible["owner"]=owner[1]
                found["owner"]=evidence(s)
            unit=re.search(r"(?:^|\s)unit\s*:\s*([\w-]+)\b",line,flags=re.I)
            if ledger and unit:
                visible["unit"]=unit[1]
                found["unit"]=evidence(s)
            cells=s.get("cells",[]) if s["kind"]=="row" else line.split()
            if ledger and len(cells)==3 and {norm(c) for c in cells}=={"item","amount","ref"}:
                visible["schema"]=cells
                found["schema"]=evidence(s)
    reasons=[]
    for field,value in visible.items():
        actual=[norm(x) for x in value] if isinstance(value,list) else norm(value or "")
        ref=expected[field]
        wanted=[norm(x) for x in ref] if isinstance(ref,list) else norm(ref)
        if actual!=wanted:
            reasons.append(f"{field}_{'absent' if value is None else 'mismatch'}")
    return dict(pass_c0=not reasons,visible=visible,miss_reasons=reasons,source_spans=found)


def assessment(row,key):
    abstain=row["type"]=="ABSTAIN"
    if key["ambiguous"]:
        return dict(full=abstain,binding=None,fields={},silent=[] if abstain else ["undecidable"],abstain=abstain,summary_diagnostic=None,binding_diagnostic=None,owner_diagnostic=None)
    applicable=FIELDS if key["stratum"]=="T3" else BIND
    fields={f:not abstain and same(pred_value(row,f),key[f]) for f in applicable}
    errors=[f for f in applicable if not abstain and not fields[f]]
    if not abstain and key["stratum"]!="T3" and row.get("subtotal_status") is not None:
        errors.append("subtotal_status")
    diagnostic=row.get("subtotal_diagnostic")
    status=None
    if key["stratum"]=="T3":
        if diagnostic and diagnostic.get("type")=="STATUS":
            status=diagnostic.get("subtotal_status")==key["subtotal_status"]
        elif diagnostic:
            require(diagnostic.get("type")=="ABSTAIN","unknown subtotal diagnostic")
    binding_diag=row.get("binding_diagnostic")
    binding_ok=all(same(binding_diag.get(f),key[f]) for f in BIND) if binding_diag and binding_diag.get("type")=="Posting" else None
    owner_ok=same(binding_diag.get("owner"),key["owner"]) if binding_diag and binding_diag.get("type")=="Posting" else None
    return dict(owner_diagnostic=owner_ok,binding_diagnostic=binding_ok,full=not abstain and not errors,binding=all(fields[f] for f in BIND),fields=fields,silent=errors,abstain=abstain,summary_diagnostic=status)


def window1_attribution(arm,binder,preds,common,expected):
    audit=preds[arm][binder].get("window1_audit")
    mode={"M0":"suffix_only","M3-Zero":"zero_matrix_control","M3-Swap":"original_receiver_before_swap"}.get(arm,"measured")
    data=dict(mode=mode,observation=audit,common_capture=common,
              measured_field_matches=None,exposed_encoding_failure=None)
    if mode=="original_receiver_before_swap":
        receiver=preds["M3"][binder].get("window1_audit")
        data.update(source_arm="M3",source_binder=binder)
        identical=(isinstance(audit,dict) and isinstance(receiver,dict)
                   and audit.get("source")=="original_receiver_before_swap"
                   and {k:v for k,v in audit.items() if k!="source"}==receiver)
        data["result"]="receiver_reference" if identical else "receiver_reference_unverified"
        data["inherited_receiver_result"]=(window1_attribution("M3",binder,preds,common,expected)["result"] if identical else None)
        return data
    if mode=="suffix_only":
        suffix_only=(isinstance(audit,dict) and audit.get("source")=="suffix_only"
                     and audit.get("observed")==[] and audit.get("decoded_binding") is None
                     and audit.get("encoded")==dict(type="ABSTAIN",reason="suffix_only"))
        data["result"]="structural_suffix_only" if suffix_only else "suffix_reference_unverified"
        return data
    if mode=="zero_matrix_control":
        # Preserve the actual zero=true read, including any unexpected binding, as control evidence.
        if not isinstance(audit,dict) or "decoded_binding" not in audit or "encoded" not in audit:
            data["result"]="zero_control_audit_missing"
        elif audit["decoded_binding"] is not None or audit["encoded"].get("type")!="ABSTAIN":
            data["result"]="zero_control_nonempty"
        else:
            data["result"]="observed_zero_read"
        return data
    if audit is None or "decoded_binding" not in audit:
        data["result"]="measurement_missing"
        return data
    if not common:
        data["result"]="common_capture_missing"
        return data
    decoded=audit["decoded_binding"] or {}
    wanted=dict(owner=expected["owner"],unit=expected["unit"],column=expected["schema"][1])
    fields={k:same(decoded.get(k),value) for k,value in wanted.items()}
    fields["ordered_schema"]=[norm(x) for x in (audit.get("encoded_schema") or [])]==[norm(x) for x in expected["schema"]]
    failed=not all(fields.values())
    data.update(measured_field_matches=fields,exposed_encoding_failure=failed,
                result="encoding_failure" if failed else "encoding_success")
    return data


def pair_counts(items,arm):
    counts=Counter()
    for p in items:
        a=p["arms"][arm]
        counts["pairs"]+=1
        counts["both_correct"]+=a["correct"]
        counts["any_abstain"]+=a["abstentions"]>0
        counts["dual_abstain"]+=a["abstentions"]==2
        counts["any_silent_wrong"]+=bool(a["silent"])
        counts["binding_both_correct"]+=a["binding"] is True
        counts["binding_diagnostic_both_correct"]+=a["binding_diagnostic"] is True
        counts["binding_diagnostic_both_observed"]+=a["binding_diagnostic"] is not None
        counts["summary_both_correct"]+=a["subtotal"] is True
        counts["summary_diagnostic_both_correct"]+=a["subtotal_diagnostic"] is True
        counts["summary_diagnostic_both_observed"]+=a["subtotal_diagnostic"] is not None
    return dict(counts)


def paired_effect(pairs,left,right,objective="correct"):
    counts=Counter(win=0,loss=0,tie=0)
    for p in pairs:
        a,b=p["arms"][left][objective],p["arms"][right][objective]
        require(a is not None and b is not None,"unscored effect outcome")
        counts["win" if a and not b else "loss" if b and not a else "tie"]+=1
    return dict(counts)|dict(net=counts["win"]-counts["loss"],denominator=len(pairs))


def score(keys,routes,preds,observations,resources,suffixes=None):
    cases={p["pair"]:p for p in keys["pairs"]}
    by_binder={b["binder"]:b for b in keys["binders"]}
    require(set(routes)==set(cases) and set(by_binder)==set(observations),"key/routing coverage")
    pairs=[]
    t1_failures=[]
    for pid,members in sorted(routes.items()):
        case=cases[pid]
        res=dict(pair=pid,match=case["match"],stratum=case["stratum"],horizon=case["horizon"])
        keys2=[by_binder[b] for b in members]
        for b,k in zip(members,keys2):
            require(k["pair"]==pid and k["target"]==preds["M3"][b]["target"],"wrong pair/target key")
        res["c0"]={b:captured(observations[b],k["window1"]) for b,k in zip(members,keys2)}
        res["eligible"]=all(item["pass_c0"] for item in res["c0"].values())
        res["arms"]={}
        for arm in ARMS:
            rows=[preds[arm][b] for b in members]
            scored=[assessment(row,k) for row,k in zip(rows,keys2)]
            summary=case["stratum"]=="T3"
            ambiguous=case["stratum"]=="T4"
            diag=[s["summary_diagnostic"] for s in scored]
            diag_bind=[s["binding_diagnostic"] for s in scored]
            diag_owner=[s["owner_diagnostic"] for s in scored]
            res["arms"][arm]=dict(owner_diagnostic=all(diag_owner) if all(v is not None for v in diag_owner) else None,binding_diagnostic=all(diag_bind) if all(v is not None for v in diag_bind) else None,correct=all(s["full"] for s in scored),
                binding=None if ambiguous else all(s["binding"] for s in scored),
                subtotal=all(s["fields"]["subtotal_status"] for s in scored) if summary else None,
                subtotal_diagnostic=all(diag) if summary and all(v is not None for v in diag) else None,
                abstentions=sum(s["abstain"] for s in scored),
                silent={b:s["silent"] for b,s in zip(members,scored) if s["silent"]},
                concordant=semantic(rows[0])==semantic(rows[1]),
                per_field_both_correct={f:all(s["fields"].get(f,False) for s in scored) for f in (FIELDS if summary else BIND)} if not ambiguous else {},
                targets={b:dict(target=k["target"],decision=semantic(row),reason=row.get("reason"),
                                literal=k["literal"],**s) for b,k,row,s in zip(members,keys2,rows,scored)})
            res["arms"][arm]["window1_audit"]={
                b:window1_attribution(arm,b,preds,res["c0"][b]["pass_c0"],k["window1"])
                for b,k in zip(members,keys2)}
            if arm in ("M2","M3") and case["stratum"]=="T1" and res["eligible"] and not res["arms"][arm]["correct"]:
                t1_failures.append(dict(pair=pid,arm=arm,predictions=rows,c0=res["c0"]))
        candidate_records=[preds[arm][b].get("candidate_receipt",{}) for arm in ARMS for b in members]
        def valid_candidate(r):
            payload=json.dumps(r.get("inputs"),sort_keys=True,separators=(",",":")).encode()
            return r.get("pair_equal") is True and r.get("sha256")==sha(payload)
        res["symmetric_anchors"]=all(valid_candidate(r) for r in candidate_records) and len({r.get("sha256") for r in candidate_records})==1
        res["newly_silent_vs_m2"]={}
        for arm in ("M0","M1","M3-Zero","M3","M3-Swap"):
            new=[]
            for b,k in zip(members,keys2):
                current=res["arms"][arm]["targets"][b]
                baseline=res["arms"]["M2"]["targets"][b]
                new.extend(dict(binder=b,target=k["target"],field=f) for f in current["silent"] if f not in baseline["silent"])
            res["newly_silent_vs_m2"][arm]=new
        res["swap"]=[]
        for idx,receiver in enumerate(members):
            donor=members[1-idx]
            r,d=by_binder[receiver],by_binder[donor]
            swapped=preds["M3-Swap"][receiver]
            native=preds["M3"][receiver]
            s_entry=swapped.get("final_entry",{})
            r_entry=native.get("final_entry",{})
            d_entry=preds["M3"][donor].get("final_entry",{})
            swap_proof=(all(re.fullmatch("[0-9a-f]{64}",str(v)) for v in (s_entry.get("matrix_sha256"),r_entry.get("matrix_sha256"),s_entry.get("nonmatrix_sha256")))
                        and s_entry["matrix_sha256"]==d_entry.get("matrix_sha256")
                        and r_entry["matrix_sha256"]==s_entry.get("original_matrix_sha256")==r_entry.get("original_matrix_sha256")
                        and s_entry["nonmatrix_sha256"]==r_entry.get("nonmatrix_sha256")==s_entry.get("receiver_nonmatrix_sha256")==r_entry.get("receiver_nonmatrix_sha256"))
            if swapped["type"]=="ABSTAIN":
                category="abstention"
            elif case["stratum"]=="T4":
                category="undecidable_posting"
            elif same(pred_value(swapped,"owner"),r["owner"]):
                category="receiver_owner_retention" if same(pred_value(native,"owner"),r["owner"]) else "receiver_truth_without_native_retention"
            elif all(same(pred_value(swapped,f),d[f]) for f in FIELDS):
                category="full_donor_posting"
            elif same(pred_value(swapped,"owner"),d["owner"]):
                category="donor_owner_mixed_fields"
            else:
                category="other_wrong"
            res["swap"].append(dict(receiver=receiver,donor=donor,category=category,matrix_only_proof=swap_proof,
                unswapped=semantic(native),swapped=semantic(swapped),
                donor_owner_flipped=bool(r["owner"] and same(pred_value(native,"owner"),r["owner"]) and same(pred_value(swapped,"owner"),d["owner"]))))
        pairs.append(res)
    slices={}
    for name,subset in (("all",pairs),("eligible",[p for p in pairs if p["eligible"]])):
        answerable=[p for p in subset if p["stratum"]!="T4"]
        t23=[p for p in subset if p["stratum"] in ("T2","T3")]
        slices[name]=dict(breakdown={},effects={})
        attribution={}
        for arm in ARMS:
            audits=[a for p in subset for a in p["arms"][arm]["window1_audit"].values()]
            attribution[arm]=dict(binders=len(audits),common_capture_binders=sum(a["common_capture"] for a in audits),
                                  outcomes=dict(Counter(a["result"] for a in audits)))
        slices[name]["window1_attribution"]=attribution
        for stratum in ("T1","T2","T3","T4","answerable","T2+T3","all"):
            selected=answerable if stratum=="answerable" else t23 if stratum=="T2+T3" else [p for p in subset if p["stratum"]==stratum or stratum=="all"]
            for h in (12,30,"both"):
                cells=[p for p in selected if h=="both" or p["horizon"]==h]
                slices[name]["breakdown"][f"{stratum}/{h}"]={arm:pair_counts(cells,arm) for arm in ARMS}
        for population,study in (("answerable",answerable),("T2+T3",t23)):
            for base in ("M1","M2"):
                slices[name]["effects"][f"{population}/{base}"]=paired_effect(study,"M3",base)
        t3=[p for p in subset if p["stratum"]=="T3"]
        owner_tied=[]
        summary_wins=set()
        summary_losses=set()
        full_losses={p["pair"] for p in t23 if p["arms"]["M2"]["correct"] and not p["arms"]["M3"]["correct"]}
        for p in t3:
            a,b=p["arms"]["M3"],p["arms"]["M2"]
            true_owners=all(arm["owner_diagnostic"] is True or arm["per_field_both_correct"]["owner"] for arm in (a,b))
            if not true_owners:
                continue
            owner_tied.append(p["pair"])
            a_status=a["subtotal"] is True or a["subtotal_diagnostic"] is True
            b_status=b["subtotal"] is True or b["subtotal_diagnostic"] is True
            if a["correct"] and not b_status:
                summary_wins.add(p["pair"])
            if b_status and not a_status:
                summary_losses.add(p["pair"])
        losses=summary_losses|full_losses
        slices[name]["effects"]["T3_summary_at_tied_owner/M2"]=dict(
            denominator=len(t23),owner_tied_pairs=owner_tied,usable_summary_wins=sorted(summary_wins),
            opposite_summary_losses=sorted(summary_losses),full_T2_T3_pair_losses=sorted(full_losses),
            union_losses=sorted(losses),net=len(summary_wins)-len(losses))
        slices[name]["effects"]["T3/binding/M2"]=paired_effect(t3,"M3","M2","binding")
        slices[name]["effects"]["T3/subtotal/M2"]=paired_effect(t3,"M3","M2","subtotal")
        components={}
        for f in ("owner_diagnostic","binding_diagnostic","subtotal_diagnostic"):
            universe=t3 if f=="subtotal_diagnostic" else answerable
            for unit in ("pairs","targets"):
                rows=[]
                for p in universe:
                    a=p["arms"]["M3"]
                    b=p["arms"]["M2"]
                    if unit=="pairs":
                        rows.append((a[f],b[f]))
                    else:
                        rows.extend((a["targets"][k]["summary_diagnostic" if f=="subtotal_diagnostic" else f],
                                     b["targets"][k]["summary_diagnostic" if f=="subtotal_diagnostic" else f]) for k in a["targets"])
                tally=Counter(win=0,loss=0,tie=0,m3_observed=0,m2_observed=0)
                for a,b in rows:
                    tally["win" if a is True and b is not True else "loss" if b is True and a is not True else "tie"]+=1
                    tally["m3_observed"]+=a is not None
                    tally["m2_observed"]+=b is not None
                components[f"{f}/{unit}"]=dict(tally)|dict(denominator=len(rows),net=tally["win"]-tally["loss"])
        slices[name]["diagnostic_effects_vs_m2"]=components
        target_comparisons={}
        for arm in ARMS:
            outcomes=Counter(win=0,loss=0,tie=0,newly_silent_fields=0)
            for p in subset:
                a=p["arms"][arm]["targets"]
                b=p["arms"]["M2"]["targets"]
                for k,val in a.items():
                    outcomes["win" if val["full"] and not b[k]["full"] else "loss" if b[k]["full"] and not val["full"] else "tie"]+=1
                outcomes["newly_silent_fields"]+=len(p["newly_silent_vs_m2"].get(arm,[]))
            target_comparisons[arm]=dict(outcomes)
        slices[name]["per_target_vs_m2"]=target_comparisons
        by_field={}
        transitions=Counter()
        for p in subset:
            for binder,current in p["arms"]["M3"]["targets"].items():
                baseline=p["arms"]["M2"]["targets"][binder]
                if baseline["full"] and current["abstain"] and p["stratum"] in ("T2","T3"):
                    transitions["formerly_correct_to_abstain"]+=1
                for f,right in current["fields"].items():
                    before=baseline["fields"][f]
                    label="win" if right and not before else "loss" if before and not right else "tie"
                    by_field.setdefault(f,Counter(win=0,loss=0,tie=0))[label]+=1
        slices[name]["target_fields_M3_vs_M2"]=by_field
        slices[name]["coverage_transitions_M3_vs_M2"]=dict(transitions)
        slices[name]["donor_directions"]=dict(Counter(row["category"] for p in subset for row in p["swap"]))
        decay={}
        for arm in ARMS:
            counts=Counter(both=0,short_only=0,long_only=0,neither=0)
            for match in {p["match"] for p in answerable}:
                hs={p["horizon"]:p["arms"][arm]["correct"] for p in answerable if p["match"]==match}
                if len(hs)<2:
                    counts["unmatched_eligible"]+=1
                else:
                    counts["both" if all(hs.values()) else "short_only" if hs[12] else "long_only" if hs[30] else "neither"]+=1
            decay[arm]=dict(counts)
        slices[name]["matched_horizons"]=decay
    collisions={}
    if suffixes is not None:
        for p in pairs:
            if p["stratum"]!="T3":
                continue
            for b,target in p["arms"]["M0"]["targets"].items():
                choice=preds["M0"][b]["candidate_receipt"]["sha256"]
                group=f"{p['horizon']}:{suffixes[b]}:{choice}"
                row=preds["M0"][b].get("subtotal_diagnostic")
                status=(row or {}).get("subtotal_status") if (row or {}).get("type")=="STATUS" else None
                collisions.setdefault(group,[]).append(dict(binder=b,target=target["target"],truth=by_binder[b]["subtotal_status"],m0_status=status))
    eligible=[p for p in pairs if p["eligible"] and p["stratum"]!="T4"]
    n=Counter(p["stratum"] for p in eligible)
    floor=len(eligible)>=18 and n["T2"]+n["T3"]>=12 and min(n.get(s,0) for s in ("T1","T2","T3"))>=4
    failures=[]
    if not resources["h0_pass"]: failures.append("H0")
    if not resources["c1_pass"]: failures.append("C1")
    if not floor: failures.append("C0_floor")
    if collisions and any(len({r["m0_status"] for r in group})>1 for group in collisions.values()):
        failures.append("M0_equal_suffix_and_candidates_inconsistent_summary")
    if not resources["independent_source_and_freeze_pass"]: failures.append("source_or_freeze")
    ans=[p for p in pairs if p["stratum"]!="T4"]
    if not all(p["symmetric_anchors"] for p in pairs): failures.append("asymmetric_canonical_candidates")
    if not all(row["matrix_only_proof"] for p in pairs for row in p["swap"]): failures.append("matrix_only_swap_proof")
    if any(p["arms"]["M0"]["correct"] or not p["arms"]["M0"]["concordant"] for p in ans): failures.append("M0_suffix_leak")
    if any(p["arms"]["M3-Zero"]["correct"] or not p["arms"]["M3-Zero"]["concordant"] or any(p["arms"]["M3-Zero"]["per_field_both_correct"][f] for f in BIND) for p in ans): failures.append("M3_Zero_binding_leak")
    if any(row["category"]=="receiver_owner_retention" for p in ans for row in p["swap"]): failures.append("M3_Swap_receiver_owner_retention")
    vetoes=[]
    if any(p["newly_silent_vs_m2"]["M3"] for p in pairs): vetoes.append("M3_new_silent_field")
    if any(p["arms"]["M3"]["silent"] for p in pairs if p["stratum"] in ("T1","T4")): vetoes.append("M3_silent_T1_or_T4")
    if any(p["arms"]["M2"]["correct"] and not p["arms"]["M3"]["correct"] for p in pairs if p["stratum"]=="T1"): vetoes.append("M3_lost_T1_pair")
    if resources["probe_vram_mib"]>256 or resources["cached_probe_ms_per_window"]>5: vetoes.append("M3_resource_budget")
    effects=slices["eligible"]["effects"]
    gain_flat=effects["answerable/M1"]["net"]
    gain_stack=effects["T2+T3/M2"]["net"]
    gain_summary=effects["T3_summary_at_tied_owner/M2"]["net"]
    hurdle=max(2,math.ceil(.125*(n["T2"]+n["T3"])))
    gains_pass=len(eligible)>0 and gain_flat>=math.ceil(.20*len(eligible)) and max(gain_stack,gain_summary)>=hurdle
    m2_safe=not any(p["arms"]["M2"]["silent"] for p in pairs if p["stratum"] in ("T1","T4"))
    m2coverage=sum(p["arms"]["M2"]["correct"] for p in eligible)/len(eligible) if eligible else 0
    m2_safe_coverage=m2_safe and m2coverage>=.85 and resources["m2_host_bytes"]<1048576
    if failures or vetoes:
        disposition="INCONCLUSIVE / FAILED"
    elif gains_pass:
        disposition="ADVANCE ONLY TO FRESH-FAMILY REPLICATION"
    elif max(gain_stack,gain_summary)<hurdle and m2_safe_coverage:
        disposition="KEEP SIMPLER M2"
    else:
        disposition="INCONCLUSIVE / FAILED"
    return dict(pairs=pairs,slices=slices,t1_failures=t1_failures,resources=resources,t3_m0_summary_collision_groups=collisions,
                decision=dict(disposition=disposition,entry_or_leakage_failures=failures,safety_or_resource_vetoes=vetoes,
                              c0_floor_pass=floor,c0_answerable=len(eligible),c0_counts=dict(n),effect_pass=gains_pass,net_vs_flat=gain_flat,primary_net_vs_stack=gain_stack,summary_net_vs_stack=gain_summary,stack_hurdle=hurdle,
                              m2_correct_pair_coverage=m2coverage,m2_safe_coverage_resources_pass=m2_safe_coverage))


def main(args):
    freeze=read(args.freeze)
    require(freeze["authority"] in ("eld-coordinator","eld-rd-reviewer") and freeze["action"]=="score-wp0024-frozen-predictions","prediction release")
    require(freeze["split"]=="blind" and freeze["arms"]==list(ARMS),"all-arm blind release")
    transport=exact_json(args.transport,freeze["transport_sha256"])
    pred=exact_json(args.predictions,freeze["predictions_sha256"])
    pairs=exact_json(args.pairs,freeze["pairs_sha256"])["pairs"]
    routes={p["pair"]:[m["binder"] for m in p["members"]] for p in pairs}
    require(len(routes)==32 and all(len(v)==2 for v in routes.values()),"blind pair count")
    targets={m["binder"]:m["target"] for p in pairs for m in p["members"]}
    require(len(targets)==len(set(targets.values()))==64,"one opaque target per binder")
    preds=check_predictions(pred if isinstance(pred,list) else pred["predictions"],targets)
    observations={}
    route_sets={frozenset(members) for members in routes.values()}
    for pair in transport["pairs"]:
        twins=pair["twins"]
        require(frozenset(t["binder"] for t in twins) in route_sets,"transport paired association")
        for twin in twins:
            b=twin["binder"]
            require(b not in observations and targets[b]==twin["target"],"ambiguous transport identity")
            observations[b]=exact_json(Path(twin["windows"][0])/"metadata.json",freeze["window1_sha256"][b])
    require(set(observations)==set(targets),"incomplete sensor freeze")
    plan=exact_json(args.pairs.with_name("manifest.json"),freeze["sensor_plan_sha256"])
    suffixes={d["binder"]:sha(json.dumps([p["rgb_sha256"] for p in d["windows"][-1]["pages"]],separators=(",",":")).encode()) for d in plan["binders"]}
    require(set(suffixes)==set(targets) and all(len({suffixes[b] for b in members})==1 for members in routes.values()),"unequal raster suffix")
    resources=exact_json(args.resources,freeze["resources_sha256"])
    for field in ("h0_pass","c1_pass","independent_source_and_freeze_pass"):
        require(type(resources[field]) is bool,field)
    for field in ("probe_vram_mib","cached_probe_ms_per_window","m2_host_bytes"):
        require(type(resources[field]) in (int,float) and math.isfinite(resources[field]) and resources[field]>=0,field)
    # The first private truth read is below prediction completeness and digest verification.
    keys=exact_json(args.truth,freeze["truth_sha256"])
    result=score(keys,routes,preds,observations,resources,suffixes)
    result["freeze_sha256"]=sha(args.freeze.read_bytes())
    with args.out.open("xb") as f:
        f.write((json.dumps(result,indent=2)+"\n").encode())


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("freeze","predictions","pairs","transport","resources","truth","out"):
        parser.add_argument("--"+arg,required=True,type=Path)
    main(parser.parse_args())
