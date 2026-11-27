"""Realize frozen continuation, interruption, and noncontiguous CPU read schedules."""
import ast
import copy
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import sys

PHASES=("C0_raw","C1_post_rep","C2_post_page")


def program(s, raws, ops):
    ids=s["vocab"]["ids"]
    page,eos=s["page_id"],s["eos_id"]
    expected=s["prompt_ids"].count(page)
    history=list(s["generated_prefix"])
    limit=s["max_new_tokens"]
    stop_at=None
    adjusted=copy.deepcopy(raws)
    for op in ops:
        if op["op"]=="max_new_tokens":
            limit=op["value"]
        elif op["op"]=="interrupt":
            stop_at=op["after_step"]+1
        elif op["op"]=="perturb_raw":
            for key,value in op["values"].items():
                adjusted[op["step"]][ids.index(int(key))]=struct.unpack("<I",struct.pack("<f",float(value)))[0]
        else:
            raise ValueError("unsupported continuation injection")
    steps=[]
    histories=[]
    for j,words in enumerate(adjusted):
        if j==limit or j==stop_at:
            break
        histories.append(list(history))
        # Bound to the frozen F5 family: order 35 never activates and cap never binds.
        assert len(history)<s["ngram"]["order"] and len(history)<s["max_page_tokens"]
        allowed=[(tok,w) for tok,w in zip(ids,words,strict=True) if tok!=eos or history.count(page)>=expected]
        scores=[[t,f"{v:08x}"] for t,v in allowed]
        previous=str(history[-1]) if history else "None"
        steps.append({"by_previous":{previous:scores}})
        winner=max(allowed,key=lambda pair:struct.unpack("<f",struct.pack("<I",pair[1]))[0])[0]
        if winner==eos:
            break
        history.append(winner)
    result={"prefix":s["generated_prefix"],"limit":limit,"steps":steps}
    if stop_at is not None:
        result["interrupt_before"]=stop_at
    return result,histories


def main(src,fixture,work):
    work.mkdir(parents=True)
    results=[]
    for c in map(json.loads,(fixture/"cases.jsonl").read_bytes().splitlines()):
        name=c["case_id"]
        if not name.startswith("F5.") and name not in {"F6.torn_raw","F4.g_interrupt_after_differing"}:
            continue
        s=c["scenario"]
        ids=s["vocab"]["ids"]
        raws=[]
        for spec in s["raw"]:
            data=(fixture/spec["input"]).read_bytes()
            assert sha256(data).hexdigest()==spec["sha256"]
            raws.append([v for v, in struct.iter_unpack("<I",data)])
        frozen=json.loads((fixture/c["reference_evidence_path"]).read_bytes())["arms"]
        public=frozen["untouched"]["public"]
        contract={"vocab":ids,"page":s["page_id"],"eos":s["eos_id"],"order":s["ngram"]["order"],
                  "window":s["ngram"]["window"],"cap":s["max_page_tokens"],"prompt":s["prompt_ids"],
                  "raw_words":[[f"{w:08x}" for w in raws[i]] for i in s["rows"]],
                  "document":{"ids":public["token_ids"],"terminal":public["finish_reason"]}}
        case={"contract":contract,"injections":[]}
        if name.startswith("F5."):
            untouched,histories=program(s,raws,[])
            observed,observed_hist=program(s,raws,c["injection"])
            contract["histories"]=[histories[i] for i in s["rows"]]
            case["continuation"]={"untouched":untouched,"observed":observed}
            missing=[i for i in s["rows"] if i>=len(observed_hist)]
            if missing:
                case["injections"].append({"op":"omit_row","row":missing[0],"through_end":True})
        else:
            contract["histories"]=[s["generated_prefix"]]
            case["document"]=contract["document"]
            events=c["injection"][0]["events"]
            early=ast.literal_eval(events[0].split(" ",2)[2])
            assert events[1:]==["W_N","R C1_post_rep *","W_P","R C0_raw *","R C2_post_page *"]
            case["injections"].append({"op":"torn","row":0,"phase":PHASES[0],"at":PHASES[2],"early_ids":early})
            for op in c["injection"][1:]:
                assert op["op"]=="truncate"
                case["injections"].append({"op":"truncate","row":op["row"],"phase":op["phase"],
                                            "bytes":4*op["keep_words"],"complete":op["declare_complete"]})
        directory=work/name
        directory.mkdir()
        for f,o in (("case",case),("contract",contract)):
            (directory/(f+".json")).write_bytes(json.dumps(o).encode())
        stock=src/"stock.py"
        evidence=subprocess.check_output([sys.executable,"-B",str(stock),"capture",str(directory/"case.json")])
        (directory/"evidence.json").write_bytes(evidence)
        verdict=subprocess.check_output([sys.executable,"-B",str(stock),"score",str(directory/"evidence.json"),str(directory/"contract.json")])
        (directory/"result.json").write_bytes(verdict)
        ev,res=json.loads(evidence),json.loads(verdict)
        observed=frozen["observed"]["public"]
        matched=ev["document"]["ids"]==observed["token_ids"] and ev["document"].get("terminal")==(
                 observed["finish_reason"] if observed["terminal_observed"] else None)
        loaded={row["index"]:row for row in ev["rows"]}
        equal=[]
        for row in frozen["observed"]["rows"]:
            for phase, cap in row["captures"].items():
                if row["row"] in loaded:
                    actual=loaded[row["row"]]["phases"][phase]
                    equal.append(sha256(bytes.fromhex(actual["hex"])).hexdigest()==cap["blob"])
        results.append({"case":name,"public_source":ev["public_source"],"observed_public_equal_to_freeze":matched,
                        "sampled_rows":list(loaded),"equal_phase_blobs":sum(equal),"compared_phase_blobs":len(equal),
                        "verdict":res["verdict"],"first":res["first_divergent_phase"],
                        "conflicts":res["conflicts"],"missing":res["missing"],
                        "continuation_events":{k:len(v["events"]) for k,v in ev.get("continuation",{}).items()}})
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    main(*map(Path,sys.argv[1:]))
