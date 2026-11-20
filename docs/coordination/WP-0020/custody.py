"""Admit committed H/A observations. The Windows phase never reads neural predictions or keys."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ASTRA = ROOT / "docs/research/WP-0015/astra"
RUNS = {"H": ("h-r1-ab", 4, "H-blind-inventory.json", "bd48af1a7f968b2231fe1d870a22c88f265ae347"),
        "A": ("a-recovery-ab", 60, "A-recovery-blind-inventory.json", "ce4206f20d63101f6344121eaaeeeb86d2ec85a0")}

def sha(data): return hashlib.sha256(data).hexdigest()

def git_bytes(rev, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", rev + ":" + path])

def write(path, data):
    if not isinstance(data, bytes):
        data = (json.dumps(data, ensure_ascii=True, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data: raise ValueError(f"Different existing output {path}")
    else:
        with path.open("xb") as stream: stream.write(data)

def checked(data, expected, label):
    if sha(data) != expected: raise ValueError(f"Digest mismatch for {label}")
    return data

def page_projection(raw, archived):
    if str(ASTRA) not in sys.path: sys.path.insert(0, str(ASTRA))
    from formats import native_page
    parserdir = ASTRA / "sensitivity-title-level"
    if str(parserdir) not in sys.path: sys.path.insert(0, str(parserdir))
    from rescore import TITLE
    text = raw["raw_output"]
    assert native_page(text, raw["points"]) == {k:archived[k] for k in ("text","spans","tables")}
    return dict(archived, **native_page(TITLE.sub(r"\1", text), raw["points"]))

def process(mode, archive, scratch, receipt):
    result = {}
    for family, (run, count, inventory, rev) in RUNS.items():
        inv = git_bytes(rev, "docs/reviews/WP-0015/evidence/" + inventory)
        record, = [r for r in json.loads(inv)["runs"] if r["run"]==run]
        root = archive/"runs"/run
        windows_folder = f"04-{family.lower()}-windows"
        native_folder = f"03-{family.lower()}-native"
        files = {}
        def source(relative):
            data = checked((root/relative).read_bytes(), record["files"][relative], relative)
            files[relative] = sha(data)
            return data
        plan = json.loads(checked((root/"plan.json").read_bytes(), record["plan_sha256"], "plan"))
        req = plan["requests"][2]
        assert (req["mode"],req["warmup"],req["label"],req["pages"])==("native",False,family.lower(),count)
        assert plan["requests"][3]["mode"]=="windows" and req["sha256"]==plan["requests"][3]["sha256"]
        starts = list(range(1,count+1,3))
        assert sorted(k for k in record["files"] if k.startswith(native_folder+"/window-")) == [f"{native_folder}/window-{i:03d}.json" for i in starts]
        windows = [{"start":i,"pages":list(range(i,min(count+1,i+3)))} for i in starts]
        if mode=="windows":
            dest = scratch/"windows"/family
            prediction = source(windows_folder+"/prediction.json")
            pred = json.loads(prediction)
            assert pred["source_sha256"]==req["sha256"] and len(pred["pages"])==count
            views = []
            for n,page in enumerate(pred["pages"],1):
                raw=json.loads(source(f"{windows_folder}/raw-{n:03d}.json"))
                grid=json.loads(source(f"{windows_folder}/window-{n:03d}.json"))
                reader=raw["reader_result"]
                assert raw["page"]==page["page"]==grid["first_page"]==n
                assert req["rgb_sha256"][n-1]==raw["rgb_sha256"] and raw["source_sha256"]==grid["source_sha256"]==req["sha256"]
                lines=reader["lines"]
                words=[[word["text"],[round(v*raw["points"][i%2]/(reader["width"],reader["height"])[i%2],3) for i,v in enumerate(word["bbox"])]] for line in lines for word in line["words"]]
                assert words==[[span["text"],span["bbox"]] for span in page["spans"]]
                views.append(dict(page=n,line_word_counts=[len(line["words"]) for line in lines],rule_tables=grid["rule_tables"],span_sha256=sha(json.dumps(words,ensure_ascii=True,separators=(",",":"),allow_nan=False).encode())))
            write(dest/"prediction.json",prediction);write(dest/"windows.json",{"windows":windows});write(dest/"layout.json",{"pages":views})
        else:
            spec = ROOT/"docs/research/WP-0019/astra/policy.py"
            assert git_bytes("d62a96f8145345ce4c43544850d20fce13659879","docs/research/WP-0019/astra/policy.py")==spec.read_bytes().replace(b"\r\n",b"\n")
            assert git_bytes("0186467670074761a777602d77b53deff3451300","docs/research/WP-0015/astra/sensitivity-title-level/rescore.py")== (ASTRA/"sensitivity-title-level/rescore.py").read_bytes().replace(b"\r\n",b"\n")
            manifest=json.loads((scratch/"manifest"/family/"manifest.json").read_bytes())
            requested=set(manifest["selected_windows"])
            assert requested<=set(starts)
            use=requested if mode=="selected" else set(starts)
            pages=[]
            for window in windows:
                if window["start"] not in use: continue
                meta=json.loads(source(f"{native_folder}/window-{window['start']:03d}.json"))
                assert meta["first_page"]==window["start"] and meta["pages"]==len(window["pages"]) and meta["source_sha256"]==req["sha256"]
                for n in window["pages"]:
                    raw=json.loads(source(f"{native_folder}/raw-{n:03d}.json"))
                    page=json.loads(source(f"{native_folder}/page-{n:03d}.json"))
                    assert raw["page"]==page["page"]==n and raw["rgb_sha256"]==req["rgb_sha256"][n-1] and raw["source_sha256"]==page["source_sha256"]==req["sha256"]
                    corrected=page_projection(raw,page)
                    if mode=="selected":write(scratch/"native"/family/f"page-{n:03d}.json",corrected)
                    pages.append(corrected)
            if mode=="scoring":
                baseline=json.loads(source(native_folder+"/prediction.json"))
                baseline["pages"]=pages
                write(scratch/"baselines"/family/"native.json",baseline)
                truth=(archive/("scoring-"+family)/"truth.json").read_bytes()
                pin=json.loads(git_bytes("918701ae318b01395b911b9dbdf597e43908665b","docs/coordination/WP-0018/kit/archive-pins.json"))
                checked(truth,pin["families"][family]["source_commitments_sha256"]["truth.json"],"truth")
                write(scratch/"keys"/family/"truth.json",truth)
                for sub in (windows_folder,native_folder):source(sub+"/timing.json")
        result[family] = dict(run=run,inventoryRevision=rev,inventorySha256=sha(inv),planSha256=record["plan_sha256"],verifiedFiles=files,
                              source=req["sha256"],availableWindows=windows)
    write(receipt,result)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("windows","selected","scoring"))
    for key in ("archive","scratch","receipt"):parser.add_argument("--"+key,type=Path,required=True)
    args=parser.parse_args()
    process(args.mode,args.archive,args.scratch,args.receipt)
