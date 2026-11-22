"""Account for the residual on six archived development pages using isolated in-memory PDF copies."""
from collections import Counter
from contextlib import closing
import ctypes
import json
import math
from pathlib import Path
import re
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,SCRATCH,save,sha
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
import pypdfium2.raw as pdf_c

def render(page):
    with closing(page.render(scale=math.nextafter(300/72,0))) as bitmap:
        return np.array(bitmap.to_pil().convert("RGB"))

def paths(obj):
    points=[]
    m=obj.get_matrix()
    for i in range(pdf_c.FPDFPath_CountSegments(obj)):
        seg=pdf_c.FPDFPath_GetPathSegment(obj,i)
        kind=pdf_c.FPDFPathSegment_GetType(seg)
        assert kind in (pdf_c.FPDF_SEGMENT_MOVETO,pdf_c.FPDF_SEGMENT_LINETO)
        x,y=ctypes.c_float(),ctypes.c_float()
        assert pdf_c.FPDFPathSegment_GetPoint(seg,x,y)
        point=m.on_point(x.value,y.value)
        if kind==pdf_c.FPDF_SEGMENT_LINETO:
            px,py=points[-1][1:]
            assert px==point[0] or py==point[1]
        points.append((kind, *point))
    return points

def check():
    start=time.perf_counter()
    plan=(ROOT/"docs/coordination/WP-0024/h0-r1-plan.json").read_bytes()
    assert sha(plan)=="0bf358c54fc97f32ca213d9a1dd10cfb2838f42f7c5dcded1625c0cca1fd2f89"
    decoded=json.loads(plan)
    source=decoded["requests"][0]
    pdf=Path(source["pdf"]).read_bytes()
    assert sha(pdf)==source["sha256"]=="675367788d2b872511d05b704b98069e8b636d02d07d78095cc4bbeab3e63d5b"
    calls={c["tag"]:c for c in decoded["calls"]}
    output=[]
    with pdfium.PdfDocument(pdf) as doc:
        for idx in range(6):
            call=calls[("b01w01H","b01w02H")[idx//3]]
            signed=call["pages"][idx%3]
            png=Path(signed["image"])
            assert sha(png.read_bytes())==signed["sha256"]
            with closing(doc[idx]) as page:
                raster=render(page)
                assert sha(raster.tobytes())==signed["rgb_sha256"]
                height,width=raster.shape[:2]
                allowed=np.zeros((height,width),dtype=bool)
                texts=[]
                with closing(page.get_textpage()) as layer:
                    native=layer.get_text_range()
                    for match in re.finditer(r"[^\r\n]+",native):
                        chars=[layer.get_charbox(j) for j in range(*match.span()) if not native[j].isspace()]
                        texts.append(match.group())
                        xmin,ymin=min(c[0] for c in chars),min(c[1] for c in chars)
                        xmax,ymax=max(c[2] for c in chars),max(c[3] for c in chars)
                        xmin=math.floor(width*(xmin/612-1/999))
                        xmax=math.ceil(width*(xmax/612+1/999))
                        top=math.floor(height*((792-ymax)/792-1/999))
                        bottom=math.ceil(height*((792-ymin)/792+1/999))
                        allowed[top:bottom,xmin:xmax]=True
                objects=list(page.get_objects())
                geometry=[]
                for obj in objects:
                    if obj.type==pdf_c.FPDF_PAGEOBJ_PATH:
                        geometry.append(paths(obj))
                    else:
                        assert obj.type==pdf_c.FPDF_PAGEOBJ_TEXT and obj.level==0
                        page.remove_obj(obj)
                        obj.close()
                page.gen_content()
                lines_only=render(page)
                remaining=np.any(raster!=255,axis=2)&~allowed
                discrepancy=np.any(raster!=lines_only,axis=2)&~allowed
                residual_count=int(remaining.sum())
                assert not discrepancy.any()
                assert residual_count=={0:30470,3:24690}.get(idx,0)
                with Image.open(png) as encoded:
                    assert np.array_equal(raster,np.asarray(encoded))
                output.append({"page":idx+1,"tag":call["tag"],"transcript":texts,
                               "lines_only_full_raster_sha256":sha(lines_only.tobytes()),
                               "complete_original_rgb_sha256":signed["rgb_sha256"],"path_geometry_pt":geometry,
                               "residual_pixel_count":residual_count,"residual_mask_u8_sha256":sha(remaining.astype("u1").tobytes()),
                               "residual_samples_differing_from_independent_text_removed_pdf":int(discrepancy.sum())})
    return {"pdf_sha256":sha(pdf),"seconds":time.perf_counter()-start,"pages":output}

if __name__=="__main__":
    save(SCRATCH/sys.argv[1],check())
