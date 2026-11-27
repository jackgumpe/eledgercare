"""Durable ordered child transitions on Windows' cross-process monotonic clock."""
import json
import time

MAX_JOURNAL_BYTES=256*1024
NS=1_000_000_000


def mark(folder,phase,tokens=0):
    payload=json.dumps([time.monotonic_ns(),phase,tokens],separators=(",",":")).encode("ascii")+b"\n"
    with (folder/"phase").open("xb" if phase=="load" and not tokens else "ab") as dest:
        if dest.tell()+len(payload)>MAX_JOURNAL_BYTES:
            raise RuntimeError("timing journal capacity")
        dest.write(payload)


def read_timing(folder):
    path=folder/"phase"
    if not path.exists():
        return b""
    with path.open("rb") as stream:
        data=stream.read(MAX_JOURNAL_BYTES+1)
    if len(data)>MAX_JOURNAL_BYTES:
        raise RuntimeError("timing journal capacity")
    return data


def timeline(data,arm,labels,limits,origin,now,finished=False):
    if type(origin)!=int or type(now)!=int or not 0<origin<=now:
        raise ValueError("invalid supervisor monotonic interval")
    phases=("preflight","load",*labels,"finished")
    index=0
    entered=progress=last=origin
    count=0

    def deadline():
        phase=phases[index]
        total=limits["call_s" if phase in labels else "load_s"]
        end=entered+int(total*NS)
        return min(end,progress+int(limits["stall_s"]*NS)) if phase in labels else end

    lines=data.split(b"\n")
    if lines.pop() and finished:
        raise ValueError("final timing receipt truncated")
    for raw in lines:
        stamp,phase,tokens=json.loads(raw)
        if type(stamp)!=int or not last<=stamp<=now or type(tokens)!=int:
            raise ValueError("invalid worker timing coordinate")
        if stamp>deadline():
            raise ValueError("completed phase exceeded deadline: "+phases[index])
        if tokens==0:
            if index+1>=len(phases) or phase!=phases[index+1]:
                raise ValueError("phase schedule discontinuity")
            index+=1
            entered=progress=stamp
            count=0
        else:
            if not (arm=="observed" and phase==phases[index]==labels[-1] and tokens==count+16):
                raise ValueError("unbound append progress")
            count=tokens
            progress=stamp
        last=stamp
    if now>deadline():
        raise ValueError("current phase exceeded deadline: "+phases[index])
    if finished and index!=len(phases)-1:
        raise ValueError("final phase receipt missing")
    return deadline()
