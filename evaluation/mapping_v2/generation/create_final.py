"""Deterministic WP13 final corpus from frozen foundations and accepted public catalog.

Writes only an absent owned output and a unique retained attempt. No OCR, mapper,
scorer, model, service, process inspection or network use is present.
"""
from __future__ import annotations
import argparse,copy,datetime,hashlib,html,importlib.metadata,io,json,subprocess,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pdf_writer as pw
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[1]
WIDTH,HEIGHT=612.0,792.24
ROLES={'pdf':'pdfs','expected':'expected','reference':'reference','policy':'policy','source':'sources','operators':'operators','render':'renders'}

def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads((ROOT/path).read_bytes())
def require(ok,message):
    if not ok:raise AssertionError(message)
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],stderr=subprocess.PIPE)
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not isinstance(data,bytes):data=(json.dumps(data,indent=2)+'\n').encode()
    with path.open('xb') as stream:stream.write(data)
    return data
def truth(item):return {k:item[k] for k in ('printed_text','normalized_value','value_type','quantity_unit') if k in item}
def native_box(box):return [round(box[0]/WIDTH*1000),round((HEIGHT-box[3])/HEIGHT*1000),round(box[2]/WIDTH*1000),round((HEIGHT-box[1])/HEIGHT*1000)]
def render(data):
    doc=pdfium.PdfDocument(data);page=doc[0];bitmap=page.render(scale=300/72)
    image=bitmap.to_pil().convert('RGB');bitmap.close();page.close();doc.close()
    require(image.size==(2550,3301),'canonical render dimensions')
    output=io.BytesIO();image.save(output,format='PNG',compress_level=9)
    return output.getvalue(),sha(image.tobytes())

def source_check(commit):
    require(ROOT.resolve()==Path('C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/sealed').resolve(),'wrong custody root')
    require(git('branch','--show-current').decode().strip()=='sealed/wp-0013' and not git('remote').strip(),'wrong branch or remote')
    pins=load('provenance/final-source-pins.json')
    for item in pins['foundation_files']:
        data=(ROOT/item['path']).read_bytes()
        require(len(data)==item['bytes'] and sha(data)==item['sha256'],'foundation changed '+item['path'])
    for item in pins['public_source_files']:
        data=(ROOT/item['private_copy']).read_bytes()
        require(len(data)==item['bytes'] and sha(data)==item['sha256'],'protocol checkpoint changed')
    for path in ('generation/create_final.py','generation/pdf_writer.py','finalization/plan-r1.json','provenance/final-source-pins.json'):
        require(git('show',commit+':'+path)==(ROOT/path).read_bytes(),'generation source differs from frozen commit '+path)
    require(sha((ROOT/'protocol_checkpoint/catalog.json').read_bytes())==pins['catalog_sha256'],'catalog hash')
    return pins

