"""Direct raster recognition and recovery of ruled cells from the current image only."""
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path
from time import perf_counter_ns as clock

import numpy as np
from PIL import Image
from formats import bbox_union, digest

ASSETS = {
    "System32/Windows.Media.Ocr.dll":"0db8e48e4f27055f7b7e45412761839b492f5b120b6245edadae61f3fe357ea1",
    "OCR/en-us/MsOcrRes.orp":"81771d772d77d541e33f3b37e94c81f8a6f87e0b75e933a2389dbcc55715b908",
}


def groups(indices):
    if not len(indices):
        return []
    return np.split(indices,np.flatnonzero(np.diff(indices)>1)+1)


def rule_tables(image, points):
    # Analyze at a common physical scale, tolerant of antialiasing; no layout template.
    size = tuple(round(p*2) for p in points)
    thumb = image.convert("L").resize(size,Image.Resampling.BILINEAR)
    ink = np.asarray(thumb)<215
    h,w=ink.shape
    horizontal=[]
    for ys in groups(np.flatnonzero(ink.sum(axis=1)>w*.22)):
        y=int(ys[len(ys)//2])
        runs=groups(np.flatnonzero(ink[y]))
        if runs:
            span=max(runs,key=len)
            if len(span)>w*.22:
                horizontal.append((y,int(span[0]),int(span[-1])))
    sets=[]
    for y,l,r in horizontal:
        for lines in sets:
            py,pl,pr=lines[-1]
            if y-py < h*.16 and max(abs(l-pl),abs(r-pr)) < w*.018:
                lines.append((y,l,r));break
        else:
            sets.append([(y,l,r)])
    tables=[]
    for lines in sets:
        if len(lines)<3:
            continue
        rows=[v[0] for v in lines]
        lo,hi=rows[0],rows[-1]
        left,right=lines[0][1:]
        candidates=np.flatnonzero(ink[lo:hi+1].sum(axis=0)>.80*(hi-lo))
        cols=[int(np.median(g)) for g in groups(candidates) if left-4 <= np.median(g) <= right+4]
        if len(cols)<3:
            continue
        tables.append(dict(xs=[x*points[0]/w for x in cols],ys=[y*points[1]/h for y in rows]))
    return tables


def layout(raw, grids, points):
    width,height=raw["width"],raw["height"]
    all_words=[]
    for li,line in enumerate(raw["lines"]):
        for word in line["words"]:
            box=[round(x*points[i%2]/(width,height)[i%2],3) for i,x in enumerate(word["bbox"])]
            all_words.append(dict(text=word["text"],bbox=box,flagged=False,line=li))
    assigned=set()
    tables=[]
    chunks=[]
    for grid in grids:
        xs,ys=grid["xs"],grid["ys"]
        cells=defaultdict(list)
        for i,w in enumerate(all_words):
            x=(w["bbox"][0]+w["bbox"][2])/2
            y=(w["bbox"][1]+w["bbox"][3])/2
            if xs[0] <= x < xs[-1] and ys[0] <= y < ys[-1]:
                col=int(np.searchsorted(xs,x,side="right"))-1
                row=int(np.searchsorted(ys,y,side="right"))-1
                cells[row,col].append(w)
                assigned.add(i)
        rows=[]
        for r in range(len(ys)-1):
            row=[]
            for c in range(len(xs)-1):
                ws=cells[r,c]
                row.append(" ".join(w["text"] for w in sorted(ws,key=lambda v:(v["line"],v["bbox"][0]))))
            rows.append(row)
        box=[xs[0],ys[0],xs[-1],ys[-1]]
        tables.append(dict(bbox=box,rows=rows))
        chunks.append((ys[0],xs[0]," ".join(v for row in rows for v in row)))
    lines=defaultdict(list)
    for i,w in enumerate(all_words):
        if i not in assigned:
            lines[w["line"]].append(w)
    for words in lines.values():
        box=bbox_union([w["bbox"] for w in words])
        chunks.append((box[1],box[0]," ".join(w["text"] for w in words)))
    spans=[{k:v for k,v in w.items() if k!="line"} for w in all_words]
    return dict(text=" ".join(" ".join(v[2] for v in sorted(chunks)).split()),spans=spans,tables=tables)


class Visual:
    window=1

    def __init__(self,run):
        win=Path(os.environ["SystemRoot"])
        for rel,want in ASSETS.items():
            if digest((win/rel).read_bytes())!=want:
                raise ValueError("Windows OCR asset mismatch: "+rel)
        cmd=[str(win/"System32/WindowsPowerShell/v1.0/powershell.exe"),"-NoProfile","-NonInteractive",
             "-ExecutionPolicy","Bypass","-File",str(Path(__file__).with_name("recognize.ps1"))]
        self.child=subprocess.Popen(cmd,cwd=run,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                    encoding="utf-8",errors="strict")
        try:
            self.info=json.loads(self.child.stdout.readline())
            self.info.update(asset_sha256=ASSETS,engine="Windows.Media.Ocr.OcrEngine",engine_version="10.0.26100.9278")
            if self.info["language"]!="en-US":
                raise ValueError("language mismatch")
        except BaseException:
            self.close()
            raise

    def close(self):
        self.child.stdin.close()
        try:
            self.child.wait(timeout=4)
        except subprocess.TimeoutExpired:
            self.child.kill()
            self.child.wait()

    def read(self,pages,folder):
        page,=pages
        begin=clock()
        image=page["image"]
        grids=rule_tables(image,page["points"])
        bitmap=folder/f"visual-{page['page']:03d}.bmp"
        limit=self.info["max_dimension"]
        if max(image.size)>limit:
            scale=limit/max(image.size)
            image=image.resize(tuple(round(s*scale) for s in image.size),Image.Resampling.LANCZOS)
        try:
            image.save(bitmap)
            self.child.stdin.write(json.dumps({"path":str(bitmap)})+"\n")
            self.child.stdin.flush()
            raw=json.loads(self.child.stdout.readline())
            if raw.get("error"):
                raise RuntimeError(raw["error"])
            output=layout(raw,grids,page["points"])
        finally:
            bitmap.unlink(missing_ok=True)
            if image is not page["image"]:
                image.close()
        words=sum(len(li["words"]) for li in raw["lines"])
        details=dict(algorithm="source-raster ruled-grid and Windows word boxes",rule_tables=grids,
                reader_and_layout_ns=clock()-begin,recognize_ms=raw["recognize_ms"],windows_ocr_words=words)
        return [(output,dict(reader_result=raw,word_count=words,token_ids=None,token_count=None,
                       token_classes=None))],details
