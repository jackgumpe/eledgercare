"""Worked counterexamples for the research paper. Standard Python, synthetic inputs.
Run with python six_controls.py. No checkpoint, GPU, or physical pages are used.
"""
from collections import defaultdict
from copy import deepcopy
from itertools import product
from math import inf, isfinite
from struct import pack, unpack

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def banned(history, order, window):
    seq = history[-window:]
    suffix = seq[-(order-1):]
    return {seq[i+order-1] for i in range(len(seq)-order+1)
            if seq[i:i+order-1] == suffix}

def snapshot():
    t=1448
    lengths=(t+1,)*11+(t,)
    suffix=list(range(100,134))
    first=suffix+[1328]+suffix
    second=suffix+[6]+suffix
    require(1328 in banned(first,35,128) and 1328 not in banned(second,35,128),
            '35-gram histories must distinguish the allowed score')
    require(not banned([6,1449,16,1328]*2,35,128), 'a repeated price is too short')
    require(lengths[-1]==1448 and sum(v==1449 for v in lengths)==11,'asymmetric entry')
    # Seen tokens is derived here. Omitting a redundant field cannot split a fiber.
    states=[(t,guard,t+1) for t,guard in product(range(2),repeat=2)]
    def sufficient(record):
        fibers=defaultdict(set)
        for t,c,seen in states:
            fibers[record(t,c,seen)].add((t+1,c))
        return all(len(s)==1 for s in fibers.values())
    require(sufficient(lambda t,c,v:(t,c)) and not sufficient(lambda t,c,v:(t,v)),
            'redundancy and a separating omitted guard')
    return '11 advanced layers, one pending layer; 35-gram collision and redundant-field control'

def storage():
    def one(mode):
        source=bytearray([10,20,30,40])
        bindings={'idx':(0,1)}
        private=source if mode=='shared' else bytearray(source)
        other=bytearray(private) if mode=='split' else private
        private_map=bindings if mode=='shared' else deepcopy(bindings)
        u=memoryview(private)[:3]; v=memoryview(other)[1:]
        u[1]=99
        private_map['idx']+=(2,)
        return v[0],source[1],len(bindings['idx'])
    require([one(m) for m in ('faithful','split','shared')]==[(99,20,2),(20,20,2),(99,99,3)],
            'view alias and container rebinding')
    offs=(1445*128*2,1445*10*128*2,1445*128*4)
    require(offs==(369920,3699200,739840),'layout-dependent offsets')
    return 'three distinct alias outcomes; two K layouts and one selected DASH address'

def rollover():
    def step(entry):
        length,counter,blocks=entry
        out=dict(blocks); b=length//32; out[b]=out.get(b,0)+1
        return length+1,counter+1,out
    entry=(31,30,{0:31})
    a=step(entry); b=step(entry); double=step(a)
    require(a==b==(32,31,{0:32}) and double==(33,32,{0:32,1:1}),'append history')
    require((32,double[1],double[2])!=a and entry==(31,30,{0:31}),'trim cannot undo side state')
    return 'index 31 completes block 0; erroneous index 32 creates block 1'

def linked():
    def trial(local,bridge):
        b=30; trace=[]
        for k in range(5):
            s=b+1+(local if k==0 else 0)
            n=s+(bridge if k==0 else 0)
            trace.append((b,s,n)); b=n
        return trace
    ref=trial(0,0)
    bridge=trial(0,1); block=trial(1,0); comp=trial(1,-1)
    require(bridge[0][:2]==ref[0][:2] and bridge[1][0]==32 and ref[1][0]==31,'bridge first difference')
    require(block[0][0]==ref[0][0] and block[0][1]!=ref[0][1],'transition first difference')
    require(comp[0][1]!=ref[0][1] and all(x[0]==y[0] for x,y in zip(comp,ref)),'compensation')
    require(all((n,n+1)==r[:2] for n,r in zip(range(30,35),ref)),'anchored rows')
    return 'local, inter-step and compensated faults separate at the predicted cuts'

def scores():
    def observe(scores):
        owned=tuple(scores); alias=scores; scores[1]=-inf
        return owned,tuple(alias)
    require(observe([4,3])==((4,3),(4,-inf)) and observe([4,2])==((4,2),(4,-inf)), 'raw copy')
    def valid(raw,z,allowed):
        return bool(allowed) and all(isfinite(x) for x in raw) and all(
            isfinite(x) if i in allowed else x==-inf for i,x in enumerate(z))
    require(valid([4,3],[4,-inf],{0}) and not valid([4,3],[4,-inf],{0,1}),'mask membership')
    nan=unpack('<f',bytes.fromhex('0100c07f'))[0]
    require(pack('<f',nan)==pack('<f',nan) and not valid([nan,3],[4,-inf],{0}),'identical NaN')
    require(not valid([4,3],[-inf,-inf],set()),'no allowed token')
    require(pack('<f',+0.)!=pack('<f',-0.),'signed zero')
    payload=bytes(16)
    require(((2,2),payload)!=((4,),payload),'shape')
    changed=[i for i,(a,b) in enumerate(zip(pack('<f',0),pack('<f',-inf))) if a!=b]
    require(changed==[2,3],'first different byte')
    return 'pre-mask capture, finite/allowed predicate, signed zero, shape and byte witness'

def verdict():
    fail,unknown,passed=range(3)
    def atom(observed,meets): return unknown if not observed else (passed if meets else fail)
    for xs in product(range(3),repeat=5):
        want=fail if fail in xs else unknown if unknown in xs else passed
        require(min(xs)==want,'finite conjunction')
    missing=atom(False,None); mismatch=atom(True,False)
    require(min(passed,missing,mismatch)==fail and min(passed,passed,missing)==unknown,'partial or absent P2b')
    require(min([passed]*5+[passed,passed,passed,unknown])==unknown,'absent continuation')
    require(min([passed]*9)==passed,'complete toy run')
    return '243 five-row verdict combinations plus incomplete, conflicting and complete field examples'

if __name__=='__main__':
    for i,check in enumerate([snapshot,storage,rollover,linked,scores,verdict],1):
        print(f'CPU-{i} PASS | {check()}')
