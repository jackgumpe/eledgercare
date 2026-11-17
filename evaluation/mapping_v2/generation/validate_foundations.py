"""Validate frozen private foundations; never render, run mappers or read OCR outputs."""
from __future__ import annotations
import argparse,datetime,hashlib,json,subprocess,sys,traceback
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=Path('C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-custodian')
AUTHORITY='47fbc7612e4a08cf1960ad7ac01bd2843ae645e5'

def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
def sha(data):return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok:raise AssertionError(message)
def load(path):return json.loads((ROOT/path).read_bytes())
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write((json.dumps(value,indent=2)+'\n').encode())
def rect_ok(box):return len(box)==4 and 0<=box[0]<box[2]<=612 and 0<=box[1]<box[3]<=792.24
def overlaps(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])

def check(receipt,candidate):
    require(ROOT.resolve()==Path('C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/sealed').resolve(),'wrong private root')
    require(git(ROOT,'branch','--show-current').decode().strip()=='sealed/wp-0013','wrong private branch')
    require(not git(ROOT,'remote').strip(),'private remote is forbidden')
    require(git(ROOT,'rev-parse','HEAD').decode().strip()==candidate,'candidate is not current exact HEAD')
    require(not git(ROOT,'diff','--name-only').strip() and not git(ROOT,'diff','--cached','--name-only').strip(),'tracked source changes')
    require(git(ROOT,'show',candidate+':generation/validate_foundations.py')==Path(__file__).read_bytes(),'validator differs from freeze')
    families=load('foundations/r1/families.json')['families'];templates=load('foundations/r1/templates.json')['templates'];plan=load('foundations/r1/case-plan.json')
    ids=[f'WP13-F0{i}' for i in range(1,5)]
    require([f['family_id'] for f in families]==ids==[t['family_id'] for t in templates],'four distinct family order')
    require([f['profile'] for f in families]==['work_order','service_invoice','inspection','work_order'],'profile allocation')
    expected_cases={family+'-'+case+'-v0' for family in ids for case in ('supported','conflict','unsupported')}
    require(len(plan['cases'])==12 and {c['fixture_id'] for c in plan['cases']}==expected_cases,'twelve reserved cases')
    require(all(c['page_count']==1 and c['final_policy_pending'] for c in plan['cases']),'one-page pending cases')
    require(plan['final_catalog_commit'] is None and plan['independent_catalog_acceptance'] is None and plan['final_rendered_bytes_released'] is False,'catalog gate silently passed')
    require(plan['fixed_sentinel']=='WP13-F04-conflict-v0','fixed sentinel changed')
    require(not list(ROOT.rglob('*.pdf')),'foundation-only phase contains rendered PDF')
    receipt['checks'].append('four fresh foundation identities; twelve planned one-page cases; catalog/rendering gates pending')

    old_paths=[p for p in git(PUBLIC,'ls-tree','-r','--name-only',AUTHORITY,'evaluation').decode().splitlines() if '/expected/' in p and p.endswith('.json')]
    old_texts=[];old_ids=set();vocab={}
    for p in old_paths:
        data=git(PUBLIC,'show',AUTHORITY+':'+p);old_texts.append(data.decode())
        obj=json.loads(data);kind=obj.get('doc_kind');entry=vocab.setdefault(kind,{'fields':set(),'absences':set(),'tables':{}})
        entry['fields'].update(x['field_id'] for x in obj.get('expected_fields',[]));entry['absences'].update(x['field_id'] for x in obj.get('expected_absences',[]))
        for t in obj.get('expected_tables',[]):entry['tables'][t['table_id']]=t['column_ids']
        def walk(value):
            if isinstance(value,dict):
                if value.get('value_type')=='identifier' and isinstance(value.get('printed_text'),str):old_ids.add(value['printed_text'])
                for child in value.values():walk(child)
            elif isinstance(value,list):
                for child in value:walk(child)
        walk(obj)
    historical='\n'.join(old_texts);fresh_ids=[];typed_count=0
    for f in families:
        source=vocab[f['doc_kind']]
        require(len({x['field_id'] for x in f['fields']})==len(f['fields']),'duplicate foundation field identity')
        require({x['field_id'] for x in f['fields']}<=source['fields'],'new unsupported semantic field')
        require(f['absence']['field_id'] in source['absences'] and f['absence']['expected_state']=='absent_blank','absence convention drift')
        table=f['table'];require(table['columns']==source['tables'][table['table_id']],'table column vocabulary drift')
        require(table['row_key_column'] in table['columns'],'row key missing')
        require(len({r['row_id'] for r in table['rows']})==len(table['rows']),'duplicate row identities')
        items=[(x['field_id'],x) for x in f['fields']]
        for row in table['rows']:
            require(set(row['cells'])==set(table['columns']),'missing source cell')
            items.extend(row['cells'].items())
        items.append((f['reserved_conflict']['field_id'],f['reserved_conflict']['alternate_value']))
        original=next(x for x in f['fields'] if x['field_id']==f['reserved_conflict']['field_id'])
        require(original['normalized_value']!=f['reserved_conflict']['alternate_value']['normalized_value'],'conflict values not distinct')
        require(f['reserved_conflict']['truth_if_both_printed']=='ambiguous','conflict truth fabricated')
        for key,item in items:
            typed_count+=1;typ=item['value_type'];raw=item['printed_text'];normal=item['normalized_value']
            require(isinstance(raw,str) and isinstance(normal,str) and raw,'typed values must be explicit strings')
            if 'quantity_unit' in item:require(isinstance(item['quantity_unit'],str) and bool(item['quantity_unit']),'empty quantity unit')
            if typ=='date_iso':datetime.date.fromisoformat(raw);require(raw==normal,'date normalization drift')
            elif typ=='identifier':
                require(raw==normal,'identifier normalization drift')
                if key!='tax_flag':fresh_ids.append(raw);require(raw not in old_ids,'historical identifier reused: '+raw)
            elif typ=='decimal_2':
                require(Decimal(normal).as_tuple().exponent==-2,'decimal precision')
                require(raw==(normal+' '+item['quantity_unit'] if 'quantity_unit' in item else normal),'quantity representation')
            elif typ=='currency_usd':require(raw=='$'+normal and Decimal(normal).as_tuple().exponent==-2,'currency representation')
            elif typ=='rate_percent':require(Decimal(raw.rstrip('%'))/100==Decimal(normal),'rate representation')
            elif typ=='boolean_mark':require((raw,normal) in (('[X]','true'),('[ ]','false')),'boolean convention')
            elif typ=='text':require(raw==normal,'text normalization drift')
            else:raise AssertionError('unsupported type '+typ)
            if raw.startswith('Fictional '):require(raw not in historical,'historical fictional name reused')
    require(len(fresh_ids)==len(set(fresh_ids)),'fresh identifier repeated across independent source slots')
    receipt['checks'].append('canonical field/table/absence vocabulary and typed-value/unit conventions; fresh identifiers and fictional names')
    invoice=families[1];fields={x['field_id']:x for x in invoice['fields']};total=Decimal('0')
    for row in invoice['table']['rows']:
        c=row['cells'];net=Decimal(c['qty_unit']['normalized_value'])*Decimal(c['unit_price']['normalized_value'])-Decimal(c['line_discount']['normalized_value'])
        require(net==Decimal(c['net_line']['normalized_value']),'invoice row arithmetic');total+=net
    tax=(total*Decimal(invoice['tax_rate'])).quantize(Decimal('.01'))
    require(total==Decimal(fields['subtotal']['normalized_value'])==Decimal(fields['taxable_subtotal']['normalized_value']),'invoice subtotal')
    require(tax==Decimal(fields['tax_amount']['normalized_value']),'invoice tax')
    require(total+tax==Decimal(fields['invoice_total']['normalized_value'])==Decimal(fields['amount_due']['normalized_value']),'invoice total')
    receipt['checks'].append('invoice row multiplication, subtotal, tax and amount due exact decimal arithmetic')

    for f,t in zip(families,templates):
        require(t['page_size_pt']==[612.0,792.24],'template page size')
        require([x['field_id'] for x in t['fields']]==[x['field_id'] for x in f['fields']],'field template identity/order')
        boxes=[]
        for slot in t['fields']:boxes.extend([slot['label_region'],slot['value_region']])
        boxes.extend([t['table']['region'],t['absence']['label_region'],t['absence']['blank_region'],t['conflict_reserve_region']])
        require(all(rect_ok(b) for b in boxes),'template region outside page')
        require(not any(overlaps(a,b) for i,a in enumerate(boxes) for b in boxes[i+1:]),'foundation template regions overlap')
        require(sum(t['table']['column_widths_pt'])==532 and len(t['table']['column_widths_pt'])==len(f['table']['columns']),'table column geometry')
        require(t['absence']['field_id']==f['absence']['field_id'],'absence template identity')
    receipt['checks'].append('four fixed independent template arrangements; all reserved regions within page and nonoverlapping')
    pins=load('provenance/source-pins.json');writer=(ROOT/'generation/pdf_writer.py').read_bytes();wp=pins['reused_generic_writer']
    require(writer==git(PUBLIC,'show',AUTHORITY+':'+wp['public_path']) and sha(writer)==wp['sha256'] and len(writer)==wp['bytes'],'generic writer byte provenance')
    receipt['checks'].append('generic deterministic writer exact exposed provenance; no rendering or historical data copy')
    receipt.update({'authority_commit':AUTHORITY,'candidate_commit':candidate,'families':4,'planned_cases':12,'final_rendered_cases':0,'source_typed_items_checked':typed_count,'historical_expected_files_checked':len(old_paths),'private_no_remote':True,'semantic_acceptance':False,'catalog_acceptance_pending':True})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',required=True);parser.add_argument('--run-id',required=True);parser.add_argument('--inventory',action='store_true');a=parser.parse_args()
    require(a.run_id.replace('-','').isalnum(),'invalid run ID');out=ROOT/'evidence'/a.run_id/'receipt.json';require(not out.parent.exists(),'retain previous attempt');out.parent.mkdir(parents=True)
    receipt={'schema':'eld-wp13-foundation-verification/1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'checks':[],'status':'running','rendering':False,'mapper_execution':False,'model_inference':False}
    try:
        check(receipt,a.candidate)
        if a.inventory:
            paths=git(ROOT,'ls-tree','-r','--name-only',a.candidate).decode().splitlines();files=[]
            for path in paths:
                data=git(ROOT,'show',a.candidate+':'+path);require(data==(ROOT/path).read_bytes(),'working/Git mismatch')
                files.append({'path':path,'bytes':len(data),'sha256':sha(data),'git_blob':git(ROOT,'rev-parse',a.candidate+':'+path).decode().strip()})
            inv={'schema':'eld-wp13-foundation-inventory/1','source_commit':a.candidate,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'files':files,'exclusions':['this inventory','this inventory execution receipt'],'status':'foundation_only_catalog_pending'}
            ip=ROOT/'inventory/foundations-r1.json';write(ip,inv);receipt['inventory_sha256']=sha(ip.read_bytes());receipt['checks'].append('complete committed foundation inventory and working-byte parity')
        receipt['status']='passed'
    except Exception:receipt['status']='failed';receipt['failure']=traceback.format_exc()
    finally:
        receipt['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();write(out,receipt)
        print(json.dumps({'status':receipt['status'],'checks':len(receipt['checks']),'receipt':str(out)}))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
