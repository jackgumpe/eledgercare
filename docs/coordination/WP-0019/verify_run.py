"""Recheck full-pass identity and crop geometry independently of the policy and the scorer."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from PIL import Image


def read(path):
    return json.loads(path.read_bytes())


def need(ok, label):
    if not ok:raise ValueError(label)


def raw_identity(raw):
    fields=('width','height','text','lines','angle')
    return {key:raw.get(key) for key in fields}


def canonical(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def pix(rectangle):
    return hashlib.sha256(rectangle.convert('RGBA').tobytes('raw','BGRA')).hexdigest()


def verify(family, order, run, reference=None):
    receipt=read(run/'receipt.json')
    pa=read(run/'A/prediction.json');pb=read(run/'B/prediction.json')
    pages=pa['pages']; count=len(pages)
    need([p['page'] for p in pages]==list(range(1,count+1)), 'control order')
    need([p['page'] for p in pb['pages']]==list(range(1,count+1)), 'treatment order')
    if reference:
        historic=read(reference/family/'raw.json')
        need(pa==read(reference/family/'prediction.json'),f'{family}-{order} full prediction vs post-update control')
    counts=Counter()
    decisions=Counter()
    region_events=[]
    for number in range(1,count+1):
        a,b=[read(run/arm/f'page-{number:03d}.json') for arm in ('A','B')]
        need(a['bitmap']==b['bitmap'], 'page manifest')
        raw=raw_identity(a['full'])
        need(raw==raw_identity(b['full']), 'intra-pair raw')
        if reference:
            need(raw==raw_identity(historic[number-1]['raw']), f'current original raw page {number}')
        meta=b['bitmap']; fi=b['full']
        with Image.open(meta['bmp']) as im:
            need((im.width,im.height)==(fi['width'],fi['height']) and pix(im)==fi['bgra_sha256']==meta['bgra_sha256'],'full SoftwareBitmap inputs')
            for region in b['regions']:
                selected=region['selected']
                need(selected==(region['crop'] is not None),'selection/read')
                counts['regions']+=1
                counts['eligible']+=region['eligible']
                if not selected:continue
                rect=region['rect_px'];x0,y0,x1,y1=rect
                need(all(type(i) is int for i in rect) and 0<=x0<x1<=im.width and 0<=y0<y1<=im.height,'crop rectangle')
                crop=region['crop']
                with im.crop(rect) as tile:
                    sha=pix(tile)
                    need(tile.size==(crop['width'],crop['height']),'crop measured dimensions')
                need(sha==crop['bgra_sha256']==region['expected_bgra_sha256']==region['observed_source_sha256'],'row hash')
                need(crop['full_bgra_sha256']==meta['bgra_sha256'],'retained parent')
                need(crop['pixel_format'].lower()==fi['pixel_format'].lower()=='bgra8','pixel mode')
                projected=[]
                for li,ln in enumerate(crop['lines']):
                    for wi,word in enumerate(ln['words']):
                        box=word['bbox']
                        need(0<=box[0]<box[2]<=x1-x0 and 0<=box[1]<box[3]<=y1-y0,'local word bounds')
                        projected.append(dict(text=word['text'],bbox=[v+(x0,y0)[i%2] for i,v in enumerate(box)],crop_word_ref=[li,wi]))
                need(projected==region['projected_words'],'projected words')
                actual=' '.join(w['text'] for w in projected)
                original=' '.join(fi['lines'][li]['words'][wi]['text'] for li,wi in region['full_word_refs'])
                need(original==region['full_value'] and actual==region['crop_value'],'selected observed literal')
                need(region['disagreement']==(actual!=original),'disagreement marker')
                used=region['decision'].startswith('use_')
                need(region['emitted_value']==(actual if used else original),'emitted value')
                counts['attempted']+=1;counts['different']+=actual!=original;counts['equal']+=actual==original
                counts['flagged_regions']+=region['flagged'];counts['accepted_reads']+=used
                decisions[region['decision']]+=1
                region_events.append((number,region['id'],tuple(rect),sha,original,actual,used,region['flagged']))
    elapsed={arm:receipt['arms'][arm]['elapsed_ns']/1e9 for arm in ('A','B')}
    return dict(family=family,order=order,pages=count,stage1_original_full_pages_checked=count if reference else None,
                stats=dict(counts),decisions=dict(decisions),prediction_semantic_hash={'A':canonical(pa),'B':canonical(pb)},
                selected_readings_hash=canonical(region_events),elapsed_s=elapsed,added_ms_per_page=1000*(elapsed['B']-elapsed['A'])/count,
                pages_per_min={arm:60*count/v for arm,v in elapsed.items()},crops_per_page=counts['attempted']/count)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run-root',type=Path,required=True);p.add_argument('--families',nargs='+',required=True)
    p.add_argument('--reference',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    results={}
    for f in a.families:
        rows=[verify(f,order,a.run_root/(f+'-'+order),a.reference) for order in ('AB','BA')]
        for key in ('stats','decisions','prediction_semantic_hash','selected_readings_hash'):
            need(rows[0][key]==rows[1][key],f'order disagreement {f} {key}')
        results[f]=rows
    with a.out.open('x',encoding='utf8',newline='\n') as stream:
        json.dump(results,stream,indent=2);stream.write('\n')
    print(json.dumps({family:{'observations':rr[0]['stats'],'added_ms_per_page':[round(r['added_ms_per_page'],2) for r in rr]} for family,rr in results.items()}))
