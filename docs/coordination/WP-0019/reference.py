"""Admit the two exposed RGB streams and run the original WinRT full-page control on this host."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VISUAL = ROOT / "docs/research/WP-0015/astra"
sys.path.insert(0, str(VISUAL))
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
from visual import layout, rule_tables

PIN = "a0e738bc03e515999659dda09c5ee76d08fb37df"
EVAL = "7598bf4155452c4a1294b7421595009d39ea1bc9"
FAMILIES = {"H": 4, "A": 60}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write((json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode())
        handle.flush()
        os.fsync(handle.fileno())


def git_file(revision, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{revision}:{path}"])


def require(ok, message):
    if not ok:
        raise ValueError(message)


def prepare(inputs, original):
    commitments = json.loads(git_file(EVAL, "docs/evaluation/WP-0015/commitments.json"))["packets"]
    expectation = {"H":"bd48af1a7f968b2231fe1d870a22c88f265ae347", "A":"ce4206f20d63101f6344121eaaeeeb86d2ec85a0"}
    inventories = {"H":"H-blind-inventory.json", "A":"A-recovery-blind-inventory.json"}
    result = {}
    for family, count in FAMILIES.items():
        folder = original / ("input-" + family)
        pdf = (folder / "source.pdf").read_bytes()
        sha = digest(pdf)
        manifest_file = folder / "rasters.input.json"
        historical = read(manifest_file)
        inventory = json.loads(git_file(expectation[family], "docs/reviews/WP-0015/evidence/" + inventories[family]))["input"]
        require(digest(manifest_file.read_bytes()) == inventory["rasters.input.json"], "historical input inventory")
        require(sha == historical["pdf_sha256"] == commitments[family]["files"]["source.pdf"] == inventory["source.pdf"], "source")
        target = inputs / family
        target.mkdir(parents=True, exist_ok=False)
        pages = []
        with closing(pdfium.PdfDocument(pdf)) as doc:
            require(len(doc) == count == len(historical["pages"]), "page count")
            for number, ref in enumerate(historical["pages"], 1):
                with closing(doc[number-1]) as pg:
                    points = list(pg.get_size())
                    with closing(pg.render(scale=300/72)) as bitmap:
                        im = bitmap.to_pil().convert("RGB")
                with im:
                    rgb = digest(im.tobytes())
                    require([im.width,im.height,number,rgb] == [ref["width_px"],ref["height_px"],ref["page_number"],ref["rgb_sha256"]], f"RGB/{family}/{number}")
                    bgra = digest(im.convert("RGBA").tobytes("raw", "BGRA"))
                    bmp_path = target / f"page-{number:03d}.bmp"
                    im.save(bmp_path, format="BMP")
                    with Image.open(bmp_path) as decoded:
                        require(decoded.mode == "RGB" and digest(decoded.tobytes()) == rgb,"lossless BMP")
                    pages.append(dict(page=number,bmp=str(bmp_path.resolve()),points=points,width=im.width,height=im.height,
                                      rgb_sha256=rgb,bgra_sha256=bgra,bmp_sha256=digest(bmp_path.read_bytes())))
        manifest = dict(family=family,source_sha256=sha,renderer=historical["renderer"],pages=pages)
        write(target/"manifest.json",manifest)
        result[family]=dict(pages=count,source_sha256=sha,manifest_sha256=digest((target/"manifest.json").read_bytes()))
        print(f"admitted {family}: {count} pages",flush=True)
    write(inputs/"admission.json",result)


def semantic(raw):
    return {k:raw[k] for k in ("width","height","text","lines","angle")}


def semantic_hash(raw):
    return digest(json.dumps(semantic(raw),ensure_ascii=True,sort_keys=True,separators=(",",":")).encode())


def control(inputs, out, archive):
    out.mkdir(parents=True,exist_ok=False)
    for fn in ("recognize.ps1","visual.py"):
        # Conversion to working-tree line endings leaves the reviewed program unchanged.
        original = git_file(PIN,"docs/research/WP-0015/astra/"+fn)
        require(original.replace(b"\r\n",b"\n") == (VISUAL/fn).read_bytes().replace(b"\r\n",b"\n"),fn)
    ps = Path(os.environ["SystemRoot"])/"System32/WindowsPowerShell/v1.0/powershell.exe"
    cmd = [str(ps),"-NoProfile","-NonInteractive","-File",str(VISUAL/"recognize.ps1")]
    def call(proc, path):
        proc.stdin.write(json.dumps({"path":path})+"\n")
        proc.stdin.flush()
        raw = json.loads(proc.stdout.readline())
        require("error" not in raw,raw.get("error"))
        return raw
    results = {}
    start = time.perf_counter()
    with (out/"stderr.txt").open("x",encoding="utf8") as errors:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,encoding="utf8",cwd=out)
        try:
            info=json.loads(proc.stdout.readline());startup_s=time.perf_counter()-start
            require(info["language"]=="en-US","control language")
            first=read(inputs/"H/manifest.json")["pages"][0]
            before=time.perf_counter();warmed=call(proc,first["bmp"]);warm_s=time.perf_counter()-before
            require((warmed["width"],warmed["height"])==(first["width"],first["height"]),"warmup dimensions")
            for family,count in FAMILIES.items():
                manifest=read(inputs/family/"manifest.json"); raw_pages=[]; predicted=[]; by_page=[]
                for item in manifest["pages"]:
                    n=item["page"]
                    require(max(item["width"],item["height"])<=info["max_dimension"],"full-page rescale would be needed")
                    raw=call(proc,item["bmp"])
                    require([raw["width"],raw["height"]]==[item["width"],item["height"]],"actual geometry")
                    with Image.open(item["bmp"]) as im:
                        grids=rule_tables(im,item["points"])
                    pred=dict(page=n,source_sha256=manifest["source_sha256"],state="complete",**layout(raw,grids,item["points"]))
                    historic=read(archive/family/"windows"/f"raw-{n:03d}.json")["reader_result"]
                    raw_pages.append(dict(page=n,raw=raw,grids=grids,recognizerPixelFormat="Bgra8/Ignore"))
                    predicted.append(pred)
                    by_page.append(dict(page=n,old=semantic_hash(historic),current=semantic_hash(raw),
                                        same_raw=semantic(raw)==semantic(historic),same_exported_page=pred==read(archive/family/"windows"/f"page-{n:03d}.json"),
                                        width=raw["width"],height=raw["height"],rgb_sha256=item["rgb_sha256"],bgra_sha256=item["bgra_sha256"]))
                write(out/family/"raw.json",raw_pages)
                write(out/family/"prediction.json",dict(source_sha256=manifest["source_sha256"],pages=predicted))
                target=out/family/"score.json"
                subprocess.run([sys.executable,"-B",str(archive/"control/score.py"),str(archive/family/"truth.json"),str(out/family/"prediction.json"),"--out",str(target)],check=True,stdout=subprocess.DEVNULL)
                score=read(target); require(score["packet_complete"],"full control incomplete")
                results[family]=dict(page_count=count,score=score["counts"],faults=score["faults"],page_identities=by_page,
                    hashes={name:digest((out/family/name).read_bytes()) for name in ("raw.json","prediction.json","score.json")})
                print(f"control {family}: {score['counts']['critical_errors']}/{score['counts']['critical_values']} critical errors; {sum(p['same_raw'] for p in by_page)}/{count} historical raw pages equal",flush=True)
        finally:
            proc.stdin.close()
            try: proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.terminate();proc.wait();raise
            proc.stdout.close()
    require(proc.returncode==0,"control worker exit")
    write(out/"control.json",dict(adapter=PIN,scorerSha256=digest((archive/"control/score.py").read_bytes()),engine=info,workerExit=proc.returncode,
        format="SoftwareBitmap Bgra8 with Ignore alpha, explicitly requested from the BMP decoder in recognize.ps1",startup_s=startup_s,excluded_warmup_s=warm_s,
        reading="Same geometry and full raw text, lines, word boxes and angle are compared. Elapsed recognition time is excluded from the identity.",families=results))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("prepare","control"));p.add_argument("--inputs",type=Path,required=True)
    p.add_argument("--archive",type=Path,required=True);p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.mode=="prepare":prepare(args.inputs,args.archive)
    else:control(args.inputs,args.out,args.archive)
