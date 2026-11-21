"""Read-only digest and modification-time inventory for the immutable Q0 model tree."""
from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path


def inventory(root):
    rows={}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Unexpected symbolic link {path}")
        if path.is_file():
            st=path.stat()
            with path.open("rb") as stream:
                digest=hashlib.file_digest(stream,"sha256").hexdigest()
            assert st.st_mtime_ns==path.stat().st_mtime_ns and st.st_size==path.stat().st_size
            rows[path.relative_to(root).as_posix()]=dict(sha256=digest,bytes=st.st_size,mtimeNs=st.st_mtime_ns)
    return {"files":rows,"directories":sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_dir())}


if __name__=="__main__":
    ap=ArgumentParser(description=__doc__)
    ap.add_argument("root",type=Path);ap.add_argument("out",type=Path);ap.add_argument("--compare",type=Path)
    args=ap.parse_args()
    data=inventory(args.root)
    if args.compare and data!=json.loads(args.compare.read_bytes()):
        raise ValueError("Q0 model file content, tree or last-write time changed")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("xb") as stream:
        stream.write((json.dumps(data,indent=2)+"\n").encode())
    print(len(data["files"]), "read-only files verified")
