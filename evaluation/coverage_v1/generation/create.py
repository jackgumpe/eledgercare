"""Three fresh content families x four matched conditions; no model or output reads.

Canonical forms use frozen B0 labels/header signatures. Private source facts are new.
Only layout coordinates, displayed label/header vocabulary, or one scan-quality recipe
varies from each family's control. Never overwrites an output directory.
"""
from __future__ import annotations
import argparse, copy, hashlib, html, io, json
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageFilter
import pdf_writer as pw

ROOT=Path(__file__).resolve().parents[1]
pw.FIXED_PDF_DATE='D:20261117000000Z'
pw.PRODUCER_TAG='eLedgerCare WP-0011 matched synthetic diagnostic generator 1'
WIDTH=612.0; HEIGHT=792.24
CONDITIONS=('control','layout','vocabulary','degraded')
RECIPE={'id':'scan-r1-fixed','parent':'same-family control canonical model-input raster',
 'renderer':'pypdfium2 5.15.2 / PDFium 159.0.8149.0','render_scale':300.0/72.0,
 'canonical_size_px':[2550,3301],'page_size_pt':[612.0,792.24],
 'steps':[{'operation':'grayscale','mode':'L'},
          {'operation':'downsample','size_px':[850,1100],'resampling':'BOX'},
          {'operation':'upsample','size_px':[2550,3301],'resampling':'BILINEAR'},
          {'operation':'gaussian_blur','radius_px':0.5},
          {'operation':'fixed_tone_lut','formula':'round(40 + 0.80 * input)','range':[40,244]}],
 'embedding':'lossless Flate RGB, unchanged page box; final render must equal transformed pixels exactly',
 'severity_selection':'fixed before first generation; no model-based selection or severity search',
 'interpretation':'One composite scan-quality condition, not separate attribution among recipe components.'}

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,indent=2,ensure_ascii=True)+'\n').encode())
def sha(data):return hashlib.sha256(data).hexdigest()
def val(raw,typ='text',normal=None,**extra):
    return {'printed_text':raw,'normalized_value':raw if normal is None else normal,'value_type':typ,**extra}
def ident(x):return val(x,'identifier')
def dec(x):return val(x,'decimal_2')
def money(x):return val('$'+x,'currency_usd',x)
def date(x):return val(x,'date_iso')
def pct(x):return val(x+'%','rate_percent','0.0000')
def field(key,label,alternate,item):return {'field_id':key,'control_label':label,'vocabulary_label':alternate,**item}

