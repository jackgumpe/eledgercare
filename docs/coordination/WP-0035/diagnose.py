"""Describe changes in the observed owner separation at fixed readout and fixed write regime."""
import argparse
import json
from pathlib import Path

FIELDS = ("alpha","beta","delta","mu","gamma","wins")


def diagnostic(data):
    checkpoints = {(r["pair"],r["model"],r["write"],r["read"],r["phase"],r["step"]):r for r in data["checkpoints"]}
    profiles = []
    for key, terminal in checkpoints.items():
        pair, model, write, read, phase, step = key
        if phase != "native_pre":
            continue
        def point(t):
            return checkpoints[(pair, model, write, read, "post", t)]
        eight, eleven = point(8), point(11)
        magnitude8 = abs(eight["delta"])
        change = None if magnitude8 == 0 else 100*(1-abs(eleven["delta"])/magnitude8)
        profiles.append({"pair":pair,"horizon":terminal["horizon"],"model":model,"write":write,"read":read,
                         "delta_at_8":eight["delta"],"delta_at_11":eleven["delta"],"delta_at_posting":terminal["delta"],
                         "delta_magnitude_loss_8_to_11_percent":change,"delta_signed_change_8_to_11":eleven["delta"]-eight["delta"],
                         "mu_at_8":eight["mu"],"mu_at_11":eleven["mu"],"mu_at_posting":terminal["mu"],
                         "gamma_at_8":eight["gamma"],"gamma_at_11":eleven["gamma"],"gamma_at_posting":terminal["gamma"],
                         "member_wins_at_8_9_11_12_posting":[point(t)["wins"] for t in (8,9,11,12)]+[terminal["wins"]]})
    rows={(r["task"], r["pair"],r["model"],r["write"],r["read"]):r for r in data["terminal_pair_contrasts"]}
    effects=[]
    for (task,pair,model,write,read), after in rows.items():
        references=[]
        if write != "W0":
            references.append(({"W1":"W0","W2a":"W1","W2b":"W2a"}[write],read))
        if read=="R1":
            references.append((write,"R0"))
        for base_w,base_r in references:
            before=rows[(task,pair,model,base_w,base_r)]
            effects.append({"task":task,"pair":pair,"horizon":after["horizon"],"model":model,"from":[base_w,base_r],
                            "to":[write,read],"differences":{f:after[f]-before[f] for f in FIELDS},
                            "simultaneous_before":before["wins"]==2,"simultaneous_after":after["wins"]==2})
    return {"delta_convention":"Alder-true literal margin minus Cedar-true literal margin; loss uses 100*(1-|delta11|/|delta8|). A sign change is recorded separately in the signed values.",
            "profiles":profiles,"terminal_paired_effects":effects}


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("reconciliation",type=Path)
    cli.add_argument("output",type=Path)
    args=cli.parse_args()
    data=diagnostic(json.loads(args.reconciliation.read_bytes()))
    with args.output.open("x",encoding="utf8",newline="\n") as out:
        json.dump(data,out,allow_nan=False,separators=(",",":"))
        out.write("\n")
    print(len(data["profiles"]),"Task A profiles and",len(data["terminal_paired_effects"]),"paired terminal comparisons")
