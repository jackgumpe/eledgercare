"""Manifest-bound reads; dev-only by default. Reference side never feeds prediction mapper."""
from __future__ import annotations
import hashlib,json,re,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MANIFEST='evaluation/manifests/corpus-manifest.json'
DEV={'F01','F02','F04','F07'}

def sha(data):return hashlib.sha256(data).hexdigest()
def load_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def manifest():return load_json(ROOT/MANIFEST)
def fixtures():return manifest()['fixtures']
def item(fid):return next(f for f in fixtures() if f['fixture_id']==fid)
def gate(f,allow_test=False):
    if not allow_test and (f['split']!='dev' or f['family_id'] not in DEV):raise PermissionError('Holdout content is gated before any file read')
def verified(path,digest,limit=32<<20):
    p=(ROOT/path).resolve();p.relative_to(ROOT)
    if p.is_symlink() or p.stat().st_size>limit:raise ValueError('Invalid input path/size')
    data=p.read_bytes()
    if sha(data)!=digest:raise ValueError('Input identity mismatch: '+path)
    return data

def expected_for(f,allow_test=False):
    gate(f,allow_test)
    return json.loads(verified(f['expected_ground_truth_path'],f['expected_ground_truth_sha256']))
def pdf_for(f,allow_test=False):
    gate(f,allow_test);return verified(f['file_path'],f['sha256'])

def reference_for(f,allow_test=False):
    """Only this admitted writer's vector parent grammar; not a general PDF extractor.
    Includes all visible text operators (furniture, repeated headers, all values) and
    separately declared raster addendum label/body. Reading order is y-desc then x-asc.
    """
    gate(f,allow_test)
    parent=next(x for x in fixtures() if x['family_id']==f['family_id'] and x['variant_kind']=='v0_clean')
    data=pdf_for(parent,allow_test)
    objects={int(m[1]):m[2] for m in re.finditer(rb'(?m)^(\d+) 0 obj\n(.*?)\nendobj',data,re.S)}
    page_ids=[int(x) for x in re.search(rb'/Kids \[(.*?)\]',objects[2])[1].split() if x.isdigit()][::2]
    runs=[]
    for pn,pid in enumerate(page_ids,1):
        page=objects[pid];cid=int(re.search(rb'/Contents (\d+) 0 R',page)[1]);content=objects[cid]
        h=re.search(rb'/Length (\d+).*?stream\n',content,re.S);n=int(h[1]);compressed=content[h.end():h.end()+n]
        dec=zlib.decompressobj();stream=dec.decompress(compressed,2<<20)
        if not dec.eof or dec.unconsumed_tail:raise ValueError('Unsupported reference content stream')
        text=stream.decode('ascii');rows=[]
        for m in re.finditer(r'1 0 0 1 ([0-9.]+) ([0-9.]+) Tm \(((?:\\.|[^\\)])*)\) Tj ET',text):
            value=re.sub(r'\\([\\()])',r'\1',m[3]);rows.append({'x':float(m[1]),'y':float(m[2]),'text':value,'source':'vector_operator'})
        if len(rows)!=text.count(' Tj ET'):raise ValueError('Unsupported text operator; reference coverage incomplete')
        runs.append(rows)
    coverage={'status':'complete_for_admitted_writer','vector_parent':parent['fixture_id'],'vector_parent_sha256':parent['sha256'],
              'includes':['all vector text operators','titles','footers','repeated headers','declared hybrid label/body'],'ordering':'page; descending exact baseline y; ascending x; original operator ordinal ties','hybrid_added':False}
    if f['variant_kind']=='v3_hybrid':
        source=json.loads(verified(f['source_record_path'],f['source_record_sha256']));hy=source['hybrid_control']
        if hy['fixture_id']!=f['fixture_id']:raise ValueError('Hybrid source binding mismatch')
        x,_,_,top=hy['box_pt'];page=hy['target_page']
        for offset,key in [(10,'label'),(24,'printed_text')]:runs[page-1].append({'x':x,'y':top-offset,'text':hy[key],'source':'declared_raster_addendum'})
        coverage['hybrid_added']=True;coverage['hybrid_source_sha256']=f['source_record_sha256']
    ordered=[sorted(page,key=lambda x:(-x['y'],x['x'])) for page in runs]
    return {'pages':['\n'.join(r['text'] for r in page) for page in ordered],'runs':ordered,'coverage':coverage}
