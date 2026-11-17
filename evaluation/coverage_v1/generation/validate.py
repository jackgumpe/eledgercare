"""Frozen custodian checks for matched facts, factor isolation and source support.

Ideal-native witnesses are contract checks, never observed model output. This helper
executes no model and performs no diagnostic treatment. Independent admission is separate.
"""
from __future__ import annotations
import argparse, datetime, hashlib, importlib.metadata, io, json, re, subprocess, sys, traceback
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
sys.dont_write_bytecode=True
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(data):return hashlib.sha256(data).hexdigest()
def check(flag,message):
    if not flag:raise AssertionError(message)
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args])
def dump(path,value):path.write_bytes((json.dumps(value,indent=2)+'\n').encode())
def render(data,scale=300.0/72.0):
    doc=pdfium.PdfDocument(data);page=doc[0];bitmap=page.render(scale=scale)
    im=bitmap.to_pil().convert('RGB');bitmap.close();page.close();doc.close();return im
def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])>.5 and min(a[3],b[3])-max(a[1],b[1])>.5
def contains(a,b):return a[0]-.02<=b[0]<=b[2]<=a[2]+.02 and a[1]-.02<=b[1]<=b[3]<=a[3]+.02
def semantic(e):
    keys=('printed_text','normalized_value','value_type','quantity_unit')
    return {'fields':[{k:f[k] for k in ('field_id','page_number',*keys) if k in f} for f in e['expected_fields']],
      'tables':[{'table_id':t['table_id'],'column_ids':t['column_ids'],'rows':[
        {'row_id':r['row_id'],'page_number':r['page_number'],'cells':{col:{k:v[k] for k in keys if k in v} for col,v in r['cells'].items()}}
        for r in t['rows']]} for t in e['expected_tables']],
      'absences':[{k:a[k] for k in ('field_id','page_number','expected_state')} for a in e['expected_absences']]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--candidate-commit',required=True)
    p.add_argument('--public-repo',type=Path,required=True);p.add_argument('--run-id',required=True);a=p.parse_args()
    candidate=a.candidate.resolve();candidate.relative_to(ROOT)
    check(bool(re.fullmatch('[a-z0-9-]+',a.run_id)),'invalid run id')
    evidence=ROOT/'evidence'/a.run_id;check(not evidence.exists(),'existing evidence preserved');evidence.mkdir(parents=True)
    result={'schema':'eld-wp11-custodian-validation/1','candidate_commit':a.candidate_commit,
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':[],'status':'running',
      'independent_admission':'pending','model_execution':False,'native_witness_role':'synthetic ideal-reading source-contract check, not observed output',
      'command':[sys.executable,*sys.argv],'environment':{'python':sys.version,**{x:importlib.metadata.version(x) for x in ('pypdf','pypdfium2','Pillow')}}}
    try:
        check(git(ROOT,'rev-parse','HEAD').decode().strip()==a.candidate_commit,'candidate HEAD')
        check(not git(ROOT,'diff','HEAD','--').strip(),'tracked candidate changed')
        pins=read(ROOT/'provenance/source-pins.json')
        for f in pins['files']:
            data=(a.public_repo/f['path']).read_bytes()
            check(sha(data)==f['sha256'],'frozen support-source worktree bytes')
            check(git(a.public_repo,'rev-parse',pins['authority_commit']+':'+f['path']).decode().strip()==f['git_blob'],'frozen support-source Git identity')
        sys.path.insert(0,str(a.public_repo))
        from qualification.mapping_v1.common import parse_native,baseline_prediction,score_document,mapping
        from qualification.mapping_v1.mapper import extract_prediction as v1_prediction
        from typed_values import compare
        rules=mapping()
        m=read(candidate/'manifest.json');check((m['families'],m['documents'],m['pages'])==(3,12,12),'bounded counts')
        expected_paths={f['path'] for f in m['files']}|{'manifest.json'}
        check(expected_paths=={str(p.relative_to(candidate)).replace('\\','/') for p in candidate.rglob('*') if p.is_file()},'complete candidate path set')
        for f in m['files']:
            data=(candidate/f['path']).read_bytes();check(len(data)==f['bytes'] and sha(data)==f['sha256'],'manifest hash '+f['path'])
        result['checks'].extend(['exact committed helper/candidate/source pins','12 one-page documents / three families / four conditions','all manifest file sizes and SHA256 identities'])
        loaded={};control_results=[];counts={'fields':0,'tables':0,'rows':0,'cells':0,'absences':0,'quantity_unit_cells':0}
        for fx in m['fixtures']:
            fid=fx['fixture_id'];e=read(candidate/'expected'/f'{fid}.json');r=read(candidate/'reference'/f'{fid}.json')
            ann=read(candidate/'annotations'/f'{fid}.json');ops=read(candidate/'operators'/f'{fid}.json')
            pdf=(candidate/'pdfs'/f'{fid}.pdf').read_bytes();reader=PdfReader(io.BytesIO(pdf),strict=True)
            check(len(reader.pages)==1 and tuple(float(v) for v in reader.pages[0].mediabox)==(0,0,612,792.24),'PDF page count/box')
            check(e['fixture_id']==ann['fixture_id']==fid and e['family_id']==ann['family_id']==fx['family_id'],'fixture identity')
            check(e['variant_kind']==ann['condition']==fx['condition'] and e['split']=='diagnostic_eval','condition contract')
            check(ann['schema']=='eld-coverage-annotations/1' and ann['control_fixture_id']==fx['family_id']+'-control-v0','annotations schema')
            check(isinstance(ann['ideal_native'],str) and len(r['pages'])==1 and isinstance(r['coverage'],dict),'reference/witness contract')
            stream=reader.pages[0].get_contents().get_data().decode('ascii')
            check(stream=='\n'.join(ops['pages'][0])+'\n','source operators and actual PDF stream')
            if fx['condition']!='degraded':
                values=re.findall(r'1 0 0 1 ([0-9.]+) ([0-9.]+) Tm \(((?:\\.|[^\\)])*)\) Tj ET',stream)
                ordered=sorted([{'x':float(x),'y':float(y),'text':re.sub(r'\\([\\()])',r'\1',t)} for x,y,t in values],key=lambda q:(-q['y'],q['x']))
                check(len(values)==stream.count(' Tj ET') and '\n'.join(t['text'] for t in ordered)==r['pages'][0],'complete actual vector reading order')
                extracted=' '.join(reader.pages[0].extract_text().split())
                check(all(' '.join(t['text'].split()) in extracted for t in ordered),'independent PDF text extraction')
            else:
                check('BT ' not in stream and reader.pages[0].extract_text()=='','degraded PDF must be image-only')
                check(len(reader.pages[0].images)==1,'degraded one-image container')
            runs=r['runs'][0]
            check('\n'.join(t['text'] for t in runs)==r['pages'][0],'run/reference identity')
            for i,run in enumerate(runs):
                b=run['bbox_pt'];check(12<=b[0]<b[2]<=600 and 12<=b[1]<b[3]<=782,'text page bounds')
                for other in runs[i+1:]:check(not overlap(b,other['bbox_pt']),'text overlap '+fid)
            check(len(ann['fields'])==len(e['expected_fields']) and len(ann['tables'])==len(e['expected_tables']) and len(ann['absences'])==len(e['expected_absences']),'annotation slot counts')
            for field,af in zip(e['expected_fields'],ann['fields']):
                check(field['field_id']==af['field_id'] and field['label_printed']==af['label_printed'],'field annotation identity')
                check(any(q['text']==field['label_printed'] and contains(af['label_bbox_pt'],q['bbox_pt']) for q in runs),'label region visual fidelity')
                check(any(q['text']==field['printed_text'] and contains(af['value_bbox_pt'],q['bbox_pt']) for q in runs),'value region visual fidelity')
                check(compare(field['printed_text'],field,True,field['field_id'])['credited_exact'],'field type convention')
            for table,at in zip(e['expected_tables'],ann['tables']):
                check(table['table_id']==at['table_id'] and table['column_ids']==at['column_ids'],'table annotation identity')
                check(at['row_key_column'] in table['column_ids'],'row key column')
                check(len({row['cells'][at['row_key_column']]['printed_text'] for row in table['rows']})==len(table['rows']),'unique visible row keys')
                for header in at['headers']:check(any(q['text']==header and contains(at['header_bbox_pt'],q['bbox_pt']) for q in runs),'header region visual fidelity')
                for row in table['rows']:
                    check(list(row['cells'])==table['column_ids'],'column order')
                    for col,item in row['cells'].items():
                        check(any(q['text']==item['printed_text'] and q['bbox_pt']==item['bbox_pt'] for q in runs),'cell visible-value location')
                        check(compare(item['printed_text'],item,True,col)['credited_exact'],'cell type convention')
                        if col=='qty_unit':check(item['printed_text'].split()[1]==item['quantity_unit'],'printed unit metadata')
                        counts['quantity_unit_cells']+=int(col=='qty_unit')
                counts['rows']+=len(table['rows']);counts['cells']+=sum(len(x['cells']) for x in table['rows'])
            for ab,aa in zip(e['expected_absences'],ann['absences']):
                check(ab['expected_state']=='absent_blank' and ab['field_id']==aa['field_id'],'absence contract')
                check(not any(overlap(ab['bbox_pt'],q['bbox_pt']) for q in runs),'absence box contains visible text')
                check(any(q['text']==aa['label_printed'] and contains(aa['label_bbox_pt'],q['bbox_pt']) for q in runs),'absence label location')
            parsed=parse_native(ann['ideal_native']);check(not parsed['errors'],'ideal-native grammar')
            if fx['condition']=='control':
                for mapper_name,mapper in [('b0',baseline_prediction),('mapping_v1',v1_prediction)]:
                    predicted=mapper(parsed,rules);score=score_document(predicted,e,r)
                    for metric in ('fields','cells','rows','normalized_fields','normalized_cells','expected_absences'):
                        check(score[metric]['correct']==score[metric]['total'],'control unsupported '+mapper_name+' '+metric)
                    check(score['fields']['unmatched_candidates']==0 and score['cells']['extra_rows']==0 and score['cells']['extra_cells']==0,'control surplus candidates')
                    control_results.append({'fixture_id':fid,'mapper':mapper_name,'status':'supported_by_ideal_native_contract','score':score})
            preview=render(pdf,1.5);preview.save(evidence/f'{fid}.png')
            counts['fields']+=len(e['expected_fields']);counts['tables']+=len(e['expected_tables']);counts['absences']+=len(e['expected_absences'])
            loaded[fid]={'expected':e,'reference':r,'annotations':ann,'pdf':pdf,'preview':preview}
        result['checks'].extend(['exact expected/reference/annotations schemas and all printed locations','no text overlap/overflow; explicit empty boxes',
          'typed values and correctly printed quantities/units','faithful ideal-native grammar for all conditions','both unchanged mappers recover every control field/cell/row/absence without surplus'])
        family_checks=[]
        for family in ('WP11-F01','WP11-F02','WP11-F03'):
            group={c:loaded[family+'-'+c+'-v0'] for c in ('control','layout','vocabulary','degraded')}
            control=group['control'];sig=semantic(control['expected'])
            check(all(semantic(g['expected'])==sig for g in group.values()),'matched fact/absence/type/unit signatures')
            cr=control['reference']['runs'][0];lr=group['layout']['reference']['runs'][0];vr=group['vocabulary']['reference']['runs'][0]
            # Compare operator order, not geometric reading order, across moved elements.
            cr=sorted(cr,key=lambda x:x['ordinal']);lr=sorted(lr,key=lambda x:x['ordinal']);vr=sorted(vr,key=lambda x:x['ordinal'])
            check(len(cr)==len(lr)==len(vr),'factor text-run counts')
            for c,l,v in zip(cr,lr,vr):
                check(all(c[k]==l[k] for k in ('text','size_pt','font','role','ordinal')),'layout changed wording/style')
                check(all(c[k]==v[k] for k in ('x','y','size_pt','font','role','ordinal')),'vocabulary changed placement/style')
                if c['role'] not in ('field_label','absence_label','table_header'):check(c==v,'vocabulary changed non-label content')
            check(any((c['x'],c['y'])!=(l['x'],l['y']) for c,l in zip(cr,lr)),'layout must change arrangement')
            check(any(c['text']!=v['text'] for c,v in zip(cr,vr)),'vocabulary must change wording')
            for key in ('fields','tables','absences'):
                ca=control['annotations'][key];va=group['vocabulary']['annotations'][key]
                for c,v in zip(ca,va):
                    for name in c:
                        if name not in ('label_printed','headers'):check(c[name]==v[name],'vocabulary annotations moved region')
            check(group['degraded']['reference']['pages']==control['reference']['pages'] and group['degraded']['reference']['runs']==control['reference']['runs'],'degraded canonical text changed')
            check(group['degraded']['annotations']['ideal_native']==control['annotations']['ideal_native'],'degraded witness changed')
            canonical=render(control['pdf']);stored=Image.open(candidate/'rasters'/f'{family}-control-canonical.png').convert('RGB')
            check(canonical.size==(2550,3301) and canonical.tobytes()==stored.tobytes(),'control model-input raster identity')
            # Independent execution of the declared fixed operation sequence, not generator import.
            low=canonical.convert('L').resize((850,1100),resample=Image.Resampling.BOX)
            restored=low.resize((2550,3301),resample=Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(0.5))
            expected_image=restored.point([round(40+value*0.80) for value in range(256)]).convert('RGB')
            target=Image.open(candidate/'rasters'/f'{family}-degraded-target.png').convert('RGB')
            actual=render(group['degraded']['pdf'])
            check(actual.size==target.size==canonical.size and actual.tobytes()==target.tobytes()==expected_image.tobytes(),'degraded transform/container model-input pixel parity')
            check(actual.tobytes()!=canonical.tobytes(),'degradation has no pixel effect')
            family_checks.append({'family_id':family,'semantic_sha256':sha(json.dumps(sig,sort_keys=True).encode()),
              'facts_equal':True,'layout_only_arrangement':True,'vocabulary_only_wording':True,
              'vocabulary_region_font_wrapping_linecount_fixed':True,'glyph_extent_note':'Ink width changes with wording inside identical reserved label/header regions; position/font/no-wrap fixed.',
              'canonical_input_pixel_sha256':sha(canonical.tobytes()),'transformed_input_pixel_sha256':sha(actual.tobytes()),
              'degraded_final_render_exact_target':True,'model_input_size_px':list(actual.size)})
            previews=[group[c]['preview'] for c in ('control','layout','vocabulary','degraded')]
            w,h=previews[0].size;sheet=Image.new('RGB',(w*2,h*2),'white')
            for i,im in enumerate(previews):sheet.paste(im,((i%2)*w,(i//2)*h))
            sheet.save(evidence/f'{family}-contact-sheet.png')
        invoice=read(candidate/'sources/WP11-F02.json');subtotal=Decimal(0)
        for row in invoice['table']['rows']:
            c=row['cells'];amount=(Decimal(c['qty_unit']['normalized_value'])*Decimal(c['unit_price']['normalized_value'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            check(amount==Decimal(c['net_line']['normalized_value']),'invoice line arithmetic');subtotal+=amount
        fields={f['field_id']:f['normalized_value'] for f in invoice['fields']};tax=(subtotal*Decimal(invoice['tax_rate'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        check(subtotal==Decimal(fields['subtotal'])==Decimal(fields['taxable_subtotal']) and tax==Decimal(fields['tax_amount']) and subtotal+tax==Decimal(fields['invoice_total'])==Decimal(fields['amount_due']),'invoice total arithmetic')
        dump(evidence/'ideal-control-support.json',{'role':'synthetic source-contract proof, not OCR/model output','records':control_results})
        dump(evidence/'matched-condition-checks.json',{'families':family_checks,'invoice_arithmetic':'passed'})
        result['counts']=counts;result['checks'].extend(['matched semantic values/types/units/absences across all conditions','layout-only text/style and vocabulary-only fixed regions/font/linecount','degraded canonical-control raster transform and final rendered pixel identity','independent invoice arithmetic','twelve rendered previews and three matched contact sheets'])
        regenerations=[]
        for n in (1,2):
            dest=ROOT/'scratch'/a.run_id/f'regeneration-{n}'
            command=[sys.executable,str(ROOT/'generation/create.py'),'--out',str(dest)]
            executed=subprocess.run(command,capture_output=True)
            (evidence/f'regeneration-{n}.stdout.txt').write_bytes(executed.stdout);(evidence/f'regeneration-{n}.stderr.txt').write_bytes(executed.stderr)
            check(executed.returncode==0,'regeneration failed')
            check(expected_paths=={str(p.relative_to(dest)).replace('\\','/') for p in dest.rglob('*') if p.is_file()},'regeneration paths')
            check(all((candidate/f).read_bytes()==(dest/f).read_bytes() for f in expected_paths),'regeneration bytes')
            regenerations.append({'command':command,'exit_code':executed.returncode,'files':len(expected_paths),'all_bytes_identical':True})
        result['regenerations']=regenerations;result['checks'].append('two fresh complete byte-identical regenerations')
        result['status']='passed'
    except Exception:
        result['status']='failed';result['failure']=traceback.format_exc()
    finally:
        result['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();dump(evidence/'validation.json',result)
        print(json.dumps({'status':result['status'],'checks':len(result['checks']),'evidence':str(evidence/'validation.json')}))
    return 0 if result['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
