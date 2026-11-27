"""Two tiny stock-like greedy decoders. A program supplies scores, never an expected document."""
import struct
from capture import pack_word


def execute(program,eos,page):
    prefix=program["prefix"]
    if not isinstance(prefix,list) or any(type(x)!=int or x<0 or x==eos for x in prefix):
        raise ValueError("invalid initial generated history")
    limit=program["limit"]
    if type(limit)!=int or not 0<=limit<=100000:
        raise ValueError("invalid continuation step limit")
    generated=list(prefix)
    events=[]
    finish=None
    interruption=None
    for i in range(limit):
        if program.get("interrupt_before")==i or i>=len(program["steps"]):
            interruption=i
            break
        step=program["steps"][i]
        last=generated[-1] if generated else None
        pairs=step.get("by_previous",{}).get(str(last),step.get("scores"))
        if not isinstance(pairs,list) or not pairs:
            raise ValueError("missing scores for live continuation state")
        pairs=sorted(pairs,key=lambda pair:pair[0])
        ids=[p[0] for p in pairs]
        if any(type(t)!=int or t<0 for t in ids) or len(set(ids))!=len(ids):
            raise ValueError("invalid continuation score domain")
        raw=b"".join(pack_word(w) for _,w in pairs)
        values=[v for v, in struct.iter_unpack("<f",raw)]
        winner=ids[max(range(len(ids)),key=values.__getitem__)]
        event={"step":i,"before":len(generated),"previous":last,"domain":ids,"f32le":raw.hex(),"selected":winner}
        if winner==eos:
            finish="stop"
            event.update(action="stop",after=len(generated))
            events.append(event)
            break
        generated.append(winner)
        event.update(action="append",after=len(generated))
        events.append(event)
    else:
        finish="length"
    doc={"ids":generated,"markers":[i for i,t in enumerate(generated) if t==page],"output_tokens":len(generated)}
    if finish is not None:
        doc["terminal"]=finish
    if "pieces" in program:
        doc["text"]="".join(program["pieces"][str(t)] for t in generated)
    result={"prefix":prefix,"limit":limit,"events":events,"interrupted_at":interruption,"document":doc}
    if "pieces" in program:
        result["pieces"]=program["pieces"]
    return result
