"""Exact minor-unit arithmetic. Injection labels never enter the blind residual locator."""
from itertools import combinations, product
import re
from html.parser import HTMLParser
from archive import sha


class Table(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.cell = None
        self.feed(raw)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.rows.append([])
        if tag in ("th", "td"):
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None:
            self.rows[-1].append(" ".join("".join(self.cell).split()))
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def minor(literal):
    """en-US cents, grouped or ungrouped ASCII digits, one unambiguous sign."""
    s = literal.strip().replace("\u2212","-")
    negative = False
    if s.startswith("(") and s.endswith(")"):
        s, negative = s[1:-1], True
    elif s.endswith("-"):
        s, negative = s[:-1], True
    elif s.startswith(("-", "+")):
        negative, s = s[0]=="-", s[1:]
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?", s):
        return None
    body, _, frac = s.replace(",", "").partition(".")
    result = int(body)*100 + int(frac.ljust(2,"0"))
    return -result if negative else result


def substitutions(literal):
    original = minor(literal)
    if original is None:
        return
    decimal = literal.find(".")
    int_end = decimal if decimal >= 0 else len(literal)
    for i, old in enumerate(literal):
        if old not in "0123456789":
            continue
        p = (2+sum(c.isascii() and c.isdigit() for c in literal[i+1:int_end]) if i<int_end
             else 2-sum(c.isascii() and c.isdigit() for c in literal[decimal+1:i+1]))
        for new in "0123456789":
            if new == old:
                continue
            changed = literal[:i]+new+literal[i+1:]
            delta = minor(changed)-original
            yield dict(original=literal, observed=changed, position=i, place=p,
                       glyph_offset=int(new)-int(old), signed_change=delta, old=old, new=new)


def decimal_offset(eps):
    if not eps:
        return None
    p = len(str(abs(eps)))-1
    u = 10**p
    if eps % u:
        return None
    return [p,eps//u]


def residual(amounts,total,balances):
    d = sum(amounts)-total if total is not None else None
    rho = None
    if balances is not None:
        assert len(balances)==len(amounts)+1
        rho = [after-before-value for before,after,value in zip(balances,balances[1:],amounts,strict=False)]
    return d,rho


def diagnose(amounts,total,balances):
    d,rho = residual(amounts,total,balances)
    r=dict(D=d,rho=rho,detected=bool(d or (rho and any(rho))),roles=[],repair=None,sign_candidate=False)
    if rho is None:
        r["reason"]="no_observed_balance_chain"
        r["body_signed_place_offset"]=decimal_offset(d)
        r["total_signed_place_offset"]=decimal_offset(-d) if d is not None else None
        return r
    nz = [(i+1,n) for i,n in enumerate(rho) if n]
    if len(nz)==1:
        (i,v), = nz
        if d in (None,-v):
            r["roles"].append(["amount",i,-v,amounts[i-1]+v])
        if d in (None,0):
            if i==1:
                r["roles"].append(["balance",0,-v,balances[0]+v])
            if i==len(amounts):
                r["roles"].append(["balance",i,v,balances[i]-v])
    elif len(nz)==2:
        (i,u),(j,v)=nz
        if j==i+1 and u==-v and d in (0,None):
            r["roles"].append(["balance",i,u,balances[i]-u])
    elif not nz and d:
        r["roles"].append(["total",0,-d,total+d])
    if len(r["roles"])==1:
        role,i,eps,restored=r["roles"][0]
        r["repair"]=dict(flagged=True,role=role,row=i,value_minor=restored,signed_place_offset=decimal_offset(eps))
        r["sign_candidate"]=bool(role=="amount" and d is not None and d==2*amounts[i-1])
    r["reason"]="unique_under_single_fault_premise" if r["repair"] else "ambiguous_or_multiple"
    return r


def grid(amount_texts,total_text,balance_texts,scope):
    a=[minor(v) for v in amount_texts]
    total=minor(total_text) if total_text is not None else None
    bs=None if balance_texts is None else [minor(v) for v in balance_texts]
    base_d,base_r=residual(a,total,bs)
    if base_d not in (None,0) or (base_r and any(base_r)) or (total is None and bs is None):
        return []
    cells=[("amount",i,amount_texts[i-1]) for i in range(2,len(a)) if total is not None]
    if bs is not None:
        cells += [("balance",i,balance_texts[i]) for i in range(1,len(a))]
    rows=[]
    for role,i,literal in cells:
        for fault in substitutions(literal):
            aa,tt,bb=list(a),total,None if bs is None else list(bs)
            val=minor(fault["observed"])
            if role=="amount":
                aa[i-1]=val
            elif role=="total":
                tt=val
            else:
                bb[i]=val
            rows.append(dict(scope=scope,kind="digit",role=role,row=i,fault=fault,observation=diagnose(aa,tt,bb)))
    if total is None or bs is None:
        return rows
    for i,literal in enumerate(amount_texts,1):
        if a[i-1]:
            aa=list(a)
            aa[i-1]=-a[i-1]
            rows.append(dict(scope=scope,kind="sign",role="amount",row=i,original=literal,observed_minor=aa[i-1],observation=diagnose(aa,total,bs)))
    for first,second in combinations(range(len(a)),2):
        for f,g in product(substitutions(amount_texts[first]),substitutions(amount_texts[second])):
            if f["place"]!=g["place"] or f["signed_change"] != -g["signed_change"]:
                continue
            aa=list(a)
            aa[first]+=f["signed_change"]
            aa[second]+=g["signed_change"]
            obs=diagnose(aa,total,bs)
            obs["single_fault_candidate"]=obs.pop("repair")
            obs["repair"]=None
            obs["reason"]="detected_multiple_fault_pattern_without_unique_cause"
            rows.append(dict(scope=scope,kind="cancelling",rows=[first+1,second+1],faults=[f,g],observation=obs))
    return rows


def physical_table(item,ptr,header):
    rows=Table(item["observed"]).rows
    assert rows and all(row for row in rows)
    own=rows[0] if rows[0][0].casefold()=="item" else None
    hdr=own or header or []
    numeric_cols=[i for i,name in enumerate(hdr) if name.casefold()=="amount"]
    balance_cols=[i for i,name in enumerate(hdr) if name.casefold() in {"balance","running balance"}]
    kinds=[]
    for row in rows:
        name=row[0].casefold()
        if name=="item":
            role="header"
        elif name in {"posting","maint-summary"}:
            role="target"
        elif name in {"total","grand total"}:
            role="total"
        elif name in {"opening balance","beginning balance"}:
            role="opening"
        else:
            role="body"
        kinds.append(role)
    amount_i=numeric_cols[0] if len(numeric_cols)==1 else None
    bodies=[v[amount_i] for v,k in zip(rows,kinds) if k=="body" and amount_i is not None and len(v)>amount_i]
    total_rows=[v for v,k in zip(rows,kinds) if k=="total"]
    total=(total_rows[0][amount_i] if amount_i is not None and kinds[-1]=="total" and len(total_rows)==1 and bodies else None)
    balances=None
    if len(balance_cols)==1 and "opening" in kinds and kinds.count("opening")==1 and bodies:
        bi=balance_cols[0]
        observed=[row[bi] for row,k in zip(rows,kinds) if k in ("opening","body") and len(row)>bi]
        if kinds.index("opening")<kinds.index("body") and len(observed)==len(bodies)+1 and all(minor(v) is not None for v in observed):
            balances=observed
    rho=None if balances is None else residual(list(map(minor,bodies)),None,list(map(minor,balances)))[1]
    return dict(ptr=ptr,raw_sha256=item["sha256"],raw_range=item["byte_range"],rows=rows,roles=kinds,
                observed_header=own,active_header=hdr,amount_index=amount_i,balance_indices=balance_cols,
                amount_literals=bodies,total_literal=total,explicit_balance_chain=balances,
                D=None if total is None else sum(map(minor,bodies))-minor(total),
                D_reason="no_in_table_amount_total_with_body" if total is None else "in_table_sum",
                rho=rho,rho_reason="no_balance_header_or_observed_b0_through_bn" if rho is None else "observed")


def archive_audit(route,physical,online):
    frames=[dict(header=None,amounts=[],sources=[],subtotal=None,unit=None) for _ in range(8)]
    controller=online.Controller()
    tables,child,checks,grids=[],[],[],[]
    for wi,tag in enumerate(route["tags"],1):
        for item in physical[tag]["spans"]:
            span=item["canonical"]
            ptr=[wi,span.page,span.index]
            depth=controller.depth
            frame=frames[depth]
            if span.kind=="block" and span.block_kind.casefold()=="table":
                header=next((f["header"] for f in reversed(frames[:depth+1]) if f["header"]),None)
                table=physical_table(item,ptr,header)
                unit=next((f["unit"] for f in reversed(frames[:depth+1]) if f["unit"]),None)
                table["unit"]=unit
                tables.append(dict(tag=tag,depth=depth,**table))
                if depth>0:
                    frame["amounts"].extend(table["amount_literals"])
                    frame["sources"].append(dict(tag=tag,ptr=ptr,table=table["raw_sha256"],unit=unit,header=table["active_header"],amount_index=table["amount_index"],body=table["amount_literals"]))
                grids.extend(grid(table["amount_literals"],table["total_literal"],table["explicit_balance_chain"],"physical"))
            for e in online.identify(span,wi):
                depth=controller.depth
                frame=frames[depth]
                controller.apply(e)
                if e.kind=="OPEN_CHILD" and controller.depth>depth:
                    frames[controller.depth]=dict(header=None,amounts=[],sources=[],subtotal=None,unit=None)
                elif e.kind in ("DECLARE_UNIT","AMEND_UNIT"):
                    frame["unit"]=e.value
                elif e.kind=="HEADER":
                    frame["header"]=list(e.value)
                elif e.kind=="TENTATIVE_CLOSE" and depth:
                    val=minor(e.value)
                    units={u["unit"] for u in frame["sources"]}
                    bound=bool(frame["sources"]) and len(units)==1 and None not in units and all(
                        u["amount_index"] is not None and u["body"] and u["header"][u["amount_index"]].casefold()=="amount" for u in frame["sources"])
                    record=dict(tag=tag,ptr=ptr,literal=e.value,minor=val,raw_slice_sha256=item["sha256"],
                                body_sources=frame["sources"],body=frame["amounts"],unit_and_amount_bound=bound,explicit_balance_chain=None,D=sum(map(minor,frame["amounts"]))-val if val is not None and bound else None)
                    child.append(record)
                    frame["subtotal"]=record
                    for r in (grid(frame["amounts"],e.value,None,"child_schedule") if bound else []):
                        grids.append(dict(**r,subtotal_ptr=ptr))
                elif e.kind=="CONFIRM_POP" and controller.depth<depth:
                    frames[controller.depth]["subtotal"]=frame["subtotal"]
                elif e.kind=="TARGET" and e.value[0].casefold()=="maint-summary":
                    sub=frame["subtotal"]
                    val=minor(e.value[1])
                    checks.append(dict(tag=tag,ptr=ptr,target_literal=e.value[1],target_minor=val,
                                       subtotal_ptr=sub["ptr"] if sub else None,subtotal_minor=sub["minor"] if sub else None,
                                       residual=val-sub["minor"] if sub and val is not None else None,
                                       raw_slice_sha256=item["sha256"],scope_reason=controller.ambiguous()))
    return dict(tables=tables,child_subtotals=child,maintenance=checks,grids=grids,final_scope=controller.ambiguous(),
                eligible_child_interior_amount_rows=sum(max(0,len(c["body"])-2) for c in child if c["D"]==0),
                full_sign_or_cancelling_gate="no_observed_b0_through_bn",
                physical_cell_gate="no_same_table_amount_total_or_explicit_running_balances")
