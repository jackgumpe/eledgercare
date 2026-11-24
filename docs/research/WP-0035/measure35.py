"""Transparent scoring, native byte gates and predeclared comparisons."""
from collections import Counter, defaultdict
import math
import struct

import online
from trajectory35 import AXIS, f64

def root_key(p, model, write):
    return dict(task=p["task"],pair=p["pair"],horizon=p["horizon"],model=model,write=write)

def correct(typed, expected):
    if typed["type"] != "Posting":
        return False
    def norm(v):
        return online.key(v) if v is not None else None
    return all(norm(typed[k]) == norm(v) for k,v in expected.items())

def owner_action(obs, expected):
    if obs is None:
        return "unavailable"
    if not obs["eligible"] or obs["scope"]:
        return "ineligible"
    if not (obs["score_pass"] and obs["gap_pass"] and len(obs["leaders"]) == 1) or obs["zero"]:
        return "abstain"
    return "correct" if expected and online.key(obs["leaders"][0]) == online.key(expected) else "wrong"

def terminal(key, member, read, typed, attempts, obs, answerable):
    posted = typed["type"] == "Posting"
    ok = correct(typed,member["expected"]) if answerable else not posted
    return dict(**key,binder=member["binder"],target=member["target"],read=read,typed=typed,
                expected=member["expected"],answerable=answerable,full_correct=ok,
                full_decision=("correct" if ok else "wrong") if posted else "abstain",
                n_attempts=len(attempts),attempts=attempts,
                owner_decision=owner_action(obs,member["expected"]["owner"]) if key["model"]!="M2" else None,
                owner_cutoff=(dict(score_pass=obs["score_pass"],gap_pass=obs["gap_pass"],top=obs["top"],gap=obs["gap"])
                              if obs else None))

def contrast(alpha,beta):
    a,b = alpha["signed_margin"],beta["signed_margin"]
    d,mu = a-b,(a+b)/2
    gamma = d-2*abs(mu)
    wins = int(a>0)+int(b<0)
    assert (gamma>0) == (wins==2)
    full_wins = int(alpha["leaders"]==["Alder"])+int(beta["leaders"]==["Cedar"])
    result = dict(alpha=a,beta=b,delta=d,mu=mu,gamma=gamma)
    return dict(**result, wins=wins, full_directory_wins=full_wins,
                fp64le={k:f64(v) for k,v in result.items()})

def add_replay(p,model,write,replays,data):
    key = root_key(p,model,write)
    aligned = defaultdict(dict)
    for m in p["members"]:
        b = m["binder"]
        replay = replays[b]
        data["anchors"].append(dict(**key,binder=b,**replay.reader.details()))
        data["writes"].append(dict(**key,binder=b,updates=replay.updates))
        terminal_score = {}
        for s in replay.rows:
            step = s["actual_step"] if p["task"]=="A" else -1
            row = dict(**key,binder=b,step=step,target=m["target"],expected_owner=m["expected"]["owner"],
                       owner_action=owner_action(s,m["expected"]["owner"]),**s)
            data["scores"].append(row)
            tag = (s["phase"],step,s["read"])
            assert m["expected"]["owner"] not in aligned[tag]
            aligned[tag][m["expected"]["owner"]] = row
            if s["phase"] == "native_pre":
                terminal_score[s["read"]] = row
        for read,typed in replay.final_outputs.items():
            data["terminals"].append(terminal(key,m,read,typed,[a[read] for a in replay.attempts],
                                              terminal_score.get(read),p["answerable"]))
    for (phase,step,read),pair in aligned.items():
        a,b = [pair[k] for k in AXIS]
        if p["task"] == "A":
            assert a["ptr"] == b["ptr"] and a["checkpoints"] == b["checkpoints"]
        data["contrasts"].append(dict(**key,step=step,phase=phase,read=read,actual_steps=[a["actual_step"],b["actual_step"]],
                                      pointers=[a["ptr"],b["ptr"]],checkpoint_labels=[a["checkpoints"],b["checkpoints"]],
                                      **contrast(a,b)))

