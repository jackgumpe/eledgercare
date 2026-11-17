"""Public schema-only contract, matched semantics and ideal control support checks."""
import math
from .common import norm,mapping,paired

CONDITIONS=('control','layout','vocabulary','degraded')
FAMILIES=('WP11-F01','WP11-F02','WP11-F03')

def require(value,message):
    if not value:raise ValueError(message)

def box(value):
    return (isinstance(value,list) and len(value)==4 and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in value)
            and value[0]<value[2] and value[1]<value[3])

def unit_metadata(value):
    require('quantity_unit' not in value or (isinstance(value['quantity_unit'],str) and bool(value['quantity_unit'])),'Explicit quantity_unit must be nonempty string')

def unit_signature(value):return ('quantity_unit' in value,value.get('quantity_unit'))

def validate(expected,reference,annotations):
    a=annotations;e=expected
    require(a['schema']=='eld-coverage-annotations/1','Annotation schema')
    require(a['family_id'] in FAMILIES and a['condition'] in CONDITIONS,'Finite family/condition')
    require(a['fixture_id']==a['family_id']+'-'+a['condition']+'-v0','Fixture ID')
    require(a['control_fixture_id']==a['family_id']+'-control-v0','Paired clean control')
    require(a['page_count']==e['page_count']==1,'Exactly one page')
    require(e['fixture_id']==a['fixture_id'] and e['family_id']==a['family_id'],'Expected identity')
    require(e['split']=='diagnostic_eval' and e['variant_kind']==a['condition'],'Expected metadata')
    require(isinstance(reference['pages'],list) and len(reference['pages'])==1 and isinstance(reference['pages'][0],str) and isinstance(reference['coverage'],dict),'Reference schema')
    for key in ('expected_fields','expected_tables','expected_absences','page_sentinels','expected_adjacent_page_pairs','cross_page_links'):
        require(isinstance(e[key],list),'Expected list '+key)
    require(not e['expected_adjacent_page_pairs'] and not e['cross_page_links'],'One-page link scope')
    require(isinstance(a['ideal_native'],str) and a['ideal_native'],'Ideal native support witness')
    for key in ('fields','tables','absences'):require(isinstance(a[key],list),'Annotation list '+key)
    fs={(f['page_number'],f['field_id']):f for f in e['expected_fields']}
    af={(f['page_number'],f['field_id']):f for f in a['fields']}
    require(len(fs)==len(e['expected_fields']) and len(af)==len(a['fields']) and fs.keys()==af.keys(),'Unique complete field annotations')
    for key,f in fs.items():
        unit_metadata(f)
        require(key[0]==1 and isinstance(f['printed_text'],str) and f['printed_text']!='' and isinstance(f['normalized_value'],str) and isinstance(f['value_type'],str),'Field metadata')
        require(isinstance(f['label_printed'],str) and f['label_printed']==af[key]['label_printed'],'Exact field label')
        require(box(af[key]['label_bbox_pt']) and box(af[key]['value_bbox_pt']),'Field boxes')
    absences={(f['page_number'],f['field_id']):f for f in e['expected_absences']}
    aa={(f['page_number'],f['field_id']):f for f in a['absences']}
    require(len(absences)==len(e['expected_absences']) and len(aa)==len(a['absences']) and absences.keys()==aa.keys() and not fs.keys()&absences.keys(),'Unique complete absence slots')
    for key,f in aa.items():
        require(key[0]==1 and isinstance(f['label_printed'],str) and box(f['label_bbox_pt']),'Absence annotation')
        require(absences[key].get('expected_state')=='absent_blank','Explicit absent_blank semantics required')
        require(absences[key].get('label_printed')==f['label_printed'],'Expected/annotation absence label mismatch')
    tables={t['table_id']:t for t in e['expected_tables']};at={t['table_id']:t for t in a['tables']}
    require(len(tables)==len(e['expected_tables']) and len(at)==len(a['tables']) and tables.keys()==at.keys(),'Unique complete tables')
    for tid,t in tables.items():
        x=at[tid];cols=x['column_ids']
        require(x['page_number']==1 and isinstance(cols,list) and cols and len(set(cols))==len(cols) and all(isinstance(v,str) for v in cols),'Table columns')
        require(isinstance(x['headers'],list) and len(x['headers'])==len(cols) and all(isinstance(v,str) and v for v in x['headers']),'Header sequence')
        require(set(t['column_ids'])==set(cols) and x['row_key_column'] in cols and box(x['header_bbox_pt']),'Header/row-key metadata')
        require(isinstance(t['rows'],list) and len({r['row_id'] for r in t['rows']})==len(t['rows']),'Unique row IDs')
        keys=[]
        for row in t['rows']:
            require(row['page_number']==1 and set(row['cells'])==set(cols),'Complete row columns')
            for cell in row['cells'].values():
                require(all(isinstance(cell[k],str) for k in ('printed_text','normalized_value','value_type')),'Cell metadata');unit_metadata(cell)
            keys.append(norm(row['cells'][x['row_key_column']]['printed_text']))
        require(all(keys) and len(set(keys))==len(keys),'Unique nonempty expected row-key values')
    return e,reference,a