FAMILIES=[
 {'family_id':'WP11-F01','doc_kind':'work_order','title':'Window maintenance work order',
  'subtitle':'Fictional Amber Otter housing workshop',
  'fields':[
   field('work_order_id','Work Order ID','Repair record',ident('WO-0008645')),
   field('property_name','Property','Premises name',val('Fictional Amber Otter Court')),
   field('building_unit','Building / Unit','Place within site',ident('Block R / Unit 007C')),
   field('requested_date','Requested Date','Opened on',date('2026-04-09')),
   field('trade_category','Trade Category','Work discipline',val('Carpentry / sash hardware')),
   field('assigned_tech','Assigned Technician','Worker assigned',val('Fictional Nola Wren')),
   field('completion_status','Work Order Status','Job state',val('Closed - sash travels freely'))],
  'absence':{'field_id':'resident_contact','control_label':'Resident Contact','vocabulary_label':'Occupant callback'},
  'table':{'table_id':'stock_parts','row_key_column':'part_sku',
   'columns':['part_sku','part_desc','bin_loc','qty_used'],
   'headers':['Part SKU','Part Description','Bin','Qty Used'],
   'vocabulary_headers':['Stock reference','Item supplied','Shelf','Used count'],
   'widths':[106,246,82,98],
   'rows':[{'row_id':'W-A','cells':{'part_sku':ident('00091284'),'part_desc':val('Nylon sash guide'),
              'bin_loc':ident('S-006'),'qty_used':dec('3.00')}},
           {'row_id':'W-B','cells':{'part_sku':ident('00046193'),'part_desc':val('Window stop fastener'),
              'bin_loc':ident('S-021'),'qty_used':dec('6.00')}}]}},
 {'family_id':'WP11-F02','doc_kind':'service_invoice','title':'Service and materials invoice',
  'subtitle':'Fictional Violet Acorn service desk',
  'fields':[
   field('invoice_number','Invoice No','Billing reference',ident('IV-0005638')),
   field('invoice_date','Invoice Date','Billed on',date('2026-05-04')),
   field('due_date','Due Date','Settle by',date('2026-06-03')),
   field('work_order_ref','Work Order Ref','Related repair',ident('WO-0003827')),
   field('payment_terms','Terms','Settlement rule',val('30 days from issue')),
   field('subtotal','Line Net Subtotal','Charges before levy',money('145.20')),
   field('taxable_subtotal','Taxable Subtotal (Tax=T Rows)','Levy basis',money('145.20')),
   field('tax_amount','Sales Tax (7.50% on Taxable Subtotal)','Local levy at 7.50%',money('10.89')),
   field('invoice_total','CURRENT INVOICE TOTAL','This bill total',money('156.09')),
   field('amount_due','TOTAL AMOUNT DUE','Balance to remit',money('156.09'))],
  'absence':{'field_id':'customer_po_code','control_label':'Customer PO / CapEx Code','vocabulary_label':'Buyer purchase reference'},
  'tax_rate':'0.0750',
  'table':{'table_id':'line_items','row_key_column':'row_id',
   'columns':['row_id','sku','description','qty_unit','unit_price','discount_rate','line_discount','tax_flag','net_line'],
   'headers':['Row','SKU / Ref','Description','Qty','Unit Price','Disc%','Disc Amt','Tax','Net Line'],
   'vocabulary_headers':['Seq','Item ref','Service / item','Units','Rate','Rebate%','Rebate','Levy','Extended'],
   'widths':[30,60,140,50,56,42,54,28,72],
   'rows':[
    {'row_id':'K17','cells':{'row_id':ident('K17'),'sku':ident('00068547'),'description':val('Actuator bracket'),
     'qty_unit':val('4.00 EA','decimal_2','4.00',quantity_unit='EA'),'unit_price':money('11.75'),
     'discount_rate':pct('0.00'),'line_discount':money('0.00'),'tax_flag':ident('T'),'net_line':money('47.00')}},
    {'row_id':'K18','cells':{'row_id':ident('K18'),'sku':ident('00090632'),'description':val('Control linkage service'),
     'qty_unit':val('1.25 HR','decimal_2','1.25',quantity_unit='HR'),'unit_price':money('68.40'),
     'discount_rate':pct('0.00'),'line_discount':money('0.00'),'tax_flag':ident('T'),'net_line':money('85.50')}},
    {'row_id':'K19','cells':{'row_id':ident('K19'),'sku':ident('00027458'),'description':val('Retainer hardware kit'),
     'qty_unit':val('2.00 KT','decimal_2','2.00',quantity_unit='KT'),'unit_price':money('6.35'),
     'discount_rate':pct('0.00'),'line_discount':money('0.00'),'tax_flag':ident('T'),'net_line':money('12.70')}}]}},
 {'family_id':'WP11-F03','doc_kind':'inspection_service_checklist','title':'Water service inspection checklist',
  'subtitle':'Fictional Silver Badger training facilities',
  'fields':[
   field('work_order_id','Ticket Number','Inspection record',ident('CK-0007516')),
   field('property_unit','Property / Unit','Inspection place',val('Fictional Silver Badger / Room 009')),
   field('requested_date','Requested Date','Check day',date('2026-03-26')),
   field('assigned_tech','Assigned Technician','Examiner assigned',val('Fictional Iris Moth')),
   field('equipment_asset_tag','Water Heater Asset Tag','Equipment reference',ident('WH-0002841')),
   field('water_isolated','Branch Isolation Tested','Isolation verified',val('[X]','boolean_mark','true'))],
  'absence':{'field_id':'secondary_vendor_po','control_label':'Secondary Vendor PO','vocabulary_label':'Outside order reference'},
  'table':{'table_id':'turnover_tasks','row_key_column':'task_code',
   'columns':['task_code','fixture_area','action_taken','pressure_psi'],
   'headers':['Task Code','Fixture / Area','Action Performed','Test PSI'],
   'vocabulary_headers':['Check ref','Inspection zone','Observed work','Gauge PSI'],
   'widths':[80,126,242,84],
   'rows':[{'row_id':'I-A','cells':{'task_code':ident('T-071'),'fixture_area':val('Cold feed'),
              'action_taken':val('Static gauge reading recorded'),'pressure_psi':dec('58.00')}},
           {'row_id':'I-B','cells':{'task_code':ident('T-072'),'fixture_area':val('Branch outlet'),
              'action_taken':val('Valve reopened; gauge steady'),'pressure_psi':dec('57.50')}}]}}
]

