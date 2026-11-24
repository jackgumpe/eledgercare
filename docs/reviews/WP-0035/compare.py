"""Compare public operator outputs by declared keys, preserving signed binary64 zero."""
import gzip
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INDEPENDENT = "43a3464b50154a1d800ce9fe3b56f3c226e574b4"
KEY = ["task","pair","horizon","model","write","read"]
POINT = ["phase","step"]
SCHEMA = {
    "scores":(KEY+["binder"]+POINT, ["score_hex","top","gap","score_pass","gap_pass"]),
    "contrasts":(KEY+POINT, ["alpha","beta","delta","mu","gamma","wins"]),
    "terminals":(KEY+["binder"], ["typed"]),
    "custody":(["pair"], ["horizon","tier","answerable","members"])
}


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT)


def rows(rev, folder, name):
    stem=folder+"/evidence/"+name+".json"
    files=git("ls-tree","-r","--name-only",rev,"--",stem,stem+".gz").decode().splitlines()
    path,=files
    data=git("cat-file","blob",rev+":"+path)
    payload=gzip.decompress(data) if path.endswith(".gz") else data
    return json.loads(payload),dict(revision=rev,path=path,sha256=hashlib.sha256(data).hexdigest())


def equality(a,b):
    if isinstance(a,float) or isinstance(b,float):
        return not isinstance(a,bool) and not isinstance(b,bool) and struct.pack("<d",a)==struct.pack("<d",b)
    if isinstance(a,dict):
        return isinstance(b,dict) and a.keys()==b.keys() and all(equality(a[k],b[k]) for k in a)
    if isinstance(a,list):
        return isinstance(b,list) and len(a)==len(b) and all(equality(x,y) for x,y in zip(a,b))
    return type(a)==type(b) and a==b


def index(items,fields):
    indexed={tuple(item[k] for k in fields):item for item in items}
    assert len(items)==len(indexed)
    return indexed


def compare(author):
    result={}
    for name,(key,fields) in SCHEMA.items():
        a,ar=rows(author,"docs/research/WP-0035",name)
        b,br=rows(INDEPENDENT,"docs/reviews/WP-0035",name)
        left,right=index(a,key),index(b,key)
        missing=sorted(left.keys()^right.keys())
        errors=[]
        for identity in sorted(left.keys()&right.keys()):
            for f in fields:
                x,y=left[identity][f],right[identity][f]
                if not equality(x,y):
                    errors.append(dict(identity=identity,field=f,author=x,independent=y))
        result[name]=dict(author=ar,independent=br,key=key,fields=fields,author_rows=len(a),review_rows=len(b),
            missing=missing,errors=errors,matched=len(left.keys()&right.keys()),passed=not missing and not errors)
    return result


if __name__=="__main__":
    data=compare(sys.argv[1])
    (HERE/"evidence"/"cross-check.json").write_bytes((json.dumps(data,sort_keys=True,indent=2)+"\n").encode())
    assert all(v["passed"] for v in data.values())
