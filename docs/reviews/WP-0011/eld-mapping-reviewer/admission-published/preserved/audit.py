"""Independent private admission checks; never mutates custodian input."""
import argparse,collections,copy,datetime,hashlib,importlib.abc,importlib.metadata,io,json,re,subprocess,sys,traceback
from decimal import Decimal
from pathlib import Path
HERE=Path(__file__).resolve().parent
SEALED=Path('C:/Users/jackg/eLedgerCare-Coverage/WP-0011/sealed')
REPO=Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-reviewer')
RECEIPT='6583715067d3a027dd2502ed9623cf02c545391d'
CORE='b5f33a65d463d4b9a5463fdb93353c0c7ac7c7f3'
INV='bd37f4020a4b5b185379d9d7d2e529b39ebc0d3fa0aa37802d2bccc0546c4330'
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton') or fullname=='q0harness.backend_torch':raise RuntimeError('Admission prohibits model imports')
sys.meta_path.insert(0,NoModel());sys.path.insert(0,str(REPO))
from qualification.mapping_v1.common import mapping,parse_native,baseline_prediction,score_document
from qualification.mapping_v1.mapper import extract_prediction
from typed_values import compare
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image,ImageFilter
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args])
def check(ok,why):
    if not ok:raise AssertionError(why)