def native_box(box):
    x,y,x2,y2=box
    return [round(x/WIDTH*1000),round((HEIGHT-y2)/HEIGHT*1000),round(x2/WIDTH*1000),round((HEIGHT-y)/HEIGHT*1000)]
def render(pdf):
    doc=pdfium.PdfDocument(pdf);page=doc[0];bitmap=page.render(scale=300.0/72.0)
    im=bitmap.to_pil().convert('RGB');bitmap.close();page.close();doc.close()
    if im.size!=(2550,3301):raise AssertionError('Canonical raster dimension mismatch')
    return im
def degrade(im):
    return im.convert('L').resize((850,1100),Image.Resampling.BOX).resize((2550,3301),Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(.5)).point([round(40+.8*x) for x in range(256)]).convert('RGB')

class Form:
    def __init__(self,source,condition):
        self.source=source;self.condition=condition;self.fid=source['family_id']+'-'+condition+'-v0'
        self.canvas=pw.PdfPageCanvas(WIDTH,HEIGHT);self.runs=[];self.blocks=[]
        self.expected={'schema_version':'1.0.0','fixture_id':self.fid,'family_id':source['family_id'],
         'doc_kind':source['doc_kind'],'split':'diagnostic_eval','variant_kind':condition,'page_count':1,
         'parent_fixture_id':None if condition=='control' else source['family_id']+'-control-v0',
         'expected_fields':[],'expected_tables':[],'expected_absences':[],
         'expected_adjacent_page_pairs':[],'page_sentinels':[],'cross_page_links':[]}
        self.annotations={'schema':'eld-coverage-annotations/1','fixture_id':self.fid,'family_id':source['family_id'],
         'condition':condition,'control_fixture_id':source['family_id']+'-control-v0','page_count':1,
         'fields':[],'tables':[],'absences':[],'ideal_native':''}
    def text(self,text,x,y,size=10,bold=False,role='furniture',limit=532,block=True):
        box=list(self.canvas.draw_text(text,x,y,'bold' if bold else 'regular',size_pt=size,max_width_pt=limit))
        self.runs.append({'text':text,'x':x,'y':y,'size_pt':size,'font':'bold' if bold else 'regular',
          'bbox_pt':box,'role':role,'ordinal':len(self.runs),'source':'canonical_vector_operator'})
        if block:self.blocks.append({'kind':'footer' if role=='footer' else 'text','bbox_pt':box,'body':text})
        return box
    def field(self,f,i):
        layout=self.condition=='layout';x=40+280*(i%2) if layout else 40
        y=480-60*(i//2) if layout else 670-28*i
        vx=x if layout else 330;vy=y-18 if layout else y
        label=f['vocabulary_label'] if self.condition=='vocabulary' else f['control_label']
        self.text(label,x,y,8,True,'field_label',252 if layout else 280,False)
        vbox=self.text(f['printed_text'],vx,vy,10,False,'field_value',252 if layout else 242,False)
        lbox=[x,y,x+(252 if layout else 280),y+8]
        valuebox=[vx,vy,vx+(252 if layout else 242),vy+10]
        self.blocks.extend([{'kind':'text','bbox_pt':lbox,'body':label},{'kind':'text','bbox_pt':valuebox,'body':f['printed_text']}])
        item={k:f[k] for k in ('printed_text','normalized_value','value_type')}
        self.expected['expected_fields'].append({'field_id':f['field_id'],'page_number':1,'label_printed':label,**item,'bbox_pt':vbox})
        self.annotations['fields'].append({'field_id':f['field_id'],'page_number':1,'label_printed':label,
                    'label_bbox_pt':lbox,'value_bbox_pt':valuebox})
    def table(self):
        spec=self.source['table'];heads=spec['vocabulary_headers'] if self.condition=='vocabulary' else spec['headers']
        top=650 if self.condition=='layout' else 350;y=top;x=40
        self.canvas.rect_fill_stroke(40,y-8,532,23,fill_rgb=(.92,.94,.96))
        for h,w in zip(heads,spec['widths']):self.text(h,x+3,y,7.2,True,'table_header',w-6,False);x+=w
        rows=[];body='<table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in heads)+'</tr>'
        for row in spec['rows']:
            y-=36;x=40;cells={};body+='<tr>'
            for col,w in zip(spec['columns'],spec['widths']):
                item=row['cells'][col];box=self.text(item['printed_text'],x+3,y,7.8,False,'table_cell',w-6,False)
                cells[col]={**item,'bbox_pt':box};body+='<td>'+html.escape(item['printed_text'])+'</td>';x+=w
            self.canvas.line(40,y-10,572,y-10,stroke_rgb=(.72,.77,.80))
            rows.append({'row_id':row['row_id'],'page_number':1,'cells':cells});body+='</tr>'
        body+='</table>'
        self.blocks.append({'kind':'table','bbox_pt':[40,y-10,572,top+15],'body':body})
        self.expected['expected_tables'].append({'table_id':spec['table_id'],'page_numbers':[1],
            'repeated_header_pages':[],'column_ids':spec['columns'],'rows':rows})
        self.annotations['tables'].append({'table_id':spec['table_id'],'page_number':1,'headers':heads,
            'column_ids':spec['columns'],'row_key_column':spec['row_key_column'],'header_bbox_pt':[40,top-8,572,top+15]})
    def absence(self):
        item=self.source['absence'];label=item['vocabulary_label'] if self.condition=='vocabulary' else item['control_label']
        self.text(label,40,145,8,True,'absence_label',280,False)
        bbox=[40,145,320,153];self.blocks.append({'kind':'text','bbox_pt':bbox,'body':label})
        self.canvas.rect_fill_stroke(330,139,242,22,fill_rgb=(1,1,1))
        self.expected['expected_absences'].append({'field_id':item['field_id'],'page_number':1,
            'label_printed':label,'expected_state':'absent_blank','bbox_pt':[330,139,572,161]})
        self.annotations['absences'].append({'field_id':item['field_id'],'page_number':1,'label_printed':label,'label_bbox_pt':bbox})
    def compose(self):
        self.text(self.source['title'],40,746,19,True)
        self.text(self.source['subtitle'],40,724,10)
        self.canvas.line(40,707,572,707,line_width=1.1)
        for i,f in enumerate(self.source['fields']):self.field(f,i)
        self.table();self.absence()
        self.text('SYNTHETIC TRAINING DOCUMENT - all names and records are fictional.',40,35,8,role='footer')
        self.text('One-page practice record; no real work or safety certification is asserted.',40,22,7,role='footer')
        ordered=sorted(self.runs,key=lambda r:(-r['y'],r['x'],r['ordinal']))
        reference={'pages':['\n'.join(r['text'] for r in ordered)],'runs':[ordered],
           'coverage':{'status':'complete_canonical_visible_text','ordering':'page; baseline y descending; x ascending; source operator ties',
            'includes':'all labels, values, table headers/cells, titles and fictional notices',
            'reference_role':'canonical intended transcription, not observed OCR',
            'bbox_convention':'points, bottom-left origin; annotations use fixed printed label/value regions, runs retain ink extents',
            'page_size_pt':[WIDTH,HEIGHT],'line_wrapping':False}}
        blocks=sorted(self.blocks,key=lambda b:(native_box(b['bbox_pt'])[1],native_box(b['bbox_pt'])[0]))
        self.annotations['ideal_native']='<PAGE>\n'+'\n'.join('<BLOCK>'+b['kind']+'['+','.join(map(str,native_box(b['bbox_pt'])))+']<FORK>'+b['body'] for b in blocks)
        return pw.serialize_pdf([self.canvas],title=self.fid),reference

def write_fixture(out,form,pdf,reference,ops,extra=None):
    fid=form.fid
    target=out/'pdfs'/f'{fid}.pdf';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(pdf)
    dump(out/'expected'/f'{fid}.json',form.expected)
    dump(out/'reference'/f'{fid}.json',reference)
    dump(out/'annotations'/f'{fid}.json',form.annotations)
    dump(out/'operators'/f'{fid}.json',{'fixture_id':fid,'page_size_pt':[WIDTH,HEIGHT],'pages':[ops],**(extra or {})})

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.relative_to(ROOT)
    if out.exists():raise FileExistsError('Refusing to overwrite '+str(out))
    out.mkdir(parents=True);fixtures=[]
    for source in FAMILIES:
        family=source['family_id'];dump(out/'sources'/f'{family}.json',source)
        control=None
        for condition in ('control','layout','vocabulary'):
            form=Form(source,condition);pdf,reference=form.compose()
            write_fixture(out,form,pdf,reference,form.canvas.ops)
            fixtures.append({'fixture_id':form.fid,'family_id':family,'condition':condition,'page_count':1})
            if condition=='control':control=(form,pdf,reference)
        parent,parent_pdf,parent_ref=control
        canonical=render(parent_pdf);transformed=degrade(canonical)
        (out/'rasters').mkdir(exist_ok=True)
        canonical.save(out/'rasters'/f'{family}-control-canonical.png')
        transformed.save(out/'rasters'/f'{family}-degraded-target.png')
        degraded=copy.deepcopy(parent);degraded.condition='degraded';degraded.fid=family+'-degraded-v0'
        degraded.expected.update(fixture_id=degraded.fid,variant_kind='degraded',parent_fixture_id=parent.fid)
        degraded.annotations.update(fixture_id=degraded.fid,condition='degraded')
        image_canvas=pw.PdfPageCanvas(WIDTH,HEIGHT)
        image_canvas.draw_image_rgb(transformed.tobytes(),*transformed.size,0,0,WIDTH,HEIGHT)
        pdf=pw.serialize_pdf([image_canvas],title=degraded.fid)
        actual=render(pdf)
        if actual.tobytes()!=transformed.tobytes():raise AssertionError('Raster container changed degradation pixels')
        reference=copy.deepcopy(parent_ref)
        reference['coverage'].update(reference_role='same-family control canonical transcription for degraded pixels; not PDF text or OCR',
             canonical_parent_fixture_id=parent.fid,canonical_parent_pdf_sha256=sha(parent_pdf),recipe=RECIPE,
             control_model_input_pixel_sha256=sha(canonical.tobytes()),degraded_target_pixel_sha256=sha(transformed.tobytes()),
             degraded_model_input_pixel_sha256=sha(actual.tobytes()),final_render_exact_target=True)
        write_fixture(out,degraded,pdf,reference,image_canvas.ops,{'canonical_text_operator_parent':parent.fid,'raster_recipe':RECIPE})
        fixtures.append({'fixture_id':degraded.fid,'family_id':family,'condition':'degraded','page_count':1})
    files=[{'path':str(p.relative_to(out)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(out.rglob('*')) if p.is_file()]
    dump(out/'manifest.json',{'schema':'eld-wp11-sealed-corpus/1','families':3,'documents':12,'pages':12,
       'conditions':list(CONDITIONS),'fixtures':fixtures,'files':files,'degradation_recipe':RECIPE,
       'independence':'three independent content families, four matched conditions each; not twelve independent samples',
       'canonical_fact_contract':'field IDs/values/types, table IDs/row keys/cell values/types/units and absence meanings identical within family',
       'condition_contract':{'control':'known frozen labels/header signatures; ideal-native support proof required',
         'layout':'arrangement only; fixed wording, multiplicity and typography',
         'vocabulary':'field/absence labels and table headers only; positions/fonts/regions/line counts fixed',
         'degraded':'single fixed recipe on control canonical input raster; target and final input pixels identical'},
       'model_execution':False})
    print(json.dumps({'status':'generated','families':3,'documents':12,'pages':12,'files':len(files)+1}))

if __name__=='__main__':main()
