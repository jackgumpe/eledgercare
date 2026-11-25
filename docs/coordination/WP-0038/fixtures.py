"""Build the synthetic census and scoring join, independently of either solver."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path


def labels(n):
    return [f"A{i}" for i in range(1,n+1)] + [f"B{i}" for i in range(n+1)] + ["T"]


def fixture(name, section, domain, n, changes, variant=""):
    amounts = [11,17,23][:n]
    balances = [100]
    for a in amounts:
        balances.append(balances[-1]+a)
    cells = labels(n)
    truth = dict(zip(cells, amounts+balances+[sum(amounts)], strict=True))
    observed = {k: v+changes.get(k,0) for k,v in truth.items()}
    observation = {"domain": domain, "amounts": [observed[k] for k in cells[:n]],
                   "balances": [observed[k] for k in cells[n:-1]], "total": observed["T"],
                   "anchor": 100 if domain=="TRUSTED_OPEN" else None}
    return {"id": name, "variant": variant, "section": section, "observed": observation,
            "truth": truth, "injection": changes}


def cases():
    rows = []
    for n in (1,2,3):
        for domain in ("OCR_OPEN","TRUSTED_OPEN"):
            cells = [k for k in labels(n) if k!="B0" or domain=="OCR_OPEN"]
            edits = [{}] + [{k:6} for k in cells]
            for a,b in itertools.combinations(cells,2):
                edits.extend([{a:6,b:e} for e in (6,-6,10)])
            for i,change in enumerate(edits):
                rows.append(fixture(f"grid/{domain}/{n}/{i:03d}","grid",domain,n,change))
    named = [
        ("C1",1,{"B0":6,"B1":6}), ("C2",1,{"B1":6}), ("C3",2,{"B1":6}),
        ("C4",2,{"A1":-6,"T":-6}), ("C5",3,{"A1":-6,"T":-6}),
        ("C6",3,{"B1":-6,"B3":-6}), ("C7",3,{"A1":6,"B3":-6}), ("C8",3,{"A1":6,"B3":10})]
    for name,n,edits in named:
        rows.append(fixture(name,"named","OCR_OPEN",n,edits,"ocr"))
        if name=="C1":
            rows.append(fixture(name,"named","TRUSTED_OPEN",1,{},"consistent_zero"))
            rows.append(fixture(name,"named","TRUSTED_OPEN",1,edits,"actual_conflict"))
        else:
            rows.append(fixture(name,"named","TRUSTED_OPEN",n,edits,"trusted"))
    rows.append(fixture("C9a","named","OCR_OPEN",1,{"A1":6,"B0":10},"ocr"))
    rows.append(fixture("C9b","named","TRUSTED_OPEN",1,{"A1":6,"B1":-10},"trusted"))
    rows.append(fixture("C9c","named","TRUSTED_OPEN",1,{"A1":6,"B0":10},"actual_conflict"))
    assert len(rows)==308 and sum(r["section"]=="grid" for r in rows)==288
    return rows


def encoded(obj):
    return json.dumps(obj,separators=(",",":"),sort_keys=True,allow_nan=False).encode("utf-8")


def observation_order(rows):
    # The permutation only orders records. IDs and injection labels never enter the solver input.
    return sorted(range(len(rows)),key=lambda i:hashlib.sha256(b"D53-ed03-order\0"+str(i).encode()).digest())


def write_inputs(path):
    records=cases()
    order=observation_order(records)
    payload=b"".join(encoded(records[i]["observed"])+b"\n" for i in order)
    with path.open("xb") as stream:
        stream.write(payload)
    print(hashlib.sha256(payload).hexdigest(), len(records))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("observations",type=Path)
    write_inputs(cli.parse_args().observations)
