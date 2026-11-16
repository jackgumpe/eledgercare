"""Custodian author verification, not independent admission. Never runs a mapper/model.

Reads the frozen generated candidate. Uses separate PDF parsers and Decimal checks,
then generates two fresh copies in an owned ignored scratch directory and byte-compares.
All reports are exclusively created and retained, including a failed report.
"""
from __future__ import annotations
import argparse, datetime, hashlib, importlib.metadata, json, re, subprocess, sys, traceback
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def require(condition, message):
    if not condition:raise AssertionError(message)
def run(argv):return subprocess.check_output(argv,text=True,encoding='utf-8').strip()
def item_checks(item, slot):
    raw=item['printed_text']; norm=item['normalized_value']; kind=item['value_type']
    require(isinstance(raw,str) and isinstance(norm,str),'string-only schema')
    if kind in ('text','identifier'):require(raw==norm,'literal string altered')
    elif kind=='date_iso':require(datetime.date.fromisoformat(raw).isoformat()==norm,'date value')
    elif kind=='boolean_mark':require({'[X]':'true','[ ]':'false'}[raw]==norm,'boolean mark')
    elif kind in ('decimal_2','currency_usd','rate_percent'):
        if slot=='qty_unit':
            number,unit=raw.split(' ');require(unit==item['quantity_unit'],'quantity unit metadata')
            require(unit in ('EA','HR','BX','KT','PR'),'unit outside established task grammar')
        else:number=raw.replace('$','').replace(',','').replace('%','')
        number=Decimal(number)
        if kind=='rate_percent':number/=100
        require(number==Decimal(norm),'numeric conversion')
    else:raise AssertionError('undeclared type '+kind)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--run-id',required=True);ap.add_argument('--public-repo',type=Path,required=True)
    ap.add_argument('--candidate-commit',required=True);a=ap.parse_args()
    candidate=a.candidate.resolve();candidate.relative_to(ROOT)
    require(re.fullmatch(r'[A-Za-z0-9_-]+',a.run_id),'invalid run id')
    out=ROOT/'evidence'/a.run_id;require(not out.exists(),'evidence must not exist');out.mkdir(parents=True)
    result={'schema':'eld-wp09-custodian-validation/1','run_id':a.run_id,
       'candidate_commit':a.candidate_commit,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'author_verification_only':True,'independent_admission':'pending','checks':[],
       'environment':{'python':sys.version,'executable':sys.executable,
                      **{n:importlib.metadata.version(n) for n in ('pypdf','pypdfium2','Pillow')}},
       'commands':[],'status':'running'}
    try:
        require(run(['git','-C',str(ROOT),'rev-parse','HEAD'])==a.candidate_commit,'candidate HEAD mismatch')
        require(not run(['git','-C',str(ROOT),'diff','HEAD','--']),'tracked source modified')
        result['checks'].append('exact candidate HEAD and tracked bytes')
        m=read(candidate/'manifest.json');require((m['families'],m['pdfs'],m['pages'])==(4,4,6),'bounded counts')
        for f in m['files']:
            p=candidate/f['path'];require(p.is_file() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],'manifest '+f['path'])
        require(len(m['files'])==20,'complete core file count')
        result['checks'].append('20 manifest paths, sizes and SHA256 identities')
        old=[read(p) for p in (a.public_repo/'evaluation/synthetic/expected').glob('*v0*json')]
        old_families={x['family_id'] for x in old}; old_ids={x['fixture_id'] for x in old}
        canonical_fields={f['field_id'] for e in old for f in e['expected_fields']+e['expected_absences']}
        canonical_tables={}
        for e in old:
            for t in e['expected_tables']:canonical_tables.setdefault(t['table_id'],set()).update(t['column_ids'])
        images=[];counts={'fields':0,'absences':0,'tables':0,'rows':0,'cells':0,'text_operators':0,'quantity_unit_cells':0,'pages':0}
        for f in m['fixtures']:
            fid=f['fixture_id'];require(fid not in old_ids and f['family_id'] not in old_families,'fresh identity')
            e=read(candidate/'expected'/f'{fid}.json');ref=read(candidate/'reference'/f'{fid}.json')
            ops=read(candidate/'operators'/f'{fid}.json');src=read(candidate/'sources'/f'{fid}.json')
            pdf=candidate/'pdfs'/f'{fid}.pdf';reader=PdfReader(pdf,strict=True)
            require(len(reader.pages)==e['page_count']==f['page_count'],'PDF page count')
            require(e['schema_version']=='1.0.0','schema version')
            for pn,page in enumerate(reader.pages,1):
                require(tuple(float(x) for x in page.mediabox)==(0,0,612,792),'page geometry')
                stream=page.get_contents().get_data().decode('ascii')
                require(stream=='\n'.join(ops['pages'][pn-1]['operators'])+'\n','actual source operator parity')
                texts=re.findall(r'1 0 0 1 ([0-9.]+) ([0-9.]+) Tm \(((?:\\.|[^\\)])*)\) Tj ET',stream)
                runs=[{'x':float(x),'y':float(y),'text':re.sub(r'\\([\\()])',r'\1',t)} for x,y,t in texts]
                require(len(runs)==stream.count(' Tj ET'),'all text operators parsed')
                ordered=sorted(runs,key=lambda r:(-r['y'],r['x']))
                require('\n'.join(r['text'] for r in ordered)==ref['pages'][pn-1],'reading order complete')
                require([r['text'] for r in ordered]==[r['text'] for r in ref['runs'][pn-1]],'run identity')
                extracted=' '.join(page.extract_text().split())
                for r in runs:require(' '.join(r['text'].split()) in extracted,'independent PDF extraction lost text')
                rr=ref['runs'][pn-1]
                for i,l in enumerate(rr):
                    box=l['bbox_pt'];require(12<=box[0]<box[2]<=600 and 12<=box[1]<box[3]<=782,'text page bounds')
                    for r in rr[i+1:]:
                        b=r['bbox_pt'];overlap=min(box[2],b[2])-max(box[0],b[0])>0.5 and min(box[3],b[3])-max(box[1],b[1])>0.5
                        require(not overlap,'text collision '+fid+': '+l['text']+' / '+r['text'])
                require('SYNTHETIC TRAINING DOCUMENT' in extracted,'visible synthetic notice')
                counts['text_operators']+=len(runs);counts['pages']+=1
            slots=[]
            for field in e['expected_fields']:
                require(field['field_id'] in canonical_fields,'unknown canonical field')
                slots.append((field['page_number'],field['field_id'],field))
            for ab in e['expected_absences']:
                require(ab['field_id'] in canonical_fields and ab['expected_state']=='absent_blank','absence schema')
                bbox=ab['bbox_pt']
                require(not any(min(bbox[2],r['bbox_pt'][2])-max(bbox[0],r['bbox_pt'][0])>0.5 and min(bbox[3],r['bbox_pt'][3])-max(bbox[1],r['bbox_pt'][1])>0.5 for r in ref['runs'][ab['page_number']-1]),'absence box contains text')
            for table in e['expected_tables']:
                require(table['table_id'] in canonical_tables and set(table['column_ids'])<=canonical_tables[table['table_id']],'unknown table slot')
                require(len({r['row_id'] for r in table['rows']})==len(table['rows']),'duplicate row identity')
                for row in table['rows']:
                    require(list(row['cells'])==table['column_ids'],'cell order')
                    for slot,item in row['cells'].items():slots.append((row['page_number'],slot,item))
                counts['rows']+=len(table['rows']);counts['cells']+=sum(len(r['cells']) for r in table['rows'])
            for page,slot,item in slots:
                item_checks(item,slot)
                require(any(r['text']==item['printed_text'] and r['bbox_pt']==item['bbox_pt'] for r in ref['runs'][page-1]),'ground truth value not visibly located')
                counts['quantity_unit_cells']+=int(slot=='qty_unit')
            for s in e['page_sentinels']:
                require(s['sentinel_id'] in ref['pages'][s['page_number']-1] and s['page_label'] in ref['pages'][s['page_number']-1],'page sentinel')
            for link in e['cross_page_links']:
                require(link['link_type']=='repeated_contract_id','unexpected link type')
                require(all(any(q['field_id']=='contract_id' and q['page_number']==p and q['printed_text']==link['value'] for q in e['expected_fields']) for p in link['pages']),'cross page identity')
            if src['doc_kind']=='supplier_invoice':
                subtotal=Decimal('0')
                for row in src['rows']:
                    amount=(Decimal(row['qty_unit']['normalized_value'])*Decimal(row['unit_price']['normalized_value'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                    require(amount==Decimal(row['net_line']['normalized_value']),'line arithmetic');subtotal+=amount
                tax=(subtotal*Decimal(src['tax_rate'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                require(subtotal==Decimal(src['fields']['subtotal']['normalized_value']),'subtotal arithmetic')
                require(tax==Decimal(src['fields']['tax_amount']['normalized_value']),'tax arithmetic')
                require(subtotal+tax==Decimal(src['fields']['invoice_total']['normalized_value'])==Decimal(src['fields']['amount_due']['normalized_value']),'invoice arithmetic')
            if src['doc_kind']=='multi_page_service_record':
                for row in src['labor']:
                    ti=datetime.datetime.strptime(row['time_in']['printed_text'],'%H:%M');to=datetime.datetime.strptime(row['time_out']['printed_text'],'%H:%M')
                    require(Decimal(int((to-ti).total_seconds()))/3600==Decimal(row['hours']['normalized_value']),'labor arithmetic')
                require(e['expected_adjacent_page_pairs']==[[1,2],[2,3]],'adjacency')
            counts['fields']+=len(e['expected_fields']);counts['absences']+=len(e['expected_absences']);counts['tables']+=len(e['expected_tables'])
            rendered=pdfium.PdfDocument(pdf)
            for pn in range(len(rendered)):
                page=rendered[pn];bitmap=page.render(scale=1.5);im=bitmap.to_pil().convert('RGB')
                require(im.size==(918,1188),'render geometry');im.save(out/f'{fid}-p{pn+1}.png');images.append(im.copy())
                bitmap.close();page.close()
            rendered.close()
        require(counts['pages']==6 and counts['quantity_unit_cells']>=2,'required coverage')
        result['counts']=counts;result['checks'].extend(['canonical schema slots and typed source values','all visible PDF text, reference and expected bbox parity','no text overlap or page overflow','empty response boxes','invoice and labor arithmetic','page markers, adjacency and repeated identity','six PDFium renderings'])
        sheet=Image.new('RGB',(918*3,1188*2),'white')
        for i,im in enumerate(images):sheet.paste(im,((i%3)*918,(i//3)*1188))
        sheet.resize((1836,1584)).save(out/'contact-sheet.png')
        regen=[]
        for n in (1,2):
            dest=ROOT/'scratch'/a.run_id/f'generate-{n}'
            argv=[sys.executable,str(ROOT/'generation/create.py'),'--out',str(dest)]
            result['commands'].append(argv);output=run(argv)
            paths=sorted(str(p.relative_to(candidate)).replace('\\','/') for p in candidate.rglob('*') if p.is_file())
            require(paths==sorted(str(p.relative_to(dest)).replace('\\','/') for p in dest.rglob('*') if p.is_file()),'regeneration path set')
            require(all((candidate/p).read_bytes()==(dest/p).read_bytes() for p in paths),'regeneration byte mismatch')
            regen.append({'run':n,'files':len(paths),'all_bytes_equal':True,'stdout':output})
        result['regeneration']=regen;result['checks'].append('two complete fresh regenerations byte-identical to candidate')
        result['status']='passed'
    except Exception:
        result['status']='failed';result['failure']=traceback.format_exc()
    finally:
        result['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'status':result['status'],'evidence':str(out/'validation.json'),'checks_completed':len(result['checks'])}))
    return 0 if result['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