def parity_a(p,model,replays,archived):
    records = []
    members = {m["expected"]["owner"]:replays[m["binder"]] for m in p["members"]}
    refs = [r for r in archived if r["run"] == model+"/"+str(p["horizon"])]
    for ref,alpha,beta in zip(refs,members["Alder"].rows,members["Cedar"].rows, strict=True):
        pair = {}
        for name,row in zip(AXIS,(alpha,beta),strict=True):
            r = ref[name]
            old = r["read"]
            assert (row["phase"], row["actual_step"]) == (r["phase"],r["step"])
            assert row["ptr"] == (r["source"]["ptr"] if r["source"] else None)
            assert row["event_kinds"] == [e["kind"] for e in r["events_applied"]]
            assert all(row[k] == old[k] for k in ("read_sha256","query_sha256","matrix_sha256","owner_columns_sha256"))
            assert row["depth"] == old["controller"]["depth"] and row["scope"] == old["controller"]["ambiguous_reason"]
            assert row["zero"] == old["zero_read"] and row["eligible"] == old["owner_eligible"]
            assert {k:list(v) for k,v in row["registry"].items()} == old["registry"]
            assert row["score_hex"] == old["score_f32le"] and f64(row["signed_margin"]) == old["margin_f64le"]
            pair[name] = dict(score_hex=row["score_hex"],margin_f64le=old["margin_f64le"],read_sha256=row["read_sha256"],
                              matrix_sha256=row["matrix_sha256"],query_sha256=row["query_sha256"],
                              owner_columns_sha256=row["owner_columns_sha256"],ptr=row["ptr"])
            if row["phase"] == "native_pre":
                attempt, = members[name].attempts
                a = attempt["R0"]
                assert a["field_scores_hex"] == r["native"]["score_bytes"] and a["typed"] == r["native"]["typed"]
                assert all(a[k] == r["native"][k] for k in ("zero","summary_target","summary_zero","reason"))
                pair[name]["typed"] = a["typed"]
        terms = contrast(alpha,beta)
        assert terms["fp64le"]["delta"] == ref["delta_f64le"] and (terms["wins"]==2) == ref["paired_win"]
        records.append(dict(model=model,horizon=p["horizon"],pair=p["pair"],step=ref["step"],phase=ref["phase"],
                            delta_f64le=ref["delta_f64le"],members=pair))
    return records

def parity_b(p,model,replays,archived):
    checks = []
    for m in p["members"]:
        b = m["binder"]
        ref = archived[model]["by_binder"][b]
        r = replays[b]
        assert ref["attempt_count"] == len(r.attempts)
        assert r.final_outputs["R0"] == ref["selected_binder_decision"]
        for item in r.attempts:
            a = item["R0"]
            ptr = "/".join(map(str,a["ptr"]))
            historical = ref["attempts_by_ptr"][ptr]
            assert a["typed"] == historical["original_selected_typed"] and a["reason"] == historical["attempt_reason"]
            for field,old in historical["fields"].items():
                actual = {online.key(k):v for k,v in a["field_scores"].get(field,{}).items()}
                assert actual.keys() == old["scores_by_key"].keys()
                assert all(struct.pack("<f",v) == struct.pack("<f",old["scores_by_key"][k]) for k,v in actual.items())
            if "owner" in a["field_scores"]:
                row, = [s for s in r.rows if s["read"]=="R0" and s["ptr"]==a["ptr"]]
                prev = historical["actual_reads"]["owner"]
                assert row["read_sha256"] == prev["read_sha256"] and row["query_sha256"] == prev["query_sha256"]
        checks.append(dict(model=model,pair=p["pair"],binder=b,attempts=len(r.attempts),typed=r.final_outputs["R0"],
                           field_score_bytes=[a["R0"]["field_scores_hex"] for a in r.attempts]))
    return checks

def symbolic(p,windows,data):
    key = root_key(p,"M2","symbolic")
    for m in p["members"]:
        state = online.Discrete()
        for i,w in enumerate(windows[m["binder"]],1):
            state.window(w,i)
        ptrs = [r["ptr"] for r in state.trace if r["event"]=="TARGET"]
        entries = [dict(ptr=ptr,typed=v) for ptr,v in zip(ptrs,state.outputs,strict=True)]
        data["terminals"].append(terminal(key,m,"symbolic",online.single(state.outputs),entries,None,p["answerable"]))

