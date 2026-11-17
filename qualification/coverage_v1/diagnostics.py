"""Reference-side stage evidence. Never changes or supplies answers to either mapper."""
from collections import Counter
from html.parser import HTMLParser
import re
from .common import norm,sha,mapping,paired
from .contract import validate,semantic_signature,CONDITIONS,FAMILIES

def surface(value):return ' '.join(norm(value).split())

class Visible(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)

def visible_units(prediction):
    units=[]
    for page in prediction['pages']:
        for bi,block in enumerate(page['blocks']):
            if block['rows']:
                for ri,row in enumerate(block['rows']):
                    for ci,cell in enumerate(row):
                        units.append({'page':page['page'],'block':bi,'row':ri,'cell':ci,'text':surface(cell['text'])})
            elif block['kind']!='unparsed':
                visible=Visible();visible.feed(block['text']);visible.close()
                units.append({'page':page['page'],'block':bi,'text':surface(''.join(visible.parts))})
    return units

def presence(target,page,units,eligible):
    if not eligible:return {'status':'unavailable','count':None,'locations':[]}
    target=surface(target)
    if not target:return {'status':'empty_target_unscored','count':None,'locations':[]}
    pattern=re.compile(r'(?<!\w)'+re.escape(target)+r'(?!\w)');hits=[]
    for unit in units:
        if unit['page']!=page:continue
        for match in pattern.finditer(unit['text']):
            hits.append({k:v for k,v in unit.items() if k!='text'}|{'span':list(match.span()),'quote':unit['text'][max(0,match.start()-40):match.end()+40],
                'visible_leaf_sha256':sha(unit['text'].encode())})
    return {'status':'none' if not hits else 'one' if len(hits)==1 else 'multiple','count':len(hits),'locations':hits}

def native_rows(prediction,page):
    return [(bi,ri,row) for p in prediction['pages'] if p['page']==page for bi,b in enumerate(p['blocks']) for ri,row in enumerate(b['rows'])]

def row_binding(prediction,annotation,row,eligible):
    if not eligible or annotation is None:return {'status':'unavailable','locations':[]}
    index=annotation['column_ids'].index(annotation['row_key_column']);target=norm(row['cells'][annotation['row_key_column']]['printed_text']);hits=[]
    for bi,ri,cells in native_rows(prediction,row['page_number']):
        if len(cells)==len(annotation['column_ids']) and all(c['colspan']==c['rowspan']==1 for c in cells) and norm(cells[index]['text'])==target:
            hits.append({'page':row['page_number'],'block':bi,'row':ri,'cells':cells})
    return {'status':'none' if not hits else 'one' if len(hits)==1 else 'multiple','locations':hits}

def unit_agreement(expected,predicted,slot):
    if slot!='qty_unit':return {'status':'not_applicable'}
    def suffix(value):
        if not isinstance(value,str):return None
        found=re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?\s+([A-Za-z0-9/%^_-]+)',surface(value))
        return found[1] if found else None
    target=suffix(expected);observed=suffix(predicted)
    return {'status':'unavailable' if target is None or observed is None else 'exact' if target==observed else 'different',
        'expected_printed_unit':target,'predicted_printed_unit':observed,'limit':'Separate literal-unit evidence; historical typed numeric credit is unchanged.'}

