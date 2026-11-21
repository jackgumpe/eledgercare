"""Preserve complete or interrupted signed output, its guarded order and source inputs in bounded ZIPs."""
import argparse
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import HOST, cpu, pinned, read, save, sha

LIMIT = 40 * 1024 * 1024

def local_files(root):
    for path,dirs,files in os.walk(root,followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.casefold() != "cache")
        for name in sorted(files):
            p = Path(path)/name
            assert p.resolve().is_relative_to(root.resolve()) and not p.is_symlink()
            yield p

def write_parts(entries,output):
    output.mkdir(parents=True,exist_ok=False)
    members,parts = {},[]
    part = None
    accumulated = 0
    try:
        for name,path in sorted(entries.items()):
            size = path.stat().st_size
            if part is None or accumulated+size > LIMIT:
                if part:
                    part.close()
                zip_name = f"primary-{len(parts)+1:03d}.zip"
                parts.append(zip_name)
                part = ZipFile(output/zip_name,"x",compression=ZIP_DEFLATED,compresslevel=6)
                accumulated = 0
            raw = path.read_bytes()
            part.writestr(name,raw)
            members[name] = {"part":zip_name,"bytes":size,"sha256":sha(raw)}
            accumulated += size
    finally:
        if part:
            part.close()
    rechecked = {}
    for file in parts:
        zpath = output/file
        with ZipFile(zpath) as z:
            assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist()))
            for name in z.namelist():
                raw = z.read(name)
                assert members[name] == {"part":file,"bytes":len(raw),"sha256":sha(raw)}
                rechecked[name] = True
        assert zpath.stat().st_size < 95*1024*1024
    assert rechecked.keys() == entries.keys()
    return {"parts":{f:{"bytes":(output/f).stat().st_size,"sha256":sha((output/f).read_bytes())} for f in parts},
            "members":members}

def archive(release_file,pin,output):
    release = pinned(release_file,pin)
    assert release["packet"] == "WP-0026" and release["operator"] == "eld-rd-reviewer"
    label = release["name"]
    assert Path(label).name == label
    lease = HOST/"coordination/leases"/label
    entries = {"binding/"+release_file.name:release_file}
    for p in local_files(lease):
        entries["guard/"+p.relative_to(lease).as_posix()] = p
    op = HOST/"review/operator"/label
    for p in local_files(op):
        entries["operator/"+p.relative_to(op).as_posix()] = p
    failures,orders = [],{}
    for order in release["orders"]:
        name = order["run"]
        run = Path(order["output"])
        assert run == HOST/"review/runs"/name and Path(name).name == name
        plan_file = Path(order["plan"])
        plan = pinned(plan_file,order["plan_sha256"])
        entries["binding/"+plan_file.name] = plan_file
        assert Path(plan["output"]) == run
        artifacts = [(Path(r["pdf"]),r["sha256"]) for r in plan["requests"]]
        for pages in [plan["warmup"]["pages"],*[c["pages"] for c in plan["calls"]]]:
            artifacts.extend((Path(p["image"]),p["sha256"]) for p in pages)
        for path,expected in set(artifacts):
            key = f"inputs/{expected}{path.suffix}"
            if not path.is_file():
                failures.append({"path":str(path),"error":"missing input"})
                continue
            actual = sha(path.read_bytes())
            if actual != expected:
                failures.append({"path":str(path),"expected":expected,"actual":actual})
                key = f"inputs/changed-{actual}{path.suffix}"
            entries[key] = path
        for p in local_files(run):
            entries["runs/"+name+"/"+p.relative_to(run).as_posix()] = p
        sensor = run/"sensor"
        tags = [c["tag"] for c in plan["calls"]]
        wall, begin, complete = {}, [], []
        for tag in tags:
            if (sensor/(tag+"-begin.json")).is_file():
                begin.append(tag)
            duration = sensor/tag/"duration.json"
            if duration.is_file():
                d = read(duration)
                wall[tag] = {k:d[k] for k in ("start_utc_ns","end_inference_utc_ns","end_capture_utc_ns",
                                              "wall_inference_ns","complete_window_wall_ns")}
            if (sensor/tag/"receipt.json").is_file():
                complete.append(tag)
        get = lambda f: read(sensor/(f+".json")) if (sensor/(f+".json")).is_file() else None
        ret = lease/(name+"-returned.json")
        samples = lease/(name+"-device.jsonl")
        board = [json.loads(x) for x in samples.read_bytes().splitlines() if x] if samples.is_file() else []
        orders[name] = {"expected_scored_calls":len(tags),"starts":begin,"scored_receipts_present":complete,
                        "scored_window_clocks":wall,"scored_inference_s":sum(d["wall_inference_ns"] for d in wall.values())/1e9,
                        "scored_complete_window_s":sum(d["complete_window_wall_ns"] for d in wall.values())/1e9,
                        "cold":get("cold"),"warmup":get("warmup"),"error":get("error"),
                        "guard_return":read(ret) if ret.is_file() else None,"samples":len(board),
                        "max_board_used_mib":max((b["used_mib"] for b in board),default=None)}
    inv = write_parts(entries,output)
    result = {"release":label,"release_sha256":pin,"candidate":release["review_worktree_head"],"orders":orders,
              "input_discrepancies":failures,"guard_return":read(lease/"returned.json") if (lease/"returned.json").is_file() else None,
              **inv}
    save(output/"inventory.json",result)
    return result

if __name__ == "__main__":
    cpu()
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("release",type=Path)
    cli.add_argument("sha")
    cli.add_argument("output",type=Path)
    a = cli.parse_args()
    archive(a.release,a.sha,a.output)
