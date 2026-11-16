"""WP-0009 independent synthetic families. CPU-only; no external input/network.

The semantic source below is authored for this packet, not derived from B0 records.
Only generic PDF serialization and canonical expected-slot names are reused.
Output directory must not exist. Each run writes complete operator and text records.
"""
from __future__ import annotations
import argparse, hashlib, json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import pdf_writer as writer

ROOT = Path(__file__).resolve().parents[1]
writer.FIXED_PDF_DATE = 'D:20261116000000Z'
writer.PRODUCER_TAG = 'eLedgerCare WP-0009 sealed synthetic generator 1'

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True)+'\n').encode('utf-8'))

def sha(data): return hashlib.sha256(data).hexdigest()

def value(printed, typ='text', normalized=None, **extra):
    return {'printed_text': printed, 'normalized_value': printed if normalized is None else normalized,
            'value_type':typ, **extra}

def money(s): return value('$'+s, 'currency_usd', s)
def ident(s): return value(s, 'identifier')
def date(s): return value(s, 'date_iso')
def decimal(s): return value(s, 'decimal_2')
def mark(flag): return value('[X]' if flag else '[ ]', 'boolean_mark', 'true' if flag else 'false')

# Source records are deliberately literal. No mapper, prediction or alias data is read.
RECORDS = [
 {'family_id':'WP09-F01','fixture_id':'WP09-F01-v0','doc_kind':'work_order','page_count':1,
  'fields': {
   'work_order_id':ident('RPR-0006382'),'property_name':value('Fictional Juniper Kite Court'),
   'building_unit':ident('West studio 003B'),'requested_date':date('2026-08-21'),
   'trade_category':value('Hardware / access'),'assigned_tech':value('Fictional Tessa Quill'),
   'reported_issue_and_resolution':value('Latch rubbed strike; reset plate and verified free swing.'),
   'completion_status':value('Finished - access restored'),'supervisor_signoff':value('Fictional Noel Reed')},
  'absences':['resident_contact'],
  'rows':[{'row_id':'P71','part_sku':ident('0019476'),'part_desc':value('Strike shim, zinc'),
           'bin_loc':ident('D-003'),'qty_used':decimal('2.00')},
          {'row_id':'P72','part_sku':ident('0005368'),'part_desc':value('M4 countersunk screw'),
           'bin_loc':ident('D-017'),'qty_used':decimal('4.00')}]},
 {'family_id':'WP09-F02','fixture_id':'WP09-F02-v0','doc_kind':'inspection_checklist','page_count':1,
  'fields': {'work_order_id':ident('CK-0002809'),'property_unit':value('Fictional Lantern Vale / Hall 02'),
   'inspection_date':date('2026-09-06'),'inspector_id':ident('INS-00053'),
   'overall_result':value('Return visit required'),'chief_engineer_ack':value('Fictional Arlo Finch')},
  'absences':['requisition_id'],
  'rows':[
   {'row_id':'C31','item_id':ident('031'),'check_desc':value('Closer sweep'),'location':value('East leaf'),
    'pass_mark':mark(True),'fail_mark':mark(False),'na_mark':mark(False),'reading_notes':value('7 seconds')},
   {'row_id':'C32','item_id':ident('032'),'check_desc':value('Latch engagement'),'location':value('West leaf'),
    'pass_mark':mark(False),'fail_mark':mark(True),'na_mark':mark(False),'reading_notes':value('Misses strike')},
   {'row_id':'C33','item_id':ident('033'),'check_desc':value('Vision panel seal'),'location':value('Both leaves'),
    'pass_mark':mark(True),'fail_mark':mark(False),'na_mark':mark(False),'reading_notes':value('Intact')},
   {'row_id':'C34','item_id':ident('034'),'check_desc':value('Powered hold-open'),'location':value('Door pair'),
    'pass_mark':mark(False),'fail_mark':mark(False),'na_mark':mark(True),'reading_notes':value('Not fitted')}]},
 {'family_id':'WP09-F03','fixture_id':'WP09-F03-v0','doc_kind':'supplier_invoice','page_count':1,
  'fields':{'invoice_number':ident('BILL-0009274'),'customer_acct_id':ident('00018403'),
   'invoice_date':date('2026-07-13'),'due_date':date('2026-08-12'),
   'address_bill_to':value('Fictional Moss Bell / 17 Imaginary Lane, ZZ 00000'),
   'address_service_location':value('Fictional Moss Bell / Pump alcove 004'),
   'subtotal':money('89.00'),'tax_amount':money('4.90'),'invoice_total':money('93.90'),
   'amount_due':money('93.90')},'absences':['work_order_ref'],
  'tax_rate':'0.0550',
  'rows':[
   {'row_id':'Q41','sku':ident('0004782'),'description':value('Float switch bracket'),
    'qty_unit':value('2.00 EA','decimal_2','2.00',quantity_unit='EA'),
    'unit_price':money('18.40'),'net_line':money('36.80')},
   {'row_id':'Q42','sku':ident('0006921'),'description':value('Drain tube section'),
    'qty_unit':value('4.00 EA','decimal_2','4.00',quantity_unit='EA'),
    'unit_price':money('6.30'),'net_line':money('25.20')},
   {'row_id':'Q43','sku':ident('0008159'),'description':value('Bench leak check'),
    'qty_unit':value('0.75 HR','decimal_2','0.75',quantity_unit='HR'),
    'unit_price':money('36.00'),'net_line':money('27.00')}]},
 {'family_id':'WP09-F04','fixture_id':'WP09-F04-v0','doc_kind':'multi_page_service_record','page_count':3,
  'fields':{'packet_id':ident('SR-0007462'),'contract_id':ident('AGR-000592'),
   'property_name':value('Fictional Pebble Comet Annex'),
   'affected_units':value('Platform lift L-007 / landing 02'),
   'crew_lead':value('Fictional Mira Dove'),'completion_status':value('Returned to service'),
   'completed_timestamp':value('2026-06-18 14:05'),
   'lead_tech_signoff':value('Fictional Mira Dove')},'absences':['supervisor_signoff'],
  'labor':[
   {'row_id':'V61','page':1,'log_id':ident('V61'),'tech_id':ident('00642'),
    'work_date':date('2026-06-17'),'time_in':value('08:10'),
    'time_out':value('08:55'),'hours':decimal('0.75'),'activity':value('Inspect guide rollers')},
   {'row_id':'V62','page':1,'log_id':ident('V62'),'tech_id':ident('00642'),
    'work_date':date('2026-06-17'),'time_in':value('09:05'),
    'time_out':value('09:35'),'hours':decimal('0.50'),'activity':value('Measure landing gap')},
   {'row_id':'V63','page':2,'log_id':ident('V63'),'tech_id':ident('00642'),
    'work_date':date('2026-06-18'),'time_in':value('11:20'),
    'time_out':value('12:20'),'hours':decimal('1.00'),'activity':value('Renew roller sleeves')},
   {'row_id':'V64','page':2,'log_id':ident('V64'),'tech_id':ident('00816'),
    'work_date':date('2026-06-18'),'time_in':value('13:10'),
    'time_out':value('13:55'),'hours':decimal('0.75'),'activity':value('Cycle lift under load')}],
  'parts':[{'row_id':'U81','part_sku':ident('0007239'),'part_desc':value('Guide roller sleeve'),
            'bin_loc':ident('L-002'),'qty_used':decimal('3.00')},
           {'row_id':'U82','part_sku':ident('0003671'),'part_desc':value('Retaining ring'),
            'bin_loc':ident('L-019'),'qty_used':decimal('3.00')}]}
]

