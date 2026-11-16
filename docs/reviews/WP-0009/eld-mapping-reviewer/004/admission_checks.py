"""Read-only sealed-corpus admission; content-bearing output stays ignored/sealed."""
from pathlib import Path
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import datetime, hashlib, importlib.util, importlib.metadata, json, re, subprocess, sys
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[5]
SEALED=Path('C:/Users/jackg/eLedgerCare-Mapping/WP-0009/sealed')
RECEIPT='559c5d09490b7729be26fb9bf9d872305cae3303'
PRIVATE=ROOT/'.scratch/wp0009-reviewer/admission-r1'
PUBLIC=Path(__file__).resolve().parent

def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args]).decode().strip()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def main():
    assert not git(ROOT,'status','--porcelain'), 'Review helper must execute clean'
    assert git(SEALED,'rev-parse','HEAD')==RECEIPT
    assert not git(SEALED,'status','--porcelain') and not git(SEALED,'remote')
    assert not PRIVATE.exists(), 'Preserve prior attempts; never overwrite'
    PRIVATE.mkdir(parents=True)
    index=load(SEALED/'inventory/sha256-r1.json')
    tracked=set(git(SEALED,'ls-files').splitlines())
    assert tracked=={x['path'] for x in index['files']}|{'inventory/sha256-r1.json'}
    assert len(index['files'])==39
    for item in index['files']:
        p=SEALED/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
    public=ROOT/'docs/evaluation/WP-0009/reservation'
    assert (public/'sealed-inventory.json').read_bytes()==(SEALED/'inventory/sha256-r1.json').read_bytes()
    assert sha(SEALED/'inventory/sha256-r1.json')=='c2971612374178aaf1194f4b3a48e0c8435d14305b813b290f0e1e2b856ac322'
    reservation=load(public/'reservation.json')
    for fixture in reservation['fixtures']:
        for item in fixture['artifacts']:
            p=SEALED/item['sealed_relative_path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
    candidate=SEALED/'corpus/r1'; manifest=load(candidate/'manifest.json')
    assert (manifest['families'],manifest['pdfs'],manifest['pages'])==(4,4,6)
    assert sorted(f['page_count'] for f in manifest['fixtures'])==[1,1,1,3]
    for item in manifest['files']:
        p=candidate/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
    old=[load(p) for p in (ROOT/'evaluation/synthetic/expected').glob('*v0*json')]
    old_fields={x['field_id'] for e in old for k in ['expected_fields','expected_absences'] for x in e[k]}
    old_tables={}
    for e in old:
        for table in e['expected_tables']:old_tables.setdefault(table['table_id'],set()).update(table['column_ids'])
    assert {f['fixture_id'] for f in manifest['fixtures']}.isdisjoint({e['fixture_id'] for e in old})
    assert {f['family_id'] for f in manifest['fixtures']}.isdisjoint({e['family_id'] for e in old})
    assert len({f['family_id'] for f in manifest['fixtures']})==4
    writer=ROOT/'evaluation/generation/pdf_writer.py'
    assert (SEALED/'generation/pdf_writer.py').read_bytes()==writer.read_bytes()
    counts=Counter();details=[];renders=[];observed_strings=[]
    def typed(item,slot):
        raw=item['printed_text'];value=item['normalized_value'];kind=item['value_type']
        assert isinstance(raw,str) and isinstance(value,str)
        if kind in ['text','identifier']:assert raw==value
        elif kind=='date_iso':assert datetime.date.fromisoformat(raw).isoformat()==value
        elif kind=='boolean_mark':assert {'[X]':'true','[ ]':'false'}[raw]==value
        elif kind in ['decimal_2','currency_usd','rate_percent']:
            number=raw
            if slot=='qty_unit':
                number,unit=raw.rsplit(' ',1);assert item['quantity_unit']==unit;counts['quantity_unit_cells']+=1
            number=Decimal(number.replace('$','').replace(',','').replace('%',''))
            assert number/(100 if kind=='rate_percent' else 1)==Decimal(value)
        else:raise AssertionError('Unsupported type')
    for fixture in manifest['fixtures']:
        fid=fixture['fixture_id'];e=load(candidate/'expected'/f'{fid}.json')
        src=load(candidate/'sources'/f'{fid}.json');ref=load(candidate/'reference'/f'{fid}.json');ops=load(candidate/'operators'/f'{fid}.json')
        assert e['fixture_id']==src['fixture_id']==ref['fixture_id']==ops['fixture_id']==fid
        assert e['family_id']==src['family_id']==fixture['family_id']
        pdf=candidate/'pdfs'/f'{fid}.pdf';reader=PdfReader(pdf,strict=True)
        assert len(reader.pages)==e['page_count']==fixture['page_count']
        page_runs=[]
        for pn,page in enumerate(reader.pages,1):
            stream=page.get_contents().get_data().decode('ascii')
            assert stream=='\n'.join(ops['pages'][pn-1]['operators'])+'\n'
            texts=re.findall(r'1 0 0 1 ([0-9.]+) ([0-9.]+) Tm \(((?:\\.|[^\\)])*)\) Tj ET',stream)
            runs=[{'x':float(x),'y':float(y),'text':re.sub(r'\\([\\()])',r'\1',t),'ordinal':i+1} for i,(x,y,t) in enumerate(texts)]
            assert len(runs)==stream.count(' Tj ET')
            ordered=sorted(runs,key=lambda r:(-r['y'],r['x'],r['ordinal']))
            assert '\n'.join(r['text'] for r in ordered)==ref['pages'][pn-1]
            assert [(r['text'],r['x'],r['y'],r['ordinal']) for r in ordered]==[(r['text'],r['x'],r['y'],r['ordinal']) for r in ref['runs'][pn-1]]
            extracted=' '.join(page.extract_text().split())
            assert all(' '.join(r['text'].split()) in extracted for r in runs)
            assert all(r['bbox_pt'][0]==r['x'] and r['bbox_pt'][1]==r['y'] and r['bbox_pt'][3]==r['y']+r['size_pt'] for r in ref['runs'][pn-1])
            page_runs.append(ref['runs'][pn-1]);counts['text_operators']+=len(runs);counts['pages']+=1
            observed_strings.extend(r['text'] for r in runs)
        slots=[]
        for field in e['expected_fields']:
            assert field['field_id'] in old_fields
            original=src['fields'][field['field_id']]
            assert all(field[k]==v for k,v in original.items())
            assert any(r['text']==field['label_printed'] for r in page_runs[field['page_number']-1])
            slots.append((field['page_number'],field['field_id'],field))
        source_rows={r['row_id']:r for v in src.values() if isinstance(v,list) for r in v if isinstance(r,dict) and 'row_id' in r}
        expected_row_ids=[]
        for table in e['expected_tables']:
            assert table['table_id'] in old_tables and set(table['column_ids'])<=old_tables[table['table_id']]
            assert table['page_numbers']==sorted({r['page_number'] for r in table['rows']})
            assert table['repeated_header_pages']==table['page_numbers'][1:]
            for row in table['rows']:
                original=source_rows[row['row_id']];expected_row_ids.append(row['row_id'])
                assert row['page_number']==original.get('page',row['page_number'])
                assert list(row['cells'])==table['column_ids']
                for slot,item in row['cells'].items():
                    if slot=='row_id':assert item['printed_text']==original['row_id']
                    else:assert all(item[k]==v for k,v in original[slot].items())
                    slots.append((row['page_number'],slot,item));counts['cells']+=1
                counts['rows']+=1
            counts['tables']+=1
        assert set(expected_row_ids)==set(source_rows) and len(expected_row_ids)==len(source_rows)
        for pn,slot,item in slots:
            typed(item,slot)
            assert any(r['text']==item['printed_text'] and r['bbox_pt']==item['bbox_pt'] for r in page_runs[pn-1])
        assert {a['field_id'] for a in e['expected_absences']}==set(src['absences'])
        for absent in e['expected_absences']:
            assert absent['field_id'] in old_fields and absent['expected_state']=='absent_blank'
            rr=page_runs[absent['page_number']-1];box=absent['bbox_pt']
            assert any(r['text']==absent['label_printed'] for r in rr)
            assert not any(min(box[2],r['bbox_pt'][2])-max(box[0],r['bbox_pt'][0])>0.5 and min(box[3],r['bbox_pt'][3])-max(box[1],r['bbox_pt'][1])>0.5 for r in rr)
        for marker in e['page_sentinels']:
            assert marker['sentinel_id'] in ref['pages'][marker['page_number']-1] and marker['page_label'] in ref['pages'][marker['page_number']-1]
        for link in e['cross_page_links']:
            assert all(any(f['page_number']==pn and f['printed_text']==link['value'] for f in e['expected_fields']) for pn in link['pages'])
        assert e['expected_adjacent_page_pairs']==[[p,p+1] for p in range(1,e['page_count'])]
        arithmetic=[]
        if 'tax_rate' in src:
            subtotal=Decimal(0)
            for row in src['rows']:
                actual=(Decimal(row['qty_unit']['normalized_value'])*Decimal(row['unit_price']['normalized_value'])).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
                assert actual==Decimal(row['net_line']['normalized_value']);subtotal+=actual
            tax=(subtotal*Decimal(src['tax_rate'])).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
            assert subtotal==Decimal(src['fields']['subtotal']['normalized_value'])
            assert tax==Decimal(src['fields']['tax_amount']['normalized_value'])
            assert subtotal+tax==Decimal(src['fields']['invoice_total']['normalized_value'])==Decimal(src['fields']['amount_due']['normalized_value'])
            arithmetic.append({'subtotal':str(subtotal),'tax':str(tax),'total':str(subtotal+tax)})
        if 'labor' in src:
            for row in src['labor']:
                start=datetime.datetime.strptime(row['time_in']['printed_text'],'%H:%M');end=datetime.datetime.strptime(row['time_out']['printed_text'],'%H:%M')
                actual=Decimal(int((end-start).total_seconds()))/Decimal(3600)
                assert actual==Decimal(row['hours']['normalized_value']);arithmetic.append({'row_id':row['row_id'],'hours':str(actual)})
        counts['fields']+=len(e['expected_fields']);counts['absences']+=len(e['expected_absences'])
        document=pdfium.PdfDocument(pdf)
        for pn in range(len(document)):
            page=document[pn];bitmap=page.render(scale=2);im=bitmap.to_pil().convert('RGB');out=PRIVATE/f'{fid}-p{pn+1}.png';im.save(out)
            renders.append({'fixture_id':fid,'page':pn+1,'path':out.relative_to(ROOT).as_posix(),'sha256':sha(out),'size':list(im.size)})
            bitmap.close();page.close()
        document.close()
        details.append({'fixture_id':fid,'source_expected_visible_parity':True,'arithmetic':arithmetic,'expected':e,'reference':ref})
    assert dict(counts)=={'text_operators':249,'pages':6,'cells':90,'rows':15,'tables':5,'fields':39,'absences':4,'quantity_unit_cells':3}
    # Independently invoke exact deterministic source with output-root guard redirected only.
    sys.path.insert(0,str(SEALED/'generation'))
    spec=importlib.util.spec_from_file_location('sealed_generator',SEALED/'generation/create.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=PRIVATE;sys.argv=[str(SEALED/'generation/create.py'),'--out',str(PRIVATE/'regenerated')];module.main()
    paths=sorted(p.relative_to(candidate) for p in candidate.rglob('*') if p.is_file())
    assert paths==sorted(p.relative_to(PRIVATE/'regenerated') for p in (PRIVATE/'regenerated').rglob('*') if p.is_file())
    assert all((candidate/p).read_bytes()==(PRIVATE/'regenerated'/p).read_bytes() for p in paths)
    # Public data contains opaque IDs/hashes/coarse coverage only; literal details stay sealed.
    payload='\n'.join(p.read_text(encoding='utf-8') for p in public.glob('*') if p.is_file())
    long_values={s for s in observed_strings if len(s)>=18 and not s.startswith('SYNTHETIC TRAINING DOCUMENT')}
    leaked=sorted(s for s in long_values if s in payload)
    assert not leaked,'Fresh visible string appears in public reservation'
    assert git(SEALED,'rev-parse','HEAD')==RECEIPT and not git(SEALED,'status','--porcelain')
    private_result={'status':'PASS','executing_head':git(ROOT,'rev-parse','HEAD'),'sealed_receipt':RECEIPT,'counts':dict(counts),'documents':details,'renders':renders,'regenerated_files_equal':len(paths),'public_literal_disclosure_hits':leaked,'environment':{'python':sys.version,'executable':sys.executable,**{p:importlib.metadata.version(p) for p in ['pypdf','pypdfium2','Pillow']}}}
    write(PRIVATE/'admission-details.json',private_result)
    private_inventory=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(PRIVATE.rglob('*')) if p.is_file()]
    write(PRIVATE/'inventory.json',{'files':private_inventory,'note':'inventory self excluded; public summary binds its digest'})
    summary={'status':'automated_checks_passed_visual_review_pending','executing_head':private_result['executing_head'],'sealed_receipt':RECEIPT,'sealed_inventory_sha256':sha(SEALED/'inventory/sha256-r1.json'),'tracked_sealed_files':40,'public_bound_artifacts':20,'counts':dict(counts),'independent_renders':6,'regenerated_files_equal':len(paths),'public_literal_disclosure_hits':0,'private_evidence_files':len(private_inventory),'private_inventory_path':str((PRIVATE/'inventory.json').relative_to(ROOT)).replace('\\','/'),'private_inventory_sha256':sha(PRIVATE/'inventory.json'),'environment':private_result['environment'],'source_modified':False,'model_inference':False}
    write(PUBLIC/'automated-summary.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
