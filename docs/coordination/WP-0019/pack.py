"""Retain exact synthetic output bytes, with a digest for each original and gzip object."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main(source, destination, names):
    source=source.resolve()
    destination.mkdir(parents=True,exist_ok=False)
    receipt=[]
    for name in names:
        entry=Path(name)
        if entry.is_absolute() or '..' in entry.parts:raise ValueError(name)
        data=(source/entry).read_bytes()
        json.loads(data)
        stored=destination/(entry.as_posix()+'.gz')
        stored.parent.mkdir(parents=True,exist_ok=True)
        packed=gzip.compress(data,compresslevel=6,mtime=0)
        if gzip.decompress(packed)!=data:raise ValueError(name)
        stored.write_bytes(packed)
        receipt.append(dict(path=entry.as_posix(),uncompressed_bytes=len(data),sha256=digest(data),
                            gzip_sha256=digest(packed),gzip_bytes=len(packed)))
    (destination/'receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('names',nargs='+')
    a=p.parse_args();main(a.source,a.destination,a.names)
