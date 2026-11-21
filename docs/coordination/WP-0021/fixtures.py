"""Construct two-page ruled ledgers, synthetic word observations, and a separate scoring key."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
import numpy

POINTS = (612, 792)
SCALE = 2
PARENT = (40, 130, 340, 430, 540)
INDENTED = (76, 210, 360, 440, 540)
SAME_MARGIN = (40, 210, 360, 440, 540)
PARENT_HEADER = ("Date","Charge","Unit","Amount")
CHILD_HEADER = ("Vendor","WorkOrder","Hrs","Amount")
COMMON_HEADER = ("Date","Description","Ref","Amount")
PIN = "a0e738bc03e515999659dda09c5ee76d08fb37df"

def sha(raw): return hashlib.sha256(raw).hexdigest()
def encode(value): return (json.dumps(value,ensure_ascii=True,indent=2)+"\n").encode()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data: raise ValueError(str(path))
    path.write_bytes(data)

class Sheet:
    def __init__(self,num,font,detector):
        self.number=num
        self.image=Image.new("RGB",(POINTS[0]*SCALE,POINTS[1]*SCALE),"white")
        self.draw=ImageDraw.Draw(self.image)
        self.font=font
        self.detector=detector
        self.lines=[]
        self.targets=[]
        self.drawn=[]
    def line(self, words, positions, y):
        row=[]
        idx=len(self.lines)+1
        for string,x in zip(words,positions,strict=True):
            if not string: continue
            self.draw.text((x*SCALE,y*SCALE),string,font=self.font,anchor="lt",fill="black")
            left,top,right,bottom=self.draw.textbbox((x*SCALE,y*SCALE),string,font=self.font,anchor="lt")
            row.append(dict(text=string,bbox=[v/SCALE for v in (left,top,right,bottom)],ref=f"p{self.number}:L{idx}:W{len(row)+1}"))
        self.lines.append(dict(words=row))
        return idx,row
    def grid(self,scope,xs,top,rows,header=None,tint=255,ambiguous=False):
        height=22
        cells=([header] if header is not None else [])+rows
        edges=[top+i*height for i in range(len(cells)+1)]
        self.draw.rectangle([xs[0]*2,top*2,xs[-1]*2,edges[-1]*2],fill=(tint,)*3)
        for y in edges:self.draw.line([(xs[0]*2,y*2),(xs[-1]*2,y*2)],fill="black",width=1)
        for x in xs:self.draw.line([(x*2,top*2),(x*2,edges[-1]*2)],fill="black",width=1)
        self.drawn.append(dict(xs=list(xs),ys=edges))
        for i,values in enumerate(cells):
            idx,ww=self.line(values,[x+5 for x in xs[:-1]],edges[i]+6)
            if header is not None and i==0:continue
            self.targets.append(dict(page=self.number,line=idx,actual_scope=scope,ambiguous=ambiguous,
                 literal=ww[-1]['text'],word_ref=ww[-1]['ref'],missing_third=not bool(values[2])))
    def observation(self):
        return dict(page=self.number,width_pt=POINTS[0],height_pt=POINTS[1],
                    grids=self.detector(self.image,POINTS),lines=self.lines)

def make(family,kind,hidden,font,detector,out):
    child_x=INDENTED if kind in ("multi","single") else SAME_MARGIN if kind=="merge" else PARENT
    parent_header=COMMON_HEADER if kind=="ambiguous" else PARENT_HEADER
    child_header=COMMON_HEADER if kind=="ambiguous" else CHILD_HEADER
    first=Sheet(1,font,detector);first.line(["Property:","Harbor","View"],[40,100,140],32)
    first.line(["Unit:","2B"],[40,77],50)
    first.line(["Ledger"],[40],85)
    first.grid("parent",PARENT,110,[("11/01","Rent","2B","1,450.00"),("11/02","Service","2B","70.00")],parent_header)
    first.line(["Contractor","detail"],[child_x[0],child_x[0]+65],359)
    first.grid("child",child_x,385,[("11/03","Valve","I0L-17","190.00"),("11/04","Visit","2","42.00")],child_header)
    second=Sheet(2,font,detector)
    if kind=="ambiguous":
        second.grid(hidden,child_x,80,[("11/20","Valve","01801-139","310.00")],tint=238 if hidden=="child" else 255,ambiguous=True)
    else:
        # Targets share dates, vocabulary and amount literals across scopes. Row content is insufficient.
        c=[("11/19","Visit","01801-139","190.00")]
        a=[("11/20","Visit","","190.00")]
        if kind!="single":
            c.append(("11/20","Valve","I0L-17","310.00"))
            a.append(("11/21","Valve","2B","310.00"))
        second.grid("child",child_x,80,c)
        second.grid("parent",PARENT,160,a)
    pages=[first,second]
    observation=dict(pages=[sheet.observation() for sheet in pages])
    raw=encode(observation);save(out/"inputs"/(family+".json"),raw)
    images=[]
    for sheet in pages:
        import io
        buf=io.BytesIO();sheet.image.save(buf,"PNG");data=buf.getvalue();name=f"{family}-p{sheet.number}.png"
        save(out/"rasters"/name,data);images.append(dict(name=name,sha256=sha(data)))
    return dict(case=kind,observationSha256=sha(raw),rasters=images,property="Harbor View",unit="2B",
                property_refs=["p1:L1:W2","p1:L1:W3"],unit_refs=["p1:L2:W2"],
                targets=first.targets+second.targets,drawnGrids=[sheet.drawn for sheet in pages],
                detectedGrids=[page['grids'] for page in observation['pages']])

def build(repo,out):
    source=repo/"docs/research/WP-0015/astra"
    for name in ("visual.py","formats.py"):
        relative=(source/name).relative_to(repo).as_posix()
        frozen=subprocess.check_output(["git","-C",str(repo),"show",PIN+":"+relative])
        assert frozen==(source/name).read_bytes().replace(b"\r\n",b"\n")
    sys.path.insert(0,str(source))
    from visual import rule_tables
    fontfile=Path(os.environ["WINDIR"])/"Fonts"/"segoeui.ttf"
    font=ImageFont.truetype(str(fontfile),20)
    specs=[("D03","multi",None),("D11","single",None),("D19","merge",None),("D27","ambiguous","parent"),("D32","ambiguous","child")]
    cases={f:make(f,k,h,font,rule_tables,out) for f,k,h in specs}
    assert cases["D27"]["observationSha256"]==cases["D32"]["observationSha256"]
    key=dict(source=PIN,fontSha256=sha(fontfile.read_bytes()),numpy=numpy.__version__,pillow=Image.__version__,cases=cases)
    save(out/"keys"/"answers.json",encode(key))
    return key

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("repo",type=Path);parser.add_argument("out",type=Path)
    args=parser.parse_args();build(args.repo.resolve(),args.out.resolve())