def diagnose(raw,expected,reference,completion='completed',annotations=None,precomputed=None):
    if annotations is not None:validate(expected,reference,annotations)
    pair=paired(raw or '',expected,reference,completion) if precomputed is None else precomputed
    pred=pair['predictions']['b0'];eligible=raw is not None and completion=='completed' and not pred['parse_errors']
    units=visible_units(pred) if eligible else [];rules=mapping()
    labels={x['label']:x['field_id'] for x in rules['labels']}
    ta={x['table_id']:x for x in annotations['tables']} if annotations else {}
    slots=[]
    for i,field in enumerate(expected['expected_fields']):
        label=field.get('label_printed');support=None if label is None else labels.get(norm(label).rstrip(':'))==field['field_id']
        slots.append({'kind':'field','expected_pointer':f'/expected_fields/{i}','page':field['page_number'],'slot':field['field_id'],
            'metadata':field,'label_or_header_support':support,'label_presence':None if label is None else presence(norm(label).rstrip(':'),field['page_number'],units,eligible),
            'ordinal':i,'local_binding':{'status':'not_asserted_by_presence'}})
    ci=0
    for ti,table in enumerate(expected['expected_tables']):
        annotation=ta.get(table['table_id']);support=None
        if annotation is not None:support=any(t['table_id']==table['table_id'] and t['headers']==annotation['headers'] and t['columns']==annotation['column_ids'] for t in rules['tables'])
        for ri,row in enumerate(table['rows']):
            binding=row_binding(pred,annotation,row,eligible)
            header_hits=[]
            if eligible and annotation:
                header_hits=[{'page':row['page_number'],'block':b,'row':r} for b,r,cells in native_rows(pred,row['page_number'])
                    if [c['text'] for c in cells]==annotation['headers'] and all(c['colspan']==c['rowspan']==1 for c in cells)]
            for column,cell in row['cells'].items():
                local=None
                if binding['status']=='one':
                    match=binding['locations'][0];index=annotation['column_ids'].index(column)
                    local={'page':match['page'],'block':match['block'],'row':match['row'],'cell':index,'quote':match['cells'][index]['text'],
                           'observed_exact':norm(match['cells'][index]['text'])==norm(cell['printed_text'])}
                slots.append({'kind':'cell','expected_pointer':f'/expected_tables/{ti}/rows/{ri}/cells/{column}','page':row['page_number'],
                    'table_id':table['table_id'],'row_id':row['row_id'],'slot':column,'metadata':cell,'ordinal':ci,
                    'label_or_header_support':support,'label_presence':None,'header_locations':header_hits,
                    'local_binding':{'status':binding['status'],'row_candidates':len(binding['locations']),'cell':local}});ci+=1
    value_multiplicity=Counter((slot['page'],surface(slot['metadata']['printed_text'])) for slot in slots)
    records=[]
    for slot in slots:
        meta=slot['metadata'];value=presence(meta['printed_text'],slot['page'],units,eligible)
        reuse=value_multiplicity[slot['page'],surface(meta['printed_text'])]
        per_mapper={}
        for name in ('b0','mapping_v1'):
            score=pair['scores'][name];metric='fields' if slot['kind']=='field' else 'cells'
            printed=score[metric]['details'][slot['ordinal']];typed=score['normalized_'+metric]['details'][slot['ordinal']]
            causes=[]
            if not eligible:causes.append('unavailable_output_or_parse')
            else:
                present_label=(slot['label_presence'] or {}).get('count',0) or len(slot.get('header_locations',[]))
                if slot['label_or_header_support'] is False and present_label:causes.append('exact_visible_label_or_header_unsupported')
                if not printed['credited_exact']:
                    if value['count']==0:causes.append('exact_value_not_observed_recognition_omission_or_segmentation_ambiguous')
                    if reuse>1 or value['count']>1:causes.append('reused_value_or_multiple_occurrences_ambiguous')
                    local=slot['local_binding']
                    anchored=(slot['kind']=='field' and value['count']==1 and reuse==1 and (slot['label_presence'] or {}).get('count')==1)
                    anchored=anchored or (slot['kind']=='cell' and local['status']=='one' and local['cell']['observed_exact'])
                    if anchored:causes.append('mapped_slot_mismatch_despite_local_or_unique_exact_payload')
                    if not causes:causes.append('unadjudicated')
                if printed['credited_exact'] and not typed['credited_exact']:causes.append('typed_conversion_or_target_boundary')
            per_mapper[name]={'printed':printed,'typed':typed,'evidence_flags_nonexclusive':causes,
                'literal_unit':unit_agreement(meta['printed_text'],printed['predicted'],slot['slot']),
                'identifier_printed_exact':None if meta['value_type']!='identifier' else printed['observed_exact']}
        records.append({k:v for k,v in slot.items() if k not in ('metadata','ordinal')}|{'expected_printed':meta['printed_text'],
            'value_type':meta['value_type'],'expected_normalized':meta['normalized_value'],'expected_same_page_value_multiplicity':reuse,
            'value_presence':value,'mappers':per_mapper})
    counts=Counter(r['value_presence']['status'] for r in records)
    result={'schema':'eld-coverage-diagnostic/1','fixture_id':expected['fixture_id'],'family_id':expected['family_id'],
        'condition':None if annotations is None else annotations['condition'],'completion':completion,'raw_available':raw is not None,
        'raw_sha256':None if raw is None else sha(raw.encode()),'eligible_for_presence':eligible,'parse_errors':pred['parse_errors'],
        'slots':records,'presence_denominator':{'all_expected_slots':len(records),'eligible_slots':len(records) if eligible else 0,
            'unavailable_slots':0 if eligible else len(records),'statuses':dict(counts)},
        'historical_scores':pair['scores'],'prediction_summary':{name:{'field_candidates':len(p['fields']),'tables':len(p['tables']),
            'unmapped_records':len(p['unmapped'])} for name,p in pair['predictions'].items()},
        'semantic_signature':semantic_signature(expected),
        'interpretation':'Nonexclusive stage evidence, not exhaustive causal attribution. Exact text presence never itself proves correct semantic association.'}
    if annotations is not None:
        ideal=paired(annotations['ideal_native'],expected,reference,'completed')
        result['ideal_witness_scores']=ideal['scores']
        result['ideal_witness_limit']='Reference-only perfect-reading counterfactual; never supplied to actual predictions and not an observed OCR result.'
    return result