def dump(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
def box_inside(inner,outer):return all([inner[0]>=outer[0]-.03,inner[1]>=outer[1]-.03,inner[2]<=outer[2]+.03,inner[3]<=outer[3]+.03])
def intersects(a,b):return min(a[2],b[2])>max(a[0],b[0])+.5 and min(a[3],b[3])>max(a[1],b[1])+.5
def semantics(e):
    def value(x):return {k:x[k] for k in ('printed_text','normalized_value','value_type','quantity_unit') if k in x}
    return {'fields':{(f['page_number'],f['field_id']):value(f) for f in e['expected_fields']},
      'cells':{(t['table_id'],r['row_id'],r['page_number'],col):value(v) for t in e['expected_tables'] for r in t['rows'] for col,v in r['cells'].items()},
      'tables':[(t['table_id'],t['column_ids'],[(r['row_id'],r['page_number']) for r in t['rows']]) for t in e['expected_tables']],
      'absences':{(a['page_number'],a['field_id']):a['expected_state'] for a in e['expected_absences']}}
def render(data):
    doc=pdfium.PdfDocument(data);check(len(doc)==1,'PDFium page count');page=doc[0];bitmap=page.render(scale=300/72);im=bitmap.to_pil().convert('RGB');bitmap.close();page.close();doc.close();return im
def degrade(im):return im.convert('L').resize((850,1100),Image.Resampling.BOX).resize((2550,3301),Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(.5)).point([round(40+.8*v) for v in range(256)]).convert('RGB')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);a=ap.parse_args();check(re.fullmatch('[a-z0-9-]+',a.attempt),'Attempt name')
    out=HERE/a.attempt;out.mkdir(exist_ok=False)
    result={'status':'RUNNING','helper_commit':git(HERE,'rev-parse','HEAD').decode().strip(),'public_head':git(REPO,'rev-parse','HEAD').decode().strip(),'sealed_receipt':RECEIPT,'candidate':CORE,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':{'python':sys.version,'executable':sys.executable,**{x:importlib.metadata.version(x) for x in ('pypdf','pypdfium2','Pillow')}},'checks':[],'fixtures':[]}
    def group(name,fn):
        try:value=fn();result['checks'].append({'name':name,'status':'PASS','evidence':value})
        except Exception:result['checks'].append({'name':name,'status':'FAIL','traceback':traceback.format_exc()})
    def identity():
        check(git(SEALED,'rev-parse','HEAD').decode().strip()==RECEIPT,'Sealed HEAD');check(not git(SEALED,'status','--porcelain').strip(),'Sealed dirty');check(not git(SEALED,'remote').strip(),'Sealed remote exists')
        data=(SEALED/'inventory/sha256-r1.json').read_bytes();check(sha(data)==INV,'Inventory digest');inv=json.loads(data)
        tracked=git(SEALED,'ls-tree','-r','--name-only',RECEIPT).decode().splitlines();check(set(tracked)=={x['path'] for x in inv['files']}|{'inventory/sha256-r1.json'},'Complete109 paths')
        for item in inv['files']:
            data=(SEALED/item['path']).read_bytes();check(len(data)==item['bytes'] and sha(data)==item['sha256'],'Input hash '+item['path']);check(data==git(SEALED,'show',RECEIPT+':'+item['path']),'Input Git bytes '+item['path'])
            if item['path'].startswith('corpus/'):check(data==git(SEALED,'show',CORE+':'+item['path']),'Frozen core corpus changed')
        for pin in load(SEALED/'provenance/source-pins.json')['files']:
            data=(REPO/pin['path']).read_bytes();check(sha(data)==pin['sha256'],'Support source hash');check(git(REPO,'rev-parse','HEAD:'+pin['path']).decode().strip()==pin['git_blob'],'Support source blob')
        public=load(REPO/'docs/evaluation/WP-0011/reservation/reservation.json');artifacts=[v for x in public['fixtures'] for v in x['artifacts']]
        for art in artifacts:
            data=(SEALED/art['sealed_relative_path']).read_bytes();check(len(data)==art['bytes'] and sha(data)==art['sha256'],'Public descriptor mismatch')
        return {'sealed_files':len(tracked),'inventory_entries':len(inv['files']),'public_descriptors':len(artifacts),'total_inventory_bytes':inv['total_bytes'],'source_files':len(load(SEALED/'provenance/source-pins.json')['files'])}
    group('exact_identity_and_complete_inventory',identity)
    corpus=SEALED/'corpus/r1';manifest=load(corpus/'manifest.json');loaded={};images={};counts=collections.Counter();support=[]
    check((manifest['families'],manifest['documents'],manifest['pages'])==(3,12,12),'Manifest counts')
    check({x['fixture_id'] for x in manifest['fixtures']}=={fam+'-'+cond+'-v0' for fam in ('WP11-F01','WP11-F02','WP11-F03') for cond in ('control','layout','vocabulary','degraded')} and len(manifest['fixtures'])==12,'Complete fixed family-condition matrix')
    def fixture(fx):
        fid=fx['fixture_id'];e=load(corpus/'expected'/f'{fid}.json');r=load(corpus/'reference'/f'{fid}.json');ann=load(corpus/'annotations'/f'{fid}.json');ops=load(corpus/'operators'/f'{fid}.json');pdf=(corpus/'pdfs'/f'{fid}.pdf').read_bytes();reader=PdfReader(io.BytesIO(pdf),strict=True)
        check(len(reader.pages)==1 and tuple(map(float,reader.pages[0].mediabox))==(0,0,612,792.24),'Page count/dimensions')
        check(e['fixture_id']==ann['fixture_id']==fid and e['family_id']==ann['family_id']==fx['family_id'],'Identity');check(e['variant_kind']==ann['condition']==fx['condition'],'Condition')
        stream=reader.pages[0].get_contents().get_data().decode('ascii');check(stream=='\n'.join(ops['pages'][0])+'\n','Actual PDF stream vs operators')
        runs=r['runs'][0];check('\n'.join(x['text'] for x in sorted(runs,key=lambda z:(-z['y'],z['x'],z['ordinal'])))==r['pages'][0],'Canonical reference order')
        if fx['condition']!='degraded':
            tokens=re.findall(r'1 0 0 1 ([0-9.]+) ([0-9.]+) Tm \(((?:\\.|[^\\)])*)\) Tj ET',stream)
            decoded=[{'x':float(x),'y':float(y),'text':re.sub(r'\\([\\()])',r'\1',text)} for x,y,text in tokens]
            check(len(tokens)==stream.count(' Tj ET')==len(runs),'Complete operator count')
            check('\n'.join(x['text'] for x in sorted(decoded,key=lambda z:(-z['y'],z['x'])))==r['pages'][0],'PDF operator reference parity')
            text=reader.pages[0].extract_text();check(all(x['text'] in text for x in decoded),'PDF extracted text parity')
        else:check('BT ' not in stream and reader.pages[0].extract_text()=='' and len(reader.pages[0].images)==1,'Image-only degradation container')
        for i,run in enumerate(runs):
            check(box_inside(run['bbox_pt'],[0,0,612,792.24]),'Visible text outside page')
            check(not any(intersects(run['bbox_pt'],v['bbox_pt']) for v in runs[i+1:]),'Text overlap')
        for f,af in zip(e['expected_fields'],ann['fields']):
            check(f['field_id']==af['field_id'] and f['label_printed']==af['label_printed'],'Field label identity')
            check(any(x['text']==f['printed_text'] and x['bbox_pt']==f['bbox_pt'] and box_inside(x['bbox_pt'],af['value_bbox_pt']) for x in runs),'Field visible value')
            check(any(x['text']==af['label_printed'] and box_inside(x['bbox_pt'],af['label_bbox_pt']) for x in runs),'Field visible label')
            check(compare(f['printed_text'],f,True,f['field_id'])['credited_exact'],'Field typed truth')
        for t,at in zip(e['expected_tables'],ann['tables']):
            check(t['table_id']==at['table_id'] and t['column_ids']==at['column_ids'],'Table annotation')
            check(len({row['cells'][at['row_key_column']]['printed_text'] for row in t['rows']})==len(t['rows']),'Unique visible row keys')
            for h in at['headers']:check(any(x['text']==h and box_inside(x['bbox_pt'],at['header_bbox_pt']) for x in runs),'Header visible region')
            for row in t['rows']:
                for col,v in row['cells'].items():
                    check(any(x['text']==v['printed_text'] and x['bbox_pt']==v['bbox_pt'] for x in runs),'Cell visible value');check(compare(v['printed_text'],v,True,col)['credited_exact'],'Cell typed truth')
                    if col=='qty_unit':check(v['quantity_unit']==v['printed_text'].split()[-1],'Quantity unit identity')
        for ab,aa in zip(e['expected_absences'],ann['absences']):
            check(ab['field_id']==aa['field_id'] and ab['label_printed']==aa['label_printed'] and ab['expected_state']=='absent_blank','Explicit absence semantics')
            check(not any(intersects(ab['bbox_pt'],x['bbox_pt']) for x in runs),'Absence region has text')
            check(any(x['text']==aa['label_printed'] and box_inside(x['bbox_pt'],aa['label_bbox_pt']) for x in runs),'Absence label visible')
        check([len(e[k]) for k in ('expected_fields','expected_tables','expected_absences')]==[len(ann[k]) for k in ('fields','tables','absences')],'Annotation cardinality')
        parsed=parse_native(ann['ideal_native']);check(not parsed['errors'],'Ideal witness parse')
        check(collections.Counter(b['text'] for pg in parsed['pages'] for b in pg['blocks'] if b['kind']!='table')==collections.Counter(x['text'] for x in runs if x['role'] not in ('table_header','table_cell')),'Ideal witness visible non-table text')
        tabletexts=[c['text'] for pg in parsed['pages'] for b in pg['blocks'] for row in b['rows'] for c in row]
        check(collections.Counter(tabletexts)==collections.Counter(x['text'] for x in runs if x['role'] in ('table_header','table_cell')),'Ideal witness visible table text')
        if fx['condition']=='control':
            for name,mapper in [('b0',baseline_prediction),('mapping_v1',extract_prediction)]:
                s=score_document(mapper(parsed,mapping()),e,r)
                check(s['eligible_for_exact_credit'] and all(s[k]['correct']==s[k]['total'] for k in ('fields','normalized_fields','cells','normalized_cells','rows','expected_absences','page_count')),'Complete control support '+name)
                check(s['fields']['unmatched_candidates']==s['cells']['extra_rows']==s['cells']['extra_cells']==0,'Control surplus')
                support.append({'fixture_id':fid,'mapper':name,'score':s})
        im=render(pdf);check(im.size==(2550,3301),'Canonical raster size');im.save(out/(fid+'.png'));images[fid]=im
        loaded[fid]={'fx':fx,'expected':e,'reference':r,'annotations':ann,'operators':ops}
        counts.update(fields=len(e['expected_fields']),tables=len(e['expected_tables']),rows=sum(len(t['rows']) for t in e['expected_tables']),cells=sum(len(row['cells']) for t in e['expected_tables'] for row in t['rows']),absences=len(e['expected_absences']),text_runs=len(runs))
        result['fixtures'].append({'fixture_id':fid,'pdf_sha256':sha(pdf),'raster_sha256':sha(im.tobytes()),'render_file':fid+'.png','page_count':1,'visible_operator_count':len(runs),'reference_sha256':sha((corpus/'reference'/f'{fid}.json').read_bytes())})
        return {'fixture_id':fid,'text_runs':len(runs),'raster_sha256':sha(im.tobytes())}
    for fx in manifest['fixtures']:group('fixture:'+fx['fixture_id'],lambda fx=fx:fixture(fx))
    def family(fam):
        variants={cond:loaded[fam+'-'+cond+'-v0'] for cond in ('control','layout','vocabulary','degraded')};base=variants['control'];source=load(corpus/'sources'/f'{fam}.json')
        for item in variants.values():check(semantics(item['expected'])==semantics(base['expected']),'Paired semantic facts/units/absence changed')
        check([f['printed_text'] for f in source['fields']]==[f['printed_text'] for f in base['expected']['expected_fields']],'Source fields')
        check(source['table']['columns']==base['expected']['expected_tables'][0]['column_ids'],'Source columns')
        for src,row in zip(source['table']['rows'],base['expected']['expected_tables'][0]['rows']):
            check(src['row_id']==row['row_id'] and all({k:v for k,v in row['cells'][col].items() if k!='bbox_pt'}==value for col,value in src['cells'].items()),'Source cells')
        br=base['reference']['runs'][0];lr=variants['layout']['reference']['runs'][0];vr=variants['vocabulary']['reference']['runs'][0]
        check(collections.Counter((x['text'],x['size_pt'],x['font'],x['role']) for x in br)==collections.Counter((x['text'],x['size_pt'],x['font'],x['role']) for x in lr),'Layout wording/style change')
        byordinal=lambda rows:sorted(rows,key=lambda x:x['ordinal'])
        check(len(vr)==len(br),'Vocabulary text count')
        for x,y in zip(byordinal(br),byordinal(vr)):
            check(all(x[k]==y[k] for k in ('x','y','size_pt','font','role','ordinal')),'Vocabulary geometry/style changed')
            if x['role'] not in ('field_label','table_header','absence_label'):check(x==y,'Vocabulary non-label change')
        check(variants['degraded']['reference']['pages']==base['reference']['pages'],'Degraded reference mismatch')
        for key in ('fields','tables','absences','ideal_native'):check(variants['degraded']['annotations'][key]==base['annotations'][key],'Degraded annotation factor change')
        control=images[fam+'-control-v0'];degraded=images[fam+'-degraded-v0'];computed=degrade(control)
        check(control.tobytes()==Image.open(corpus/'rasters'/f'{fam}-control-canonical.png').convert('RGB').tobytes(),'Control canonical pixel mismatch')
        check(computed.tobytes()==degraded.tobytes()==Image.open(corpus/'rasters'/f'{fam}-degraded-target.png').convert('RGB').tobytes(),'Degradation/recontainer pixel mismatch')
        if source.get('tax_rate'):
            total=Decimal(0)
            for row in source['table']['rows']:
                cells=row['cells'];line=Decimal(cells['qty_unit']['normalized_value'])*Decimal(cells['unit_price']['normalized_value'])-Decimal(cells['line_discount']['normalized_value']);check(line==Decimal(cells['net_line']['normalized_value']),'Line arithmetic');total+=line
            fields={x['field_id']:x['normalized_value'] for x in source['fields']};tax=(total*Decimal(source['tax_rate'])).quantize(Decimal('.01'));check(total==Decimal(fields['subtotal']) and tax==Decimal(fields['tax_amount']) and total+tax==Decimal(fields['invoice_total'])==Decimal(fields['amount_due']),'Invoice arithmetic')
        return {'family':fam,'semantic_pairs':3,'degradation_exact':True,'layout_style_and_wording_exact':True,'vocabulary_positions_fonts_nonlabels_exact':True}
    for fam in ('WP11-F01','WP11-F02','WP11-F03'):group('family:'+fam,lambda fam=fam:family(fam))
    def regeneration():
        stage=HERE/'.scratch'/a.attempt;gen=stage/'generation';gen.mkdir(parents=True,exist_ok=False)
        for name in ('create.py','pdf_writer.py'):(gen/name).write_bytes((SEALED/'generation'/name).read_bytes())
        proc=subprocess.run([sys.executable,'-B',str(gen/'create.py'),'--out',str(stage/'corpus/r1')],capture_output=True)
        (out/'regeneration.stdout.txt').write_bytes(proc.stdout);(out/'regeneration.stderr.txt').write_bytes(proc.stderr);check(proc.returncode==0,'Independent regeneration command failed')
        actual={p.relative_to(corpus).as_posix():p.read_bytes() for p in corpus.rglob('*') if p.is_file()};rebuilt={p.relative_to(stage/'corpus/r1').as_posix():p.read_bytes() for p in (stage/'corpus/r1').rglob('*') if p.is_file()};check(actual==rebuilt,'Independent regeneration differs')
        return {'files':len(actual),'returncode':proc.returncode,'exact_bytes':True}
    group('independent_regeneration_in_owned_scratch',regeneration)
    result['counts']=dict(counts);result['support_checks']=len(support);dump(out/'ideal-control-independent-scores.json',support)
    result['failures']=sum(x['status']=='FAIL' for x in result['checks']);result['status']='PASS' if result['failures']==0 else 'FAIL';result['model_imports']=[x for x in sys.modules if x.split('.')[0] in ('torch','transformers','triton')]
    check(not git(SEALED,'status','--porcelain').strip(),'Custodian input changed');dump(out/'audit.json',result);print(json.dumps({'status':result['status'],'checks':len(result['checks']),'failures':result['failures'],'rendered':len(result['fixtures']),'counts':dict(counts),'support_checks':len(support)}));return bool(result['failures'])
if __name__=='__main__':raise SystemExit(main())
