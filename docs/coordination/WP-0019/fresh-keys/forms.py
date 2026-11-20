"""Coordinator fixture generator. Produce two six-page lossless raster forms and DPAPI-sealed keys."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import os
from pathlib import Path
import random
import secrets
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageSequence, __version__ as pillow_version

FAMILIES = ('LIFT','VALVE')
SIZE = (2550,3300)
POINTS = (612,792)
SCALE = 300/72
FONTS = Path(os.environ['WINDIR'])/'Fonts'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def formatted(obj):
    return (json.dumps(obj,ensure_ascii=True,indent=2)+'\n').encode()


def save(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


class Blob(ctypes.Structure):
    _fields_ = [('n',wintypes.DWORD),('ptr',ctypes.POINTER(ctypes.c_ubyte))]


def protect(payload, unlock=False):
    """Use current Windows user DPAPI. No plaintext answer key is saved before the release."""
    buf=(ctypes.c_ubyte*len(payload)).from_buffer_copy(payload)
    source=Blob(len(payload),buf);out=Blob()
    api=ctypes.WinDLL('crypt32',use_last_error=True)
    fn=api.CryptUnprotectData if unlock else api.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:return ctypes.string_at(out.ptr,out.n)
    finally:
        free=ctypes.WinDLL('kernel32').LocalFree
        free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p
        free(out.ptr)


def px(points):
    return round(points*SCALE)


def pt(pixels):
    return round(pixels/SCALE,3)


class Codes:
    def __init__(self,seed):
        self.rng=random.Random(int.from_bytes(seed,'big'));self.used=set()

    def value(self,kind):
        choose=self.rng.choice
        while True:
            if kind=='confusable':
                v=choose('OILB')+choose('018')+''.join(choose('O0I1L8B') for _ in range(3))+'-'+''.join(choose('0123456789') for _ in range(3))
            elif kind=='ordinary':
                v=''.join(choose('ACDEFGHJKMNPQRTUVWXYZ') for _ in range(3))+str(self.rng.randrange(23,98))+'-'+str(self.rng.randrange(200,970))
            else:
                v=''.join(choose('ACDEFGHJKMNPQRTUVWXYZ') for _ in range(2))+' '+str(self.rng.randrange(2300,9800))
            if v not in self.used:self.used.add(v);return v


def render(family,number,codes):
    im=Image.new('RGB',SIZE,'white');draw=ImageDraw.Draw(im)
    sans=family=='LIFT'
    regular='segoeui.ttf' if sans else 'georgia.ttf'
    bold='segoeuib.ttf' if sans else 'georgiab.ttf'
    def font(size,heavy=False):
        return ImageFont.truetype(str(FONTS/(bold if heavy else regular)),px(size))
    def paint(x,y,text,size,heavy=False):
        f=font(size,heavy);pos=(px(x),px(y))
        draw.text(pos,text,font=f,fill=(22,22,22),anchor='lt')
        return draw.textbbox(pos,text,font=f,anchor='lt')
    lines=[];events=[];tags=[];tables=[];audit=[]
    def line(x,y,text,critical=None,kind=None,size=11,heavy=False):
        raw=paint(x,y,text,size,heavy)
        box=[pt(raw[0])-1,pt(raw[1])-1,pt(raw[2])+1,pt(raw[3])+1]
        assert all(0<=v<=POINTS[i%2] for i,v in enumerate(box))
        lines.append(dict(text=text,bbox=box,critical=critical))
        events.append((y,text))
        if kind:tags.append(dict(at=f'page/{number}/line/{len(lines)}',stratum=kind))
    def grid(xs,ys,values,types):
        trows=[];words=[]
        for y in ys:draw.line((px(xs[0]),px(y),px(xs[-1]),px(y)),fill=(52,52,52),width=3)
        for x in xs:draw.line((px(x),px(ys[0]),px(x),px(ys[-1])),fill=(52,52,52),width=3)
        for ri,items in enumerate(values):
            row=[]
            for ci,v in enumerate(items):
                box=[xs[ci],ys[ri],xs[ci+1],ys[ri+1]]
                if v:
                    painted=paint(box[0]+6,box[1]+8,v,10.5,ri==0)
                    assert painted[2]<px(box[2]-3) and painted[3]<px(box[3]-2),(family,number,ri,ci,'fit')
                inner=im.crop(tuple([px(box[0])+5,px(box[1])+5,px(box[2])-5,px(box[3])-5]))
                ink=inner.getextrema()[0][0]<128;inner.close()
                assert ink==bool(v),(family,number,ri,ci,'visible ink')
                at=f'page/{number}/table/1/row/{ri+1}/col/{ci+1}'
                typ=types.get((ri,ci))
                row.append(dict(text=v,bbox=box,critical=typ in ('confusable','ordinary','legitimate_space')))
                if typ:tags.append(dict(at=at,stratum=typ))
                audit.append(dict(at=at,has_ink=ink))
                words.append(v)
            trows.append(row)
        tables.append(dict(bbox=[xs[0],ys[0],xs[-1],ys[-1]],rows=trows))
        events.append((ys[0],' '.join(words)))
    if sans:
        line(39,52,'Lift maintenance release',size=20,heavy=True)
        line(40,92,'Service desk inspection record',size=11)
        k='confusable' if number%2 else 'ordinary'
        val=codes.value(k);line(41,152,'Release ref '+val,val,k)
        val=codes.value('legitimate_space');line(41,190,'Shift group '+val,val,'legitimate_space')
        line(41,232,'Inspection interval 24 hours.',kind='numeric_negative')
        top=282+(number%3)*9
        serials=[codes.value(k) for k in ('ordinary','confusable','legitimate_space')]
        rows=[['Point','Serial ID','Disposition'],['Hoist',serials[0],'Serviceable'],['Carriage',serials[1],'Retained'],
              ['Guide',serials[2],'Reviewed'],['Brake','','Pending']]
        ty={(1,1):'ordinary',(2,1):'confusable',(3,1):'legitimate_space',(4,1):'blank',(4,2):'text_negative'}
        grid([40,160,355,567],[top+i*37 for i in range(6)],rows,ty)
        line(40,580,'Technician signature on file.',kind='text_negative')
    else:
        line(246,54,'Valve work clearance',size=19,heavy=True)
        line(54,116,'Bench verification sheet',size=13,heavy=True)
        line(54,152,'Test pressure 37 kPa.',kind='numeric_negative')
        k='ordinary' if number%2 else 'confusable'
        val=codes.value(k);line(260,206,'Permit code '+val,val,k)
        val=codes.value('legitimate_space');line(260,245,'Bay group '+val,val,'legitimate_space')
        top=333+(number%3)*7
        serials=[codes.value(k) for k in ('confusable','legitimate_space','ordinary')]
        rows=[['Station','Action','Asset code','Reading'],['Inlet','Hold',serials[0],'15 mm'],
              ['Outlet','Check',serials[1],'12 mm'],['Stem','Replace',serials[2],'8 mm'],['Seal','Observe','','']]
        ty={(1,2):'confusable',(2,2):'legitimate_space',(3,2):'ordinary',(4,2):'blank',(4,3):'blank',(1,3):'numeric_negative',(4,1):'text_negative'}
        grid([34,131,244,437,579],[top+i*32 for i in range(6)],rows,ty)
        line(55,614,'Retain this clearance with the work record.',kind='text_negative')
    ref=dict(page=number,width=POINTS[0],height=POINTS[1],text='\n'.join(text for y,text in sorted(events)),lines=lines,tables=tables)
    return im,ref,tags,audit


def build(share,vault,seed):
    assert not share.exists() and not vault.exists()
    share.mkdir(parents=True);vault.mkdir(parents=True)
    save(vault/'seed.dpapi',protect(seed))
    raster_report={};key_report={};provenance={}
    for family in FAMILIES:
        codes=Codes(hashlib.sha256(seed+family.encode()).digest());images=[];refs=[];tags=[];qa=[];page_info=[]
        dest=share/family;dest.mkdir()
        for n in range(1,7):
            im,ref,ts,audit=render(family,n,codes);images.append(im);refs.append(ref);tags.extend(ts);qa.extend(audit)
        tiff=dest/'source.tif'
        images[0].save(tiff,format='TIFF',save_all=True,append_images=images[1:],compression='tiff_deflate',dpi=(300,300))
        source=digest(tiff.read_bytes())
        with Image.open(tiff) as multi:
            assert multi.n_frames==6
            for n,im in enumerate(images,1):
                multi.seek(n-1)
                copy=multi.convert('RGB')
                assert copy.size==SIZE and copy.tobytes()==im.tobytes()
                bmp=dest/f'page-{n:03d}.bmp';copy.save(bmp,format='BMP',dpi=(300,300))
                with Image.open(bmp) as loaded:assert loaded.tobytes()==im.tobytes()
                page_info.append(dict(page=n,bmp=str(bmp.resolve()),width=SIZE[0],height=SIZE[1],points=list(POINTS),
                           rgb_sha256=digest(copy.tobytes()),bgra_sha256=digest(copy.convert('RGBA').tobytes('raw','BGRA')),bmp_sha256=digest(bmp.read_bytes())))
                copy.close();im.close()
        manifest=dict(family=family,source_sha256=source,renderer={'source':'lossless native raster TIFF','dpi':300,'pillow':pillow_version},pages=page_info)
        save(dest/'manifest.json',formatted(manifest))
        truth=formatted(dict(family=family,source_sha256=source,pages=refs))
        descriptor=formatted(dict(family=family,locations=tags,visibleCellAudit=qa))
        save(vault/(family+'.truth.dpapi'),protect(truth));save(vault/(family+'.strata.dpapi'),protect(descriptor))
        assert protect((vault/(family+'.truth.dpapi')).read_bytes(),True)==truth
        counts=Counter(t['stratum'] for t in tags)
        raster_report[family]=dict(pages=6,source_tiff_sha256=source,manifest_sha256=digest(formatted(manifest)),ordered_rgb_sha256=[v['rgb_sha256'] for v in page_info])
        key_report[family]=dict(truth_sha256=digest(truth),strata_sha256=digest(descriptor))
        provenance[family]=dict(criticalIdentifiers=counts['ordinary']+counts['confusable']+counts['legitimate_space'],strata=dict(counts),cellInkChecks=len(qa),pages=6)
    save(share/'raster-commitment.json',formatted(dict(method='Lossless 300 DPI native synthetic paper forms with source TIFF and verified ready BMPs.',families=raster_report)))
    save(vault/'answer-key-commitment.json',formatted(dict(seed_sha256=digest(seed),generator_sha256=digest(Path(__file__).read_bytes()),families=key_report)))
    save(vault/'fixture-counts.json',formatted(dict(families=provenance,pillow=pillow_version,fonts={f:digest((FONTS/f).read_bytes()) for f in ('segoeui.ttf','segoeuib.ttf','georgia.ttf','georgiab.ttf')},
         escrow='The coordinator retained DPAPI-protected labels and seed under the local Windows user. OCR inputs contain only source images and raster metadata.')))
    print(json.dumps(provenance))


def release(vault,returned,dest):
    receipt=json.loads(returned.read_bytes())
    if {(r['family'],r['order']) for r in receipt['runs']}!={(f,o) for f in FAMILIES for o in ('AB','BA')}:raise ValueError('blind returns incomplete')
    for r in receipt['runs']:
        if r['exit']!=0:raise ValueError('blind run failed')
        for name,want in r['outputs'].items():
            if digest((returned.parent/(r['family']+'-'+r['order'])/name).read_bytes())!=want:raise ValueError('blind output altered')
    if dest.exists():raise FileExistsError(dest)
    keys=json.loads((vault/'answer-key-commitment.json').read_bytes())
    for f in FAMILIES:
        for label in ('truth','strata'):
            raw=protect((vault/(f+'.'+label+'.dpapi')).read_bytes(),True)
            if digest(raw)!=keys['families'][f][label+'_sha256']:raise ValueError('key commitment')
            save(dest/f/(label+'.json'),raw)
    seed=protect((vault/'seed.dpapi').read_bytes(),True)
    if digest(seed)!=keys['seed_sha256']:raise ValueError('seed commitment')
    save(dest/'seed.hex',seed.hex().encode()+b'\n')
    print('Verified blind return and released the two committed fixture keys.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    subs=parser.add_subparsers(dest='mode',required=True)
    b=subs.add_parser('build');b.add_argument('--share',type=Path,required=True);b.add_argument('--vault',type=Path,required=True)
    b.add_argument('--seed-hex-file',type=Path,help='Only for reproducing an already released fixture.')
    u=subs.add_parser('release');u.add_argument('--vault',type=Path,required=True);u.add_argument('--return-file',type=Path,required=True);u.add_argument('--dest',type=Path,required=True)
    a=parser.parse_args()
    if a.mode=='build':build(a.share,a.vault,bytes.fromhex(a.seed_hex_file.read_text().strip()) if a.seed_hex_file else secrets.token_bytes(32))
    else:release(a.vault,a.return_file,a.dest)