def semantic_signature(e):
    fields=sorted((f['field_id'],f['page_number'],f['printed_text'],f['normalized_value'],f['value_type'],unit_signature(f)) for f in e['expected_fields'])
    cells=sorted((t['table_id'],r['row_id'],r['page_number'],col,c['printed_text'],c['normalized_value'],c['value_type'],unit_signature(c)) for t in e['expected_tables'] for r in t['rows'] for col,c in r['cells'].items())
    absent=sorted((f['field_id'],f['page_number'],f.get('expected_state')) for f in e['expected_absences'])
    return {'fields':fields,'cells':cells,'absences':absent,'page_count':e['page_count']}

def validate_family(records):
    require(len(records)==4 and {r[2]['condition'] for r in records}==set(CONDITIONS),'Four conditions required')
    for row in records:validate(*row)
    require(len({r[2]['family_id'] for r in records})==1,'One family')
    signatures=[semantic_signature(r[0]) for r in records]
    require(all(s==signatures[0] for s in signatures),'Paired semantic slots/values/types/absence meanings changed')
    control=next(r for r in records if r[2]['condition']=='control')
    degraded=next(r for r in records if r[2]['condition']=='degraded')
    require(degraded[1]['pages']==control[1]['pages'],'Degraded reference must match its control')
    for key in ('fields','tables','absences','ideal_native'):
        require(degraded[2][key]==control[2][key],'Degraded condition changes more than scan quality: '+key)
    return True

def support_control(expected,reference,annotations,rules=None):
    validate(expected,reference,annotations);require(annotations['condition']=='control','Control witness required')
    rules=mapping() if rules is None else rules
    label_rules={x['label']:x['field_id'] for x in rules['labels']}
    for f in annotations['fields']+annotations['absences']:
        require(label_rules.get(norm(f['label_printed']).rstrip(':'))==f['field_id'],'Control exact label unsupported')
    for table in annotations['tables']:
        require(any(t['table_id']==table['table_id'] and t['headers']==table['headers'] and t['columns']==table['column_ids'] for t in rules['tables']),'Control exact header/column sequence unsupported')
    witness=paired(annotations['ideal_native'],expected,reference,'completed',rules)
    for name,score in witness['scores'].items():
        require(score['eligible_for_exact_credit'],name+' control parse ineligible')
        for metric in ('fields','cells','rows','expected_absences','page_count'):
            require(score[metric]['correct']==score[metric]['total'],name+' unsupported control witness '+metric)
        require(not score['fields']['unmatched_candidates'] and not score['cells']['extra_rows'] and not score['cells']['extra_cells'],name+' surplus control mapping')
    return {'status':'supported_by_both_frozen_mappers','scores':witness['scores'],
            'limit':'Ideal perfect-reading witness only; independent visible-layout fidelity admission required; no actual OCR success implied.'}