class Document:
    def __init__(self, spec):
        self.spec=spec; self.canvases=[]; self.runs=[]
        self.expected={'schema_version':'1.0.0','fixture_id':spec['fixture_id'],'family_id':spec['family_id'],
          'doc_kind':spec['doc_kind'],'split':'fresh_eval','split_disclosure':'procedurally_blinded_to_mapping_author_until_accepted_freeze',
          'variant_kind':'v0_clean','parent_fixture_id':None,'page_count':spec['page_count'],
          'expected_adjacent_page_pairs':[],'page_sentinels':[],'cross_page_links':[],
          'expected_fields':[],'expected_absences':[],'expected_tables':[],
          'expected_routing_for_e3':'eligible_digital_text_layer',
          'transform_params':{'renderer':'retained generic PDF 1.4 writer','dpi':None,'rotation_deg':0.0}}
    def page(self):
        self.canvases.append(writer.PdfPageCanvas());self.runs.append([])
        self.c=self.canvases[-1]; self.p=len(self.canvases)
    def text(self,s,x,y,size=9,bold=False,role='furniture',limit=540):
        bbox=self.c.draw_text(s,x,y,'bold' if bold else 'regular',size_pt=size,max_width_pt=limit)
        self.runs[-1].append({'text':s,'x':x,'y':y,'size_pt':size,'bbox_pt':list(bbox),
                            'ordinal':len(self.runs[-1])+1,'role':role,'source':'vector_operator'})
        return list(bbox)
    def field(self,key,label,x,y,vx=195,size=10,above=False):
        item=self.spec['fields'][key]
        self.text(label,x,y,8,True,role='field_label')
        bbox=self.text(item['printed_text'],x if above else vx,y-17 if above else y,size,
                       role='field_value',limit=570-(x if above else vx))
        self.expected['expected_fields'].append({'field_id':key,'label_printed':label,
           'page_number':self.p,**item,'bbox_pt':bbox})
    def absence(self,key,label,x,y,width=170):
        self.text(label,x,y,8,True,role='absence_label')
        self.c.rect_fill_stroke(x,y-29,width,20,fill_rgb=(1,1,1))
        self.expected['expected_absences'].append({'field_id':key,'label_printed':label,
            'page_number':self.p,'expected_state':'absent_blank','bbox_pt':[x,y-29,x+width,y-9],
            'semantics':'A printed empty response box; no asserted value, not an unknown filled value.'})
    def table(self,tid,columns,rows,y,row_height=32,size=8):
        # columns: (canonical slot, fresh printed heading, width)
        x=40; width=sum(c[2] for c in columns)
        self.c.rect_fill_stroke(x,y-8,width,23,fill_rgb=(0.91,0.94,0.95))
        for key,label,w in columns:
            self.text(label,x+4,y,7.3,True,role='table_header',limit=w-8);x+=w
        table=next((t for t in self.expected['expected_tables'] if t['table_id']==tid),None)
        if table is None:
            table={'table_id':tid,'page_numbers':[],'repeated_header_pages':[],
                   'column_ids':[c[0] for c in columns],'rows':[]};self.expected['expected_tables'].append(table)
        else: table['repeated_header_pages'].append(self.p)
        table['page_numbers'].append(self.p)
        for row in rows:
            y-=row_height;x=40; cells={}
            for key,label,w in columns:
                item=ident(row['row_id']) if key=='row_id' else row[key]
                bbox=self.text(item['printed_text'],x+4,y,size,role='table_cell',limit=w-8)
                cells[key]={**item,'bbox_pt':bbox};x+=w
            self.c.line(40,y-9,40+width,y-9,stroke_rgb=(0.75,0.79,0.81))
            table['rows'].append({'row_id':row['row_id'],'page_number':self.p,'cells':cells})
        return y
    def footer(self,tag):
        self.text('SYNTHETIC TRAINING DOCUMENT - all people, sites and contact details are fictional.',40,35,7)
        self.text(tag,40,22,7)
    def write(self,out):
        fid=self.spec['fixture_id']
        pdf=writer.serialize_pdf(self.canvases,title=fid+' synthetic evaluation original')
        p=out/'pdfs'/f'{fid}.pdf';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(pdf)
        dump(out/'expected'/f'{fid}.json',self.expected)
        ordered=[sorted(r,key=lambda q:(-q['y'],q['x'],q['ordinal'])) for r in self.runs]
        ref={'fixture_id':fid,'pages':['\n'.join(x['text'] for x in r) for r in ordered], 'runs':ordered,
             'coverage':{'status':'complete_all_visible_text_operators','ordering':'page; baseline y descending; x ascending; operator ordinal for ties',
              'includes':['titles','all labels','all filled values','table headers and cells','fictional notices','page markers'],
              'excludes':['nontext lines and boxes'],'text_layer_only':True,'handwriting':False,'raster_text':False}}
        dump(out/'reference'/f'{fid}.json',ref)
        dump(out/'operators'/f'{fid}.json',{'fixture_id':fid,'pages':[{'page_number':i+1,'operators':c.ops} for i,c in enumerate(self.canvases)]})
        dump(out/'sources'/f'{fid}.json',self.spec)

