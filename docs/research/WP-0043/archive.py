"""Derive five field positions, supports, byte coordinates and storage from pinned Git objects."""
import json
from itertools import product
from collections import Counter
from native_score import archived
from scorer import support

def main():
    doc,p=archived("F07.warm1")
    ids=doc["ids"]
    raw=doc["text"].encode()
    rows=[]
    for g in range(618,623):
        h=ids[:g+1]
        longest=max((n for n in range(1,35) if any(h[j:j+n]==h[-n:] for j in range(len(h)-n))),default=0)
        rows.append({"consumed":g,"t":p+g,"y":ids[g+1],"length":len(h),"starts":len(h)-34,
                     "longest":longest,"banned":sorted(support(h,{"order":35,"window":1024})),
                     "page_markers":h.count(128827),"page_len":h[::-1].index(128827),"expected_pages":doc["expected_pages"]})
    c=2*10*128*2+128*4
    payload=sum((24*t+23)*c for t in range(1445,1450))
    print(json.dumps({"rows":rows,"starts":sum(v["starts"] for v in rows),"ids":len(ids),"bytes":len(raw),
       "target":raw[1823:1838].decode(),"net_line":raw[1880:1886].decode(),"markers":doc["markers"],
       "logical_cache_bytes":payload,"score_bytes":15*129280*4,"verdict_counts":dict(Counter(
       min(a,key="MUP".index) for a in product("MUP",repeat=5)))},indent=2))

if __name__=="__main__":
    main()
