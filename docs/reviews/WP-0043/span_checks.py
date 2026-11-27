"""Enumerate small physical layouts independently of producer address coalescing."""
from itertools import product
import json
from pathlib import Path
import sys


def main(src):
    sys.path.insert(0,str(src))
    from transfer import spans
    count=0
    for rank in range(4):
        for shape in product(range(4),repeat=rank):
            for stride in product(range(4),repeat=rank):
                for width in (1,2,4):
                    addresses=[]
                    for position in product(*(range(n) for n in shape)):
                        start=width*(2+sum(a*b for a,b in zip(position,stride)))
                        addresses.extend(range(start,start+width))
                    storage=max(addresses,default=0)+1
                    pieces=list(spans(shape,stride,width,2,storage,65536))
                    actual=[a for first,n in pieces for a in range(first,first+n)]
                    assert actual==addresses, (shape,stride,width)
                    count+=1
    for shape,stride,offset,storage,span_limit in [((4,),(1,),-1,32,1),
            ((3,),(-1,),2,32,1),((4,),(2,),0,24,10),((3,3),(1,3),0,36,8)]:
        try:
            list(spans(shape,stride,4,offset,storage,span_limit))
        except ValueError:
            continue
        raise AssertionError((shape,stride))
    print(json.dumps({"accepted_logical_layouts":count,"rejected_malformed_or_over_budget":4,
                      "scope":"CPU address arithmetic only; no actual transfer"}))


if __name__=="__main__":
    main(Path(sys.argv[1]))