class Form:
    def __init__(self,family,template,case,plan,catalog):
        self.family,self.template,self.case,self.plan=family,template,case,plan
        self.fixture_id=family['family_id']+'-'+case+'-v0';self.font=plan['fonts']
        self.profile=next(p for p in catalog['profiles'] if p['profile']==family['profile'])
        self.field_rules={f['field_id']:f for f in self.profile['fields']};self.table_rule=self.profile['tables'][0]
        self.canvas=pw.PdfPageCanvas(WIDTH,HEIGHT);self.runs=[];self.blocks=[];self.occurrences=[]
        self.expected={'schema_version':'1.0.0','fixture_id':self.fixture_id,'family_id':family['family_id'],'doc_kind':family['doc_kind'],
          'split':'vocabulary_eval','variant_kind':case,'page_count':1,'parent_fixture_id':None,'expected_fields':[],'expected_tables':[],
          'expected_absences':[],'page_sentinels':[],'expected_adjacent_page_pairs':[],'cross_page_links':[]}
        table=family['table']
        self.policy={'schema':'eld-mapping-v2-policy/1','fixture_id':self.fixture_id,'family_id':family['family_id'],'case':case,'profile':family['profile'],
          'page_count':1,'catalog_sha256':sha((ROOT/'protocol_checkpoint/catalog.json').read_bytes()),'ideal_native':'',
          'tables':[{'table_id':table['table_id'],'column_ids':table['columns'],'row_ids':[r['row_id'] for r in table['rows']]}],'slots':[]}

    def text(self,text,x,y,font,size,role,anchor,limit=532,native=False):
        ink=list(self.canvas.draw_text(text,x,y,font,size_pt=size,max_width_pt=limit))
        self.runs.append({'ordinal':len(self.runs),'text':text,'baseline':[x,y],'font':font,'size_pt':size,'bbox_pt':ink,'role':role,'anchor':anchor})
        if native:self.blocks.append({'kind':'footer' if role=='footer' else 'text','bbox_pt':ink,'body':text})
        return ink

    def label(self,key):
        return self.plan['unsupported_fields'][self.family['profile']][key] if self.case=='unsupported' else self.field_rules[key]['aliases'][0]

    def pair(self,key,label,value,baseline,label_region,value_region,anchor,blank=False):
        # Explicit two-cell row; spaces between frozen text regions remain a divider gutter.
        self.canvas.rect_fill_stroke(40,baseline-4,532,18,fill_rgb=(1,1,1),stroke_rgb=(.72,.75,.77),line_width=.4)
        self.canvas.line(244,baseline-4,244,baseline+14,stroke_rgb=(.72,.75,.77),line_width=.4)
        self.text(label,40,baseline,'bold',self.font['field_label'],'field_label',anchor+'.label',194)
        if value:self.text(value,252,baseline,'regular',self.font['field_value'],'field_value',anchor+'.value',320)
        occurrence={'label_printed':label,'value_printed':value,'label_bbox_pt':label_region,'value_bbox_pt':value_region}
        self.occurrences.append({'anchor':anchor,'field_id':key,'blank':blank,**occurrence})
        self.blocks.append({'kind':'table','bbox_pt':[40,baseline-4,572,baseline+14],
          'body':'<table><tr><td>'+html.escape(label)+'</td><td>'+html.escape(value)+'</td></tr></table>'})
        return occurrence

    def fields(self):
        target=self.family['reserved_conflict']['field_id'];config=self.plan['conflicts'][self.family['family_id']]
        for item,position in zip(self.family['fields'],self.template['fields']):
            key=item['field_id'];label=self.label(key)
            occurrence=self.pair(key,label,item['printed_text'],position['baseline'],position['label_region'],position['value_region'],'field.'+key)
            slot={'kind':'field','page_number':1,'field_id':key,'truth_status':'known','action':'abstain' if self.case=='unsupported' else 'assign',
              'reason':'unsupported_vocabulary' if self.case=='unsupported' else 'supported','truth':truth(item),'evidence':[occurrence]}
            if self.case=='conflict' and key==target:
                box=self.template['conflict_reserve_region'];y=box[3]-38
                self.text(self.plan['conflict_caption'],40,box[3]-14,'regular',self.font['caption'],'conflict_notice','conflict.caption',native=True)
                other=item if config['value_source']=='original' else self.family['reserved_conflict']['alternate_value']
                extra=self.pair(key,config['extra_label'],other['printed_text'],y,[40,y-2,234,y+12],[252,y-2,572,y+12],'conflict.'+key)
                slot.update(action='abstain',reason=config['mode'],truth_status=config['truth_status'])
                slot['evidence'].append(extra)
                if slot['truth_status']!='known':slot['truth']=None
            if slot['truth_status']=='known':self.expected['expected_fields'].append({'field_id':key,'page_number':1,'label_printed':label,**truth(item),'bbox_pt':position['value_region']})
            self.policy['slots'].append(slot)

    def table(self):
        spec=self.family['table'];layout=self.template['table'];columns=spec['columns'];top=layout['header_baseline'];widths=layout['column_widths_pt']
        headers=self.plan['unsupported_headers'][spec['table_id']] if self.case=='unsupported' else self.table_rule['alias_headers']
        x=40;header_boxes=[];self.canvas.rect_fill_stroke(40,top-8,532,24,fill_rgb=(.91,.94,.96),line_width=.4)
        for index,(head,width) in enumerate(zip(headers,widths)):
            self.text(head,x+3,top,'bold',self.font['table_header'],'table_header','table.'+spec['table_id']+'.header.'+columns[index],width-6)
            header_boxes.append([x,top-8,x+width,top+16]);x+=width
        body='<table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr>';rows=[]
        for ri,row in enumerate(spec['rows']):
            y=top-(ri+1)*layout['row_height_pt'];x=40;cells={};body+='<tr>'
            for ci,(column,width) in enumerate(zip(columns,widths)):
                item=row['cells'][column];anchor='table.'+spec['table_id']+'.row.'+row['row_id']+'.'+column
                self.text(item['printed_text'],x+3,y,'regular',self.font['table_cell'],'table_cell',anchor,width-6)
                box=[x,y-8,x+width,y+16];cells[column]={**truth(item),'bbox_pt':box}
                evidence={'label_printed':headers[ci],'value_printed':item['printed_text'],'label_bbox_pt':header_boxes[ci],'value_bbox_pt':box}
                self.occurrences.append({'anchor':anchor,'table_id':spec['table_id'],'row_ordinal':ri,'row_id':row['row_id'],'column_id':column,**evidence})
                self.policy['slots'].append({'kind':'cell','page_number':1,'table_id':spec['table_id'],'row_ordinal':ri,'row_id':row['row_id'],'column_id':column,
                  'truth_status':'known','truth':truth(item),'action':'abstain' if self.case=='unsupported' else 'assign',
                  'reason':'unsupported_vocabulary' if self.case=='unsupported' else 'supported','evidence':[evidence]})
                body+='<td>'+html.escape(item['printed_text'])+'</td>';x+=width
            self.canvas.line(40,y-8,572,y-8,stroke_rgb=(.72,.75,.77),line_width=.4)
            rows.append({'row_id':row['row_id'],'page_number':1,'cells':cells});body+='</tr>'
        body+='</table>'
        self.blocks.append({'kind':'table','bbox_pt':layout['region'],'body':body})
        self.expected['expected_tables'].append({'table_id':spec['table_id'],'page_numbers':[1],'repeated_header_pages':[],'column_ids':columns,'rows':rows})

    def absence(self):
        item=self.family['absence'];pos=self.template['absence'];key=item['field_id'];label=self.label(key);y=pos['label_region'][1]+2
        ev=self.pair(key,label,'',y,pos['label_region'],pos['blank_region'],'absence.'+key,True)
        self.expected['expected_absences'].append({'field_id':key,'page_number':1,'label_printed':label,'expected_state':'absent_blank','bbox_pt':pos['blank_region']})
        self.policy['slots'].append({'kind':'absence','page_number':1,'field_id':key,'truth_status':'known','truth':{'printed_text':'','expected_state':'absent_blank'},
          'action':'abstain' if self.case=='unsupported' else 'assign','reason':'unsupported_vocabulary' if self.case=='unsupported' else 'supported','evidence':[ev]})

    def compose(self):
        self.text(self.family['title'],*self.template['title_baseline'],'bold',self.font['title'],'title','furniture.title',native=True)
        self.text(self.family['subtitle'],*self.template['subtitle_baseline'],'regular',self.font['subtitle'],'subtitle','furniture.subtitle',native=True)
        self.canvas.line(40,707,572,707,line_width=1)
        self.fields();self.table();self.absence()
        for i,(text,y) in enumerate(zip(self.plan['footer'],self.template['footer_baselines'])):
            self.text(text,40,y,'regular',self.font['footer'],'footer','furniture.footer.'+str(i),native=True)
        runs=sorted(self.runs,key=lambda r:(-r['baseline'][1],r['baseline'][0],r['ordinal']))
        blocks=sorted(self.blocks,key=lambda b:(native_box(b['bbox_pt'])[1],native_box(b['bbox_pt'])[0]))
        self.policy['ideal_native']='<PAGE>\n'+'\n'.join('<BLOCK>'+b['kind']+'['+','.join(map(str,native_box(b['bbox_pt'])))+']<FORK>'+b['body'] for b in blocks)
        reference={'pages':['\n'.join(r['text'] for r in runs)],'runs':[runs],'coverage':{'status':'complete_canonical_visible_text','page_size_pt':[WIDTH,HEIGHT],
          'ordering':'page; baseline descending; x ascending; source operator tie','includes':'all title/footer/notice/labels/headers/values/cells including all duplicate occurrences',
          'line_wrapping':False,'reference_role':'intended transcription from printed source; not observed OCR','bbox_convention':'PDF points, left/bottom/right/top'}}
        source={'schema':'eld-wp13-final-source/1','fixture_id':self.fixture_id,'family_id':self.family['family_id'],'case':self.case,
          'foundation_family':self.family,'foundation_template':self.template,'catalog_sha256':self.policy['catalog_sha256'],'source_occurrences':self.occurrences,
          'furniture_and_text_runs':self.runs,'native_blocks':blocks,'conflict_plan':self.plan['conflicts'][self.family['family_id']] if self.case=='conflict' else None,
          'foundation_mutated':False,'source_anchor_convention':'field.<id>, absence.<id>, conflict.<id>, table.<table>.row.<row>.<column>, furniture.*'}
        return pw.serialize_pdf([self.canvas],title=self.fixture_id),reference,source