PARTS=[('part_sku','Stock code',100),('part_desc','Material issued',240),('bin_loc','Shelf',90),('qty_used','Count',102)]
LABOR=[('log_id','Entry',39),('tech_id','Crew no.',51),('work_date','Visit date',76),('time_in','Start',46),
       ('time_out','Finish',46),('hours','Hours',43),('activity','Service performed',231)]

def compose(spec):
    d=Document(spec); d.page(); family=spec['family_id']
    if family=='WP09-F01':
        d.c.rect_fill_stroke(30,700,552,62,fill_rgb=(0.91,0.95,0.96))
        d.text('REPAIR AUTHORITY',42,737,22,True)
        d.text('Fictional Juniper Kite maintenance desk',42,716,10)
        d.field('work_order_id','Request key',40,672,above=True)
        d.field('requested_date','Opened on',370,672,above=True)
        d.field('property_name','Premises',40,600)
        d.field('building_unit','Work spot',40,570)
        d.field('trade_category','Craft needed',40,540)
        d.field('assigned_tech','Assigned to',40,510)
        d.text('REPAIR RECORD',40,464,11,True)
        d.field('reported_issue_and_resolution','Concern and action',40,440,above=True,size=9)
        d.text('Items taken from stores',40,373,10,True)
        d.table('stock_parts',PARTS,spec['rows'],348)
        d.field('completion_status','Closeout',40,232)
        d.field('supervisor_signoff','Duty lead',40,202)
        d.absence('resident_contact','Resident callback (left empty)',40,150,250)
        d.footer('Training form JKC-R / 1 of 1')
    elif family=='WP09-F02':
        d.text('DOOR PAIR WALKDOWN',40,742,21,True)
        d.text('Fictional Lantern Vale safety workshop',40,722,10)
        d.c.line(40,703,572,703,line_width=2)
        d.field('property_unit','Inspection place',40,678,above=True)
        d.field('work_order_id','Check record',40,620,above=True)
        d.field('inspection_date','Visit day',245,620,above=True)
        d.field('inspector_id','Examiner code',440,620,above=True)
        d.text('Choose one outcome per checkpoint; comments describe the observation.',40,560,9)
        cols=[('item_id','No.',32),('check_desc','Checkpoint',135),('location','Position',83),
              ('pass_mark','OK',34),('fail_mark','Fix',34),('na_mark','N/A',34),('reading_notes','Observation',180)]
        d.table('safety_checklist',cols,spec['rows'],525,row_height=47,size=8.4)
        d.field('overall_result','Disposition',40,275)
        d.field('chief_engineer_ack','Responsible engineer',40,240)
        d.absence('requisition_id','Parts request number (if issued)',40,188,250)
        d.text('No powered hold-open is installed on this fictional door set.',40,100,9)
        d.footer('Training checklist LV-D / 1 of 1')
    elif family=='WP09-F03':
        d.text('COPPER KITE SUPPLY',40,744,22,True)
        d.text('Fictional supplier - training transactions only',40,722,9)
        d.text('81 Make-Believe Way, Example Borough, ZZ 00000',40,705,9)
        d.text('service@copper-kite.example / 202-555-0146',40,688,9)
        d.field('invoice_number','Billing note',40,646,above=True)
        d.field('customer_acct_id','Ledger account',350,646,above=True)
        d.field('invoice_date','Issued',40,585,above=True)
        d.field('due_date','Settle by',350,585,above=True)
        d.field('address_bill_to','Charge to',40,526,above=True,size=9)
        d.field('address_service_location','Delivery point',40,477,above=True,size=9)
        cols=[('row_id','Row',38),('sku','Product',66),('qty_unit','Supplied',70),
              ('description','Goods / work',198),('unit_price','Each',75),('net_line','Extended',85)]
        d.table('line_items',cols,spec['rows'],414,row_height=35,size=8.5)
        d.absence('work_order_ref','Buyer job reference (not supplied)',40,248,230)
        d.field('subtotal','Goods and work',320,262,vx=490)
        d.text('Tax applies to every row at 5.50%.',320,234,8)
        d.field('tax_amount','Sales levy',320,209,vx=490)
        d.field('invoice_total','Bill total',320,181,vx=490)
        d.field('amount_due','Balance to remit',320,150,vx=490)
        d.text('No discounts, additional fees, prior balance or payments apply.',40,100,9)
        d.footer('Fictional transaction CK-S / 1 of 1')
    else:
        for pn in range(1,4):
            if pn>1:d.page()
            d.c.rect_fill_stroke(30,714,552,53,fill_rgb=(0.96,0.93,0.88))
            d.text('LIFT SERVICE JOURNAL',42,742,21,True)
            d.text(('Initial visit','Follow-up visit','Return to service')[pn-1],42,723,10)
            d.field('packet_id','Journal key',40,680,above=True)
            d.field('contract_id','Service agreement',350,680,above=True)
            d.field('property_name','Site',40,612)
            if pn==1:
                d.field('affected_units','Equipment covered',40,574)
                d.field('crew_lead','Visit lead',40,538)
                d.text('Initial finding: guide roller sleeves were worn; landing clearance recorded.',40,485,9)
                d.table('labor_log',LABOR,[r for r in spec['labor'] if r['page']==1],437,row_height=45,size=7.8)
                d.text('Next visit: renew sleeves and complete loaded travel checks.',40,280,10)
            elif pn==2:
                d.text('Follow-up finding: replacement sleeves seated and lift travel checked.',40,548,10)
                d.table('labor_log',LABOR,[r for r in spec['labor'] if r['page']==2],485,row_height=45,size=7.8)
                d.text('Observed result: both landing stops aligned; no rubbing during travel.',40,326,10)
                d.text('Materials and return decision are recorded on the final sheet.',40,290,10)
            else:
                d.text('Materials used during the follow-up visit',40,550,11,True)
                d.table('stock_parts',PARTS,spec['parts'],515,row_height=40,size=9)
                d.field('completion_status','Return decision',40,362)
                d.field('completed_timestamp','Closed at (local)',40,327)
                d.field('lead_tech_signoff','Technician attestation',40,292)
                d.absence('supervisor_signoff','Second witness (left empty)',40,224,250)
                d.text('Fictional equipment record. This sheet makes no real safety certification.',40,133,9)
            sentinel=f'LCJ-26-{pn}'
            d.text(f'Sheet {pn} / 3   |   {sentinel}',40,80,10,True)
            d.expected['page_sentinels'].append({'page_number':pn,'page_label':f'Sheet {pn} / 3',
                 'sentinel_id':sentinel,'repeated_contract_id':spec['fields']['contract_id']['printed_text']})
            d.footer('Training journal PCA-L / fictional record')
        d.expected['expected_adjacent_page_pairs']=[[1,2],[2,3]]
        d.expected['cross_page_links']=[{'link_id':'WP09-F04-agreement','link_type':'repeated_contract_id',
             'value':spec['fields']['contract_id']['printed_text'],'pages':[1,2,3]}]
    return d

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);args=ap.parse_args()
    out=args.out.resolve(); out.relative_to(ROOT)
    if out.exists():raise FileExistsError('Refusing to overwrite existing generation: '+str(out))
    out.mkdir(parents=True)
    for spec in RECORDS:compose(spec).write(out)
    files=[{'path':str(p.relative_to(out)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
           for p in sorted(out.rglob('*')) if p.is_file()]
    dump(out/'manifest.json',{'schema':'eld-wp09-sealed-corpus/1','families':4,'pdfs':4,'pages':6,
      'fixtures':[{'fixture_id':x['fixture_id'],'family_id':x['family_id'],'page_count':x['page_count'],
                   'doc_kind':x['doc_kind']} for x in RECORDS], 'files':files,
      'coverage':{'clean_vector_only':True,'new_semantic_families':4,'variants':0,
        'expected_schema':'B0 1.0.0 canonical slots; additive bbox and quantity_unit metadata',
        'scored_semantics':'Only existing canonical fields, table slots, types, absence and link structures.',
        'unsupported_or_untested':['raster','skew','handwriting','photos','customer data','population representativeness'],
        'quantity_units':'Explicitly retained in printed text and separate metadata; B0 normalized quantity scores number only.',
        'absence':'Only explicitly printed empty response boxes; unprinted optional fields are outside the denominator.'}})
    print(json.dumps({'status':'generated','pdfs':4,'pages':6,'files':len(files)+1}))

if __name__=='__main__':main()