def paired_conditions(documents):
    expected_ids=[f'{f}-{c}-v0' for f in FAMILIES for c in CONDITIONS]
    if len(documents)!=12 or sorted(d['fixture_id'] for d in documents)!=sorted(expected_ids):raise ValueError('All twelve primary diagnostic rows required')
    pairs=[]
    for family in FAMILIES:
        group={d['condition']:d for d in documents if d['family_id']==family}
        if set(group)!=set(CONDITIONS):raise ValueError('Four matched conditions per family')
        control=group['control']
        for condition in CONDITIONS[1:]:
            other=group[condition]
            if other['semantic_signature']!=control['semantic_signature']:raise ValueError('Unmatched semantic contents')
            eligible=control['eligible_for_presence'] and other['eligible_for_presence']
            deltas={}
            for name in ('b0','mapping_v1'):
                deltas[name]={metric:other['historical_scores'][name][metric]['rate']-control['historical_scores'][name][metric]['rate']
                    if other['historical_scores'][name][metric]['rate'] is not None and control['historical_scores'][name][metric]['rate'] is not None else None
                    for metric in ('fields','cells','normalized_fields','normalized_cells','rows')}
            pairs.append({'family_id':family,'condition':condition,'control_fixture_id':control['fixture_id'],'fixture_id':other['fixture_id'],
                'presence_pair_eligible':eligible,'presence_pair_unavailable':not eligible,'historical_score_delta_including_failed_denominators':deltas,
                'presence_count_delta':None if not eligible else sum(s['value_presence']['count']>0 for s in other['slots'])-sum(s['value_presence']['count']>0 for s in control['slots'])})
    return {'primary_documents':12,'independent_families':3,'paired_comparisons':9,'eligible_presence_pairs':sum(p['presence_pair_eligible'] for p in pairs),
            'unavailable_presence_pairs':sum(p['presence_pair_unavailable'] for p in pairs),'pairs':pairs,
            'limit':'Each degraded result is paired with its own clean control. Twelve conditions are not twelve independent families.'}