def tables(data):
    contrasts = data["contrasts"]
    by_key = {(r["pair"],r["model"],r["write"],r["read"],r["phase"],r["step"]):r for r in contrasts}
    effects = []
    for r in contrasts:
        options = []
        if r["write"] != "W0":
            options.append(({"W1":"W0","W2a":"W1","W2b":"W2a"}[r["write"]],r["read"]))
        if r["read"]=="R1":
            options.append((r["write"],"R0"))
        for w,read in options:
            base = by_key[r["pair"],r["model"],w,read,r["phase"],r["step"]]
            diff = {f:r[f]-base[f] for f in ("alpha","beta","mu","delta","gamma","wins")}
            effects.append(dict(**{k:r[k] for k in ("task","pair","horizon","model","phase","step","write","read")},
                                base_write=w,base_read=read,difference=diff))
    tables = {}
    for r in data["terminals"]:
        group = "A" if r["task"]=="A" else "B" if r["answerable"] else "B-safety"
        arm = "/".join((r["model"],r["write"],r["read"]))
        for scope in (group,group+"-"+str(r["horizon"])):
            counts = tables.setdefault(scope,{}).setdefault(arm,Counter())
            counts["binders"] += 1
            counts["typed_"+r["full_decision"]] += 1
            counts["typed_"+r["typed"].get("reason","Posting")] += 1
            if r["owner_decision"] is not None:
                counts["owner_"+r["owner_decision"]] += 1
            if r["owner_cutoff"]:
                c = r["owner_cutoff"]
                bracket = {(False,False):"both_failed",(True,False):"gap_failed",(False,True):"score_failed",
                           (True,True):"neither_failed"}[c["score_pass"],c["gap_pass"]]
                counts["cutoff_"+bracket] += 1
            if r["n_attempts"] != 1:
                counts["no_target" if not r["n_attempts"] else "multiple_targets"] += 1
    for r in contrasts:
        if r["phase"]!="native_pre":
            continue
        arm = "/".join((r["model"],r["write"],r["read"]))
        for scope in (r["task"],r["task"]+"-"+str(r["horizon"])):
            counts = tables[scope][arm]
            counts["rank_pairs"] += 1
            counts["both_ranked"] += int(r["wins"]==2)
            counts["positive_delta"] += int(r["delta"]>0)
    for group,arms in tables.items():
        for arm,counts in arms.items():
            for name in ("typed_correct","typed_wrong","typed_abstain","no_target","multiple_targets","missing_binder"):
                counts.setdefault(name,0)
            if not arm.startswith("M2/"):
                for name in ("owner_correct","owner_wrong","owner_abstain","owner_ineligible","owner_unavailable",
                             "cutoff_both_failed","cutoff_gap_failed","cutoff_score_failed","cutoff_neither_failed"):
                    counts.setdefault(name,0)
                if "safety" not in group:
                    for name in ("rank_pairs","both_ranked","positive_delta"):
                        counts.setdefault(name,0)
    attenuation = []
    for r in contrasts:
        if (r["task"],r["phase"],r["step"]) != ("A","post",11):
            continue
        old = by_key[r["pair"],r["model"],r["write"],r["read"],"post",8]["delta"]
        attenuation.append(dict(**{k:r[k] for k in ("pair","horizon","model","write","read")},delta8=old,delta11=r["delta"],
                                fraction_abs_lost=1-abs(r["delta"])/abs(old) if old else None))
    dynamics = []
    for w in data["writes"]:
        updates = [u for u in w["updates"] if u["downstream"] and not u["after_target"]]
        dynamics.append(dict(**{k:v for k,v in w.items() if k!="updates"},
                             eligible_root_writes=len(updates),alpha_beta_over_one=sum(u["alpha_beta"]>1 for u in updates),
                             native_alpha_product=math.prod(u["alpha"] for u in updates),
                             effective_alpha_product=math.prod(u["effective_alpha"] for u in updates),
                             declaration_steps=[u["step"] for u in w["updates"] if u["designated"]]))
    return effects, dict(by_population=tables,attenuation=attenuation,dynamics=dynamics,
                         interpretation="Top-two gap in FP64 after promotion. Threshold uses native FP32 gap. Full typed C/W/A uses every field. Safety and M2 do not have a numerical rank denominator.")