def generate(out,commit):
    pins=source_check(commit);require(not out.exists(),'existing corpus destination must be preserved')
    plan=load('finalization/plan-r1.json');families=load('foundations/r1/families.json')['families'];templates=load('foundations/r1/templates.json')['templates'];catalog=load('protocol_checkpoint/catalog.json')
    pw.FIXED_PDF_DATE=plan['pdf_date'];pw.PRODUCER_TAG='eLedgerCare WP-0013 sealed vocabulary corpus generator 1'
    out.mkdir(parents=True);fixtures=[];files=[]
    for family,template in zip(families,templates):
        for case in plan['cases']:
            form=Form(family,template,case,plan,catalog);pdf,reference,source=form.compose();png,pixels=render(pdf)
            objects={'pdf':pdf,'expected':form.expected,'reference':reference,'policy':form.policy,'source':source,
              'operators':{'fixture_id':form.fixture_id,'page_size_pt':[WIDTH,HEIGHT],'ops':form.canvas.ops,'runs':form.runs},'render':png}
            descriptors=[]
            for role,obj in objects.items():
                ext='.pdf' if role=='pdf' else '.png' if role=='render' else '.json';rel=ROLES[role]+'/'+form.fixture_id+ext
                data=write(out/rel,obj);entry={'path':rel,'role':role,'bytes':len(data),'sha256':sha(data)};files.append(entry);descriptors.append(entry)
            fixtures.append({'fixture_id':form.fixture_id,'family_id':family['family_id'],'case':case,'page_count':1,'render_size_px':[2550,3301],'render_pixels_sha256':pixels,
              'artifacts':descriptors,'policy_counts':{'slots':len(form.policy['slots']),'known':sum(s['truth_status']=='known' for s in form.policy['slots']),
                'ambiguous':sum(s['truth_status']=='ambiguous' for s in form.policy['slots']),'required_abstentions':sum(s['action']=='abstain' for s in form.policy['slots'])}})
    manifest={'schema':'eld-wp13-corpus-manifest/1','generator_commit':commit,'foundation_receipt':pins['foundation_receipt'],'protocol_source':pins['protocol_source'],
      'protocol_review':pins['independent_protocol_review'],'catalog_sha256':pins['catalog_sha256'],'protocol_sha256':pins['protocol_sha256'],'families':4,'documents':12,'pages':12,
      'fixtures':fixtures,'files':files,'file_count_excluding_manifest':len(files),'renderer':{'pypdfium2':importlib.metadata.version('pypdfium2'),'Pillow':importlib.metadata.version('Pillow'),
        'scale':300/72,'size_px':[2550,3301]},'coverage_limits':plan['coverage_limits'],'future_public_prefix':'evaluation/mapping_v2/corpus/r1/'}
    write(out/'manifest.json',manifest)
    return manifest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--source-commit',required=True);parser.add_argument('--run-id',required=True);a=parser.parse_args()
    out=(ROOT/a.output).resolve();out.relative_to(ROOT.resolve());require(a.run_id.replace('-','').isalnum(),'invalid run ID')
    receipt_path=ROOT/'evidence'/a.run_id/'receipt.json';require(not receipt_path.parent.exists(),'existing attempt must be retained');receipt_path.parent.mkdir(parents=True)
    receipt={'schema':'eld-wp13-generation-receipt/1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],
      'source_commit':a.source_commit,'output_relative':str(out.relative_to(ROOT)).replace('\\','/'),'status':'running','model_inference':False}
    try:
        manifest=generate(out,a.source_commit);receipt.update(status='passed',documents=manifest['documents'],pages=manifest['pages'],artifact_files=manifest['file_count_excluding_manifest']+1)
    except Exception:receipt.update(status='failed',failure=traceback.format_exc())
    finally:
        receipt['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(receipt_path,receipt)
        print(json.dumps({'status':receipt['status'],'receipt':str(receipt_path),'documents':receipt.get('documents')}))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
