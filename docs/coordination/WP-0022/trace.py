"""Replay the immutable candidate and retain exact per-line frame states and paired geometric witnesses."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import runpy
import sys

from score import area, belongs, centered, index_observation, overlap, read, refs_in, sourced, write


READER_HASH = "62aec65d9a3c363cfbe94ba8c22f7e5b9f17df279790b361c46f6d5850ed6be7"


def snapshot(locals_):
    frames = []
    for f in locals_["frames"]:
        frames.append(dict(scope=f.scope, headingRefs=list(f.heading_refs), headerRefs=list(f.header_refs),
             x0Anchors=list(f.anchors), rules=list(f.rules), headerPage=f.header_page, headedGrid=f.headed_grid))
    banners = {k: [list(v[0]),list(v[1]),v[2]] for k,v in locals_["banners"].items()}
    return {"frames":frames,"banners":banners}


def trace_reader(reader, observation, prediction):
    engine = runpy.run_path(str(reader))["read"]
    entry = next(i for i,s in enumerate(reader.read_text(encoding="utf-8").splitlines(),1) if s.strip()=='words = line["words"]')
    trace, unique, state_index = {}, [], {}
    previous = None
    def store(state):
        key = json.dumps(state,sort_keys=True)
        if key not in state_index:
            state_index[key] = len(unique)
            unique.append(state)
        return state_index[key]
    def hook(frame, event, arg):
        nonlocal previous
        if frame.f_code is not engine.__code__:
            return None
        if (event == "line" and frame.f_lineno == entry) or event == "return":
            locs = frame.f_locals
            state = store(snapshot(locs))
            if previous is not None:
                trace[previous]["after"] = state
            if event != "return":
                previous = (locs["page_number"], locs["line_no"])
                trace[previous] = {"before":state}
        return hook
    old = sys.gettrace()
    try:
        sys.settrace(hook)
        result = engine(observation,"grid-words")
    finally:
        sys.settrace(old)
    assert json.loads(json.dumps(result)) == prediction
    preds = {(x["page"],x["line"]):x for x in prediction["rows"]}
    lines = {}
    for page in observation["pages"]:
        for num,line in enumerate(page["lines"],1):
            coord=(page["page"],num)
            item=trace[coord]
            pred=preds.get(coord)
            if pred is not None:
                assert [f["scope"] for f in unique[item["before"]]["frames"]] == pred["stack_before"]
                assert [f["scope"] for f in unique[item["after"]]["frames"]] == pred["stack_after"]
            lines[coord] = dict(page=coord[0],line=num,text=line.get("text"," ".join(w["text"] for w in line["words"])),
                textOrigin="supplied" if "text" in line else "ordered renderer words joined by one space",words=line["words"],
                before=item["before"],after=item["after"],decision=None if pred is None else
                {k:pred[k] for k in ["literal","word_ref","scope","column_role","heading_refs","header_refs","flagged",
                                     "reason","grid","alignment","stack_before","stack_after"]})
    return {"lines":lines,"states":unique}


def words_in_region(lines, region):
    return [(loc,w) for loc,line in lines.items() if loc[0]==region["page"] for w in line["words"]
            if sourced(w["bbox"],region["bbox"])]


def source_differences(r_lines, w_lines, region):
    rwords = words_in_region(r_lines,region)
    wwords = words_in_region(w_lines,region)
    candidates = {}
    inverse = {}
    for _,r in rwords:
        matches=[]
        for _,w in wwords:
            if overlap(r["bbox"],w["bbox"]) >= .5 * min(area(r["bbox"]),area(w["bbox"])):
                matches.append(w["ref"])
                inverse.setdefault(w["ref"],[]).append(r["ref"])
        candidates[r["ref"]] = matches
    by_ref={w["ref"]:(coord,w) for coord,w in wwords}
    original_lines={}
    new_lines={}
    aligned=[]
    for coord,r in rwords:
        matches=candidates[r["ref"]]
        if not matches:
            aligned.append(dict(r=r["ref"],w=[],changes=["no-overlapping-W-word"]))
            continue
        changes=[]
        if len(matches)>1:
            changes.append("one-rendered-to-multiple-W")
        if any(len(inverse[m])>1 for m in matches):
            changes.append("multiple-rendered-to-one-W")
        row=dict(r=r["ref"],w=matches,changes=changes)
        if len(matches)==1 and len(inverse[matches[0]])==1:
            newloc,w=by_ref[matches[0]]
            original_lines.setdefault(coord,set()).add(newloc)
            new_lines.setdefault(newloc,set()).add(coord)
            if w["text"]!=r["text"]:
                changes.append("word-text")
            delta=[round(b-a,6) for a,b in zip(r["bbox"],w["bbox"])]
            row["WminusR_Pt"]=delta
            if any(delta):
                changes.append("rectangle")
        aligned.append(row)
    # Line IDs refer to physical arrays local to an arm and are not compared for equality.
    for (coord,r),row in zip(rwords,aligned):
        if len(row["w"])!=1:
            continue
        wcoord=by_ref[row["w"][0]][0]
        if len(original_lines.get(coord,()))>1 or len(new_lines.get(wcoord,()))>1:
            row["changes"].insert(0,"line-grouping")
    extras=[w["ref"] for _,w in wwords if w["ref"] not in inverse]
    return dict(words=aligned,additionalW=extras,firstChanged=next((x for x in aligned if x["changes"]),None))


def state_has_intended(frame, target, sources):
    return (frame["scope"]==target["scope"] and frame["headerRefs"] and
            refs_in(frame["headingRefs"],target["heading"],sources))


def lines_for_target(run, target):
    result=[]
    for loc,line in run["lines"].items():
        if loc[0]==target["page"] and any(belongs(w,target) for w in line["words"]):
            result.append((loc,line))
    return result


def analyze_arm(run, target, scored, sources):
    physical=words_in_region(run["lines"],target["amount_header"])
    physical_header=[dict(page=loc[0],line=loc[1],ref=w["ref"],x0=w["bbox"][0]) for loc,w in physical]
    rowlines=lines_for_target(run,target)
    line_ids = [f"{loc[0]}/{loc[1]}" for loc,_ in rowlines]
    before_loc=min((loc for loc,_ in rowlines),default=(target["page"],10**9))
    previous_states = [run["states"][line["after"]] for loc,line in run["lines"].items() if loc<before_loc]
    captured=any(state_has_intended(f,target,sources) for s in previous_states for f in s["frames"])
    analysis=[]
    for loc,line in rowlines:
        d=line["decision"]
        before=run["states"][line["before"]]
        after=run["states"][line["after"]]
        intended=next((f for f in before["frames"] if state_has_intended(f,target,sources)),None)
        last=line["words"][-1]
        x0=last["bbox"][0]
        anchors=[dict(scope=f["scope"],headerRefs=f["headerRefs"],x0=f["x0Anchors"][-1] if f["x0Anchors"] else None,
             dx0=round(x0-f["x0Anchors"][-1],6) if f["x0Anchors"] else None) for f in before["frames"]]
        analysis.append(dict(line=f"{loc[0]}/{loc[1]}",beforeState=line["before"],afterState=line["after"],
            candidateRef=last["ref"] if d else None,terminalWord=last["ref"],decision=d,
            intendedFramePresentBefore=bool(intended),intendedFramePresentAfter=any(
                bool(state_has_intended(f,target,sources)) for f in after["frames"]),
            savedHeaderDeltas=anchors,dx0ToPhysicalAmountHeader=[round(x0-h["x0"],6) for h in physical_header]))
    return dict(lineIds=line_ids,physicalHeader=physical_header,typedIntendedFramePreviouslyCaptured=captured,
                lineDecisions=analysis,score=scored)


def classify(target, arm):
    if arm["score"]["passed"]:
        return "passed"
    if arm["score"]["outcome"]=="silent_wrong":
        return "silent-post"
    if not arm["score"]["intersectionRefs"]:
        return "amount-source-unobserved"
    amount_refs=set(arm["score"]["centeredRefs"])
    relevant=[d for d in arm["lineDecisions"] if d["candidateRef"] in amount_refs]
    if not relevant:
        return "amount-not-emitted-as-terminal-candidate"
    primary=relevant[0]
    if not primary["intendedFramePresentBefore"]:
        return "intended-typed-frame-unavailable"
    reason=primary["decision"]["reason"]
    if reason=="missing-banner":
        return "required-banner-unavailable"
    if any(a["scope"]==target["scope"] and a["dx0"] is not None and abs(a["dx0"])>3 for a in primary["savedHeaderDeltas"]):
        return "amount-x0-outside-three-points"
    if reason=="tied-scopes":
        return "tied-geometry"
    return "line-or-schema-disagreement"


def per_doc(key, result, evidence, reader):
    targets=key
    doc=targets[0]["doc"]
    runs,source={},{}
    for arm in ("R","W"):
        obs=read(evidence/"observations"/arm/(doc+".json"))
        pred=read(evidence/"predictions"/arm/(doc+".json"))
        runs[arm]=trace_reader(reader,obs,pred)
        source[arm]=index_observation(obs)[0]
    details={}
    for t in targets:
        r=analyze_arm(runs["R"],t,result[t["id"]]["R"],source["R"])
        w=analyze_arm(runs["W"],t,result[t["id"]]["W"],source["W"])
        regions={name:t[name] for name in ("property_region","unit_region","heading","amount_header")}
        for name in ("property_region","unit_region","heading","amount_header"):
            item=t[name]
            top,bottom=item["bbox"][1::2]
            regions[name+"_line_band"]={"page":item["page"],"bbox":[0,top,612,bottom]}
        regions["row"]={"page":t["page"],"bbox":t["row_box"]}
        regions["amount"]={"page":t["page"],"bbox":t["amount_box"]}
        diffs={name:source_differences(runs["R"]["lines"],runs["W"]["lines"],region) for name,region in regions.items()}
        details[t["id"]] = dict(truth=t,R=r,W=w,spatialWordCorrespondence=diffs,
            Rpattern=classify(t,r),Wpattern=classify(t,w),pair=result[t["id"]]["pair"])
    output={"doc":doc,"targets":details}
    for arm in ("R","W"):
        output[arm]={"states":runs[arm]["states"],"lines":{f"{pg}/{li}":v for (pg,li),v in runs[arm]["lines"].items()}}
    return output


if __name__ == "__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ["reader","truth","evidence","scores","out"]:
        ap.add_argument(arg,type=Path)
    args=ap.parse_args()
    assert hashlib.sha256(args.reader.read_bytes().replace(b"\r\n",b"\n")).hexdigest()==READER_HASH
    key=read(args.truth)["targets"]
    scores=read(args.scores)["rows"]
    index={}
    for doc in sorted({t["doc"] for t in key}):
        result=per_doc([t for t in key if t["doc"]==doc],scores,args.evidence,args.reader)
        write(args.out/(doc+".json"),result)
        for tid,t in result["targets"].items():
            index[tid]={"doc":doc,"pair":t["pair"],"Rpattern":t["Rpattern"],"Wpattern":t["Wpattern"]}
    write(args.out/"index.json",index)
