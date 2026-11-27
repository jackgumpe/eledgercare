"""Post-opening reconciliation. Keys and controls are joined from committed rows, never from case labels in scoring."""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import struct
import subprocess
import sys

def read(p):
    return json.loads(p.read_bytes())

def write(p,val):
    p.write_text(json.dumps(val,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

def keyed(seq):
    return {x['id']:x for x in seq}

def flatten(e,o,path='',missing=None):
    absent={'field_absent':True}
    if isinstance(e,dict) and isinstance(o,dict):
        out=[]
        for k in sorted(e.keys()|o.keys()):
            place=path+'/'+k
            if k not in o:
                out.append({'path':place,'expected':e[k],'returned':absent})
            elif k not in e:
                out.append({'path':place,'expected':absent,'returned':o[k]})
            else:
                out.extend(flatten(e[k],o[k],place))
        return out
    if isinstance(e,list) and isinstance(o,list):
        if path in ('/missing','/conflicts'):
            return flatten({x['key']:x for x in e},{x['key']:x for x in o},path)
        return flatten({str(i):x for i,x in enumerate(e)},{str(i):x for i,x in enumerate(o)},path)
    return [] if type(e)==type(o) and e==o else [{'path':path,'expected':e,'returned':o}]

def core(r):
    return {**{k:r[k] for k in ('coordinates','content','joint','custody')},
            **{k:sorted(x['key'] for x in r[k]) for k in ('conflicts','missing')}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expected',type=Path,required=True)
    p.add_argument('--directory',type=Path,required=True)
    ns=p.parse_args()
    ex=keyed(read(ns.expected)['rows'])
    directory=ns.directory
    both={r:keyed(read(directory/(r+'-observed.json'))['rows']) for r in ('author','reviewer')}
    result={}; counts={}
    for role,rows in both.items():
        cmp=keyed(read(directory/(role+'-comparison.json'))['rows'])
        count={i:{k:0 for k in ('complete','coordinates_content_verdicts','atom_key_sets','core','scheduled')}
               for i in ('live','constructed','archive','mathematical')}
        for k,e in ex.items():
            o=rows[k]
            iface=e['interface']
            count[iface]['scheduled']+=1
            count[iface]['complete']+=cmp[k]['status']=='match'
            differences=[delta for f,okay in cmp[k]['fields'].items() if not okay for delta in
                         flatten(e[f],o.get(f,{'field_absent':True}),'/'+f)]
            rec={'complete':cmp[k]['status']=='match','differing_fields':differences}
            if 'coordinates' in e:
                a,b=core(e),core(o)
                keys_equal=all(a[v]==b[v] for v in ('conflicts','missing'))
                num_equal=all(a[v]==b[v] for v in ('coordinates','joint','custody','content'))
                rec.update(coordinates_content_verdicts=num_equal,atom_key_sets=keys_equal,core=a==b)
                for name,value in rec.items():
                    if name in ('coordinates_content_verdicts','atom_key_sets','core'):
                        count[iface][name]+=value
            result.setdefault(k,{'interface':iface})[role]=rec
        for iface in ('archive','mathematical'):
            for name in ('coordinates_content_verdicts','atom_key_sets','core'):
                count[iface][name]=None
        counts[role]=count
    for k,e in ex.items():
        if 'coordinates' in e:
            a,b=[core(both[r][k]) for r in ('author','reviewer')]
            state=all(a[v]==b[v] for v in ('coordinates','joint','custody','content'))
            keys=all(a[v]==b[v] for v in ('conflicts','missing'))
            result[k]['routes']=dict(coordinates_content_verdicts=state,atom_key_sets=keys,core=a==b)
    pair={i:{f:sum(v['routes'][f] for v in result.values() if v['interface']==i) for f in ('coordinates_content_verdicts','atom_key_sets','core')} for i in ('live','constructed')}
    write(directory/'field-differences.json',{'counts_vs_oracle':counts,'agreement_between_routes':pair,'cases':result})
    print(json.dumps(pair))
    print(json.dumps(counts))

if __name__=='__main__':
    main()
