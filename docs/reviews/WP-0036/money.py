"""Scope-bound arithmetic audit. All values are signed integer cents."""
import re
from itertools import combinations
from inputs import sha


def cents(s):
    text=s.strip().replace("\N{MINUS SIGN}","-")
    neg=text.startswith("(") and text.endswith(")")
    if neg:
        text=text[1:-1]
    elif text.endswith("-"):
        neg=True
        text=text[:-1]
    elif text.startswith(("-", "+")):
        neg=text[0]=="-"
        text=text[1:]
    m=re.fullmatch(r"([0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:[.]([0-9]{1,2}))?",text)
    if not m:
        return None
    v=int(m[1].replace(",",""))*100+int((m[2] or "").ljust(2,"0"))
    return -v if neg else v


def single_change(delta):
    """Decode a signed value error; signed-digit offset differs on a negative literal."""
    if not delta:
        return None
    p=len(str(abs(delta)))-1
    unit=10**p
    return (p,delta//unit) if delta%unit==0 and 0<abs(delta//unit)<=9 else None


def residuals(amounts,balances):
    assert len(balances)==len(amounts)+1
    return [b-a-v for v,a,b in zip(amounts,balances,balances[1:])]


def locate(amounts, total, balances):
    d=sum(amounts)-total
    if balances is None:
        return {"discrepancy":d,"single_digit_if_single_body":single_change(d),"repair":None}
    rho=residuals(amounts,balances)
    bad=[i for i,r in enumerate(rho) if r]
    if len(bad)==1:
        i=bad[0]
        if rho[i]==-d and d:
            return dict(row=i+1,role="amount",value=amounts[i]-d,sign_flip_consistent=d==2*amounts[i],
                        numeric_place_offset=single_change(d))
        if d==0 and len(amounts)>1 and i in (0,len(rho)-1):
            return dict(index=0 if i==0 else len(amounts),role="balance",
                        value=balances[0]+rho[0] if i==0 else balances[-1]-rho[-1])
    if len(bad)==2:
        i,j=bad
        if not d and j==i+1 and rho[i]==-rho[j]:
            return dict(index=i+1,role="balance",value=balances[i+1]-rho[i])
    return dict(discrepancy=d,residuals=rho,repair=None)


def printed_changes(literal):
    value=cents(literal)
    assert value is not None
    for pos,original in enumerate(literal):
        if original not in "0123456789":
            continue
        for new in "0123456789":
            if new==original:
                continue
            corrupted=literal[:pos]+new+literal[pos+1:]
            measured=cents(corrupted)
            assert measured is not None
            p,k=single_change(measured-value)
            yield dict(before=literal,after=corrupted,char_offset=pos,original=value,observed=measured,
                       place=p,signed_value_offset=k,printed_digit_offset=int(new)-int(original))


def table_inventory(caps):
    seen={}
    for tag,c in caps.items():
        blocks=[]
        for s in c["spans"]:
            r=s["record"]
            if r["kind"]!="block" or r["block_kind"].casefold()!="table":
                continue
            lo,hi=r["byte_range"]
            rows=[(rr["record"],rr["rawsha"]) for rr in c["spans"] if rr["record"]["kind"]=="row" and
                  lo<=rr["record"]["byte_range"][0]<rr["record"]["byte_range"][1]<=hi]
            assert all(t["page"]==r["page"] for t,h in rows)
            heads=[t["cells"] for t,h in rows if t["cells"] and t["cells"][0].casefold()=="item"]
            explicit_total=[t["index"] for t,h in rows if t["cells"] and t["cells"][0].casefold() in ("total","grand total")]
            balance_cols=[i for header in heads for i,name in enumerate(header) if name.casefold() in ("balance","running balance")]
            blocks.append(dict(index=r["index"],bytes=[lo,hi],raw_sha=s["rawsha"],page=r["page"],
                               complete=s["raw"].casefold().strip().endswith("</table>"),header=heads,
                               total_rows=explicit_total,balance_columns=balance_cols,
                               rows=[dict(idx=t["index"],range=t["byte_range"],fields=t["cells"],raw_sha=h) for t,h in rows]))
        seen[tag]=blocks
    return seen


def arithmetic(route,caps,physical):
    from machine import events
    units=[None]
    child=None
    groups=[]
    uses=[]
    for wi,tag in enumerate(route["tags"],1):
        for t in physical[tag]:
            uses.append([wi,tag,t["index"],t["raw_sha"]])
        for s in caps[tag]["spans"]:
            r=s["record"]
            ptr=[wi,tag,r["page"],r["index"]]
            for kind,value,literal in events(s,wi):
                if kind=="OPEN_CHILD":
                    assert child is None
                    child=dict(open=ptr,close=None,headers=[],body=[],subtotal=None,active_header=None)
                    units.append(units[-1])
                elif kind in ("DECLARE_UNIT","AMEND_UNIT"):
                    units[-1]=value
                elif kind=="HEADER" and child is not None:
                    child["active_header"]=dict(value=value,ptr=ptr,raw_sha=s["rawsha"])
                    child["headers"].append(child["active_header"])
                elif kind=="TENTATIVE_CLOSE" and child:
                    child["subtotal"]=dict(raw=s["raw"],literal=value,value=cents(value),ptr=ptr,
                                           unit=units[-1],raw_sha=s["rawsha"])
                elif kind=="CONFIRM_POP" and child:
                    child["close"]=ptr
                    groups.append(child)
                    child=None
                    units.pop()
            if child and r["kind"]=="row" and r["cells"] and r["cells"][0].casefold() in ("service","materials"):
                header=child["active_header"]
                j=header["value"].index("Amount") if header and header["value"].count("Amount")==1 else None
                lit=r["cells"][j] if j is not None and j<len(r["cells"]) else None
                child["body"].append(dict(ptr=ptr,raw_sha=s["rawsha"],cells=r["cells"],amount=lit,
                                         value=None if lit is None else cents(lit),header=header,unit=units[-1],col=j))
    if child:
        groups.append(child)
    grid=[]
    for g in groups:
        body=g["body"]
        tot=g["subtotal"]
        ok=bool(g["close"] and tot and tot["value"] is not None and body and
                all(i["value"] is not None and i["unit"]==tot["unit"] and i["unit"] is not None for i in body) and
                len({i["col"] for i in body})==1)
        d=sum(i["value"] for i in body)-tot["value"] if ok else None
        g.update(D=d,balanced=(d==0 if ok else None),interior_rows=max(len(body)-2,0),balance_observations=None,
                 single_fault_premise="injected on internally balanced observed baseline only" if d==0 else None)
        if d==0:
            for i,item in enumerate(body[1:-1],2):
                for e in printed_changes(item["amount"]):
                    altered=[x["value"] for x in body]
                    altered[i-1]=e["observed"]
                    got=locate(altered,tot["value"],None)
                    assert got["single_digit_if_single_body"]==(e["place"],e["signed_value_offset"])
                    grid.append(dict(row=i,kind="interior_amount_D1_D2",**e,measured=got))
    # Received physical tables have neither a printed total row nor a balance series.
    assert not any(t["balance_columns"] or t["total_rows"] for tag in route["tags"] for t in physical[tag])
    return dict(binder=route["binder"],table_uses=uses,schedules=groups,grid=grid,
                missing=dict(physical_D="No observed body plus in-table total row",
                             rho="No explicit b0..bn series",D3_D4="No balance series",
                             D4_1="Sign recovery requires a verified total and balance series",
                             D5="Dual residual detection requires an observed balance series"))
