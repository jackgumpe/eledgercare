"""Ground-truth comparison only; prediction extraction lives in native.py."""
from collections import defaultdict
from difflib import SequenceMatcher
from native import norm
from typed_values import compare

def counts(correct,total,**extra):
    return {'correct':correct,'total':total,'rate':correct/total if total else None,**extra}

def token_errors(reference,prediction):
    a=norm(reference).split();b=norm(prediction).split()
    if max(len(a),len(b))>12000:return {'status':'unsupported_token_limit','reference_tokens':len(a),'prediction_tokens':len(b),'error_rate':None}
    sub=delete=insert=0
    for tag,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if tag=='replace':sub+=min(j-i,l-k);delete+=max(0,(j-i)-(l-k));insert+=max(0,(l-k)-(j-i))
        elif tag=='delete':delete+=j-i
        elif tag=='insert':insert+=l-k
    return {'status':'scored','reference_tokens':len(a),'prediction_tokens':len(b),'substitutions':sub,'deletions':delete,'insertions':insert,
            'error_rate':(sub+delete+insert)/len(a) if a else None,'alignment':'SequenceMatcher-autojunk=False; not minimum Levenshtein WER'}

def score_document(pred,expected,reference,completion='completed'):
    eligible=completion=='completed' and not pred['parse_errors']
    fields=defaultdict(list)
    for f in pred['fields']:fields[f['page'],f['field_id']].append(f)
    used=set();details=[];typed_fields=[];typed_cells=[];fc=0
    for f in expected['expected_fields']:
        key=f['page_number'],f['field_id'];items=fields[key];index=sum(1 for d in details if d['key']==list(key))
        got=items[index] if index<len(items) else None
        if got:used.add(id(got))
        exact=got is not None and norm(got['value'])==norm(f['printed_text']);fc+=int(exact and eligible)
        details.append({'key':list(key),'expected_printed':f['printed_text'],'expected_normalized':f['normalized_value'],
                        'predicted':None if got is None else got['value'],'observed_exact':exact,'credited_exact':exact and eligible,
                        'status':'missing' if got is None else 'exact' if exact else 'different'})
        typed_fields.append({'key':list(key),**compare(None if got is None else got['value'],f,eligible,f['field_id'])})
    absence=[]
    for f in expected['expected_absences']:
        items=fields[f['page_number'],f['field_id']]
        if items:used.add(id(items[0]))
        values=[x['value'] for x in items if norm(x['value'])]
        absence.append({'field_id':f['field_id'],'page':f['page_number'],'values':values,'violation':bool(values),'candidate_count':len(items),'surplus_candidates':max(0,len(items)-1),'verified_absent':eligible and bool(items) and not values,'unmapped':not bool(items)})
    predicted_tables=defaultdict(list)
    for t in pred['tables']:
        for r in t['rows']:predicted_tables[t['page'],t['table_id']].append((t['columns'],r['values'],r.get('physical_values',r['values']),r.get('mapping_status','mapped')))
    expected_keys=set();cell_details=[];row_details=[];cc=ct=missing_rows=extra_rows=extra_cells=0
    for t in expected['expected_tables']:
        page_rows=defaultdict(list)
        for r in t['rows']:page_rows[r['page_number']].append(r)
        for page,rows in page_rows.items():
            key=page,t['table_id'];expected_keys.add(key);actual=predicted_tables[key]
            for i,row in enumerate(rows):
                cols,values,physical,mapping=actual[i] if i<len(actual) else ([],[],[],'missing')
                missing_rows+=int(i>=len(actual) or mapping=='unsupported_spanning_row');row_exact=True
                for column,cell in row['cells'].items():
                    value=values[cols.index(column)] if column in cols and cols.index(column)<len(values) else None
                    exact=value is not None and norm(value)==norm(cell['printed_text']);ct+=1;cc+=int(exact and eligible);row_exact &= exact
                    cell_details.append({'table':t['table_id'],'page':page,'row_ordinal':i,'row_id':row['row_id'],'column':column,
                                         'expected_printed':cell['printed_text'],'predicted':value,'observed_exact':exact,'credited_exact':exact and eligible})
                    typed_cells.append({'table':t['table_id'],'page':page,'row_ordinal':i,'row_id':row['row_id'],'column':column,**compare(value,cell,eligible,column)})
                extra_cells+=max(0,len(physical)-len(row['cells']))
                row_details.append({'table':t['table_id'],'page':page,'row_ordinal':i,'exact':row_exact and eligible})
            extra_rows+=max(0,len(actual)-len(rows))
            extra_cells+=sum(len(physical) for _,_,physical,_ in actual[len(rows):])
    for key,rows in predicted_tables.items():
        if key not in expected_keys:extra_rows+=len(rows);extra_cells+=sum(len(physical) for _,_,physical,_ in rows)
    page_text=['\n'.join(b['text'] for b in p['blocks']) for p in pred['pages']]
    tokens=token_errors('\n'.join(reference['pages']), '\n'.join(page_text))
    anchors=pred['anchors'];sentinels=[]
    for s in expected['page_sentinels']:
        candidates=[a for a in anchors if a['page']==s['page_number']]
        ok=len(candidates)==1 and candidates[0]['value']==s['sentinel_id'] and eligible
        sentinels.append({'page':s['page_number'],'expected':s['sentinel_id'],'predicted':[a['value'] for a in candidates],'correct':ok})
    adjacency=[]
    for pair in expected['expected_adjacent_page_pairs']:
        # Preserve the schema shape; undefined structures are unsupported, never dropped.
        if isinstance(pair,list) and len(pair)==2:
            flags={s['page']:s['correct'] for s in sentinels};ok=bool(flags.get(pair[0]) and flags.get(pair[1]) and pair[1]==pair[0]+1)
        else:ok=False
        adjacency.append({'expected':pair,'correct':ok})
    links=[]
    for link in expected['cross_page_links']:
        kind=link['link_type'];ok=False;supported=True
        if kind in {'repeated_document_id','repeated_contract_id'}:
            fid='invoice_number' if kind=='repeated_document_id' else 'contract_id'
            ok=all(any(norm(x['value'])==norm(link['value']) for x in fields[p,fid]) for p in link['pages'])
        elif kind=='table_continuation':
            a=predicted_tables[link['from_page'],link['table_id']];b=predicted_tables[link['to_page'],link['table_id']]
            def rowid(row):
                cols,vals,_,_=row
                return vals[cols.index('row_id')] if 'row_id' in cols and len(vals)>cols.index('row_id') else None
            ok=bool(a and b and rowid(a[-1])==link['from_last_row'] and rowid(b[0])==link['to_first_row'])
        elif kind=='final_page_only_summary':
            totals={'subtotal','taxable_subtotal','tax_amount','invoice_total','amount_due'}
            ok=any(f['field_id'] in totals and f['page']==link['summary_page'] for f in pred['fields']) and not any(f['field_id'] in totals and f['page'] in link['excluded_pages'] for f in pred['fields'])
        else:supported=False
        links.append({'link_id':link['link_id'],'supported':supported,'correct':bool(ok and eligible)})
    return {'schema':'eld-baseline-score/1','fixture_id':expected['fixture_id'],'family_id':expected['family_id'],'split':expected['split'],'variant_kind':expected['variant_kind'],
      'completion':completion,'eligible_for_exact_credit':eligible,'document_denominator':1,'completed_documents':int(completion=='completed'),'parse_errors':pred['parse_errors'],
      'fields':counts(fc,len(details),missing=sum(x['status']=='missing' for x in details),unmatched_candidates=sum(id(f) not in used for f in pred['fields']),details=details),
      'cells':counts(cc,ct,extra_rows=extra_rows,extra_cells=extra_cells,missing_rows=missing_rows,details=cell_details),
      'normalized_fields':typed_counts(typed_fields),
      'normalized_cells':typed_counts(typed_cells),
      'rows':counts(sum(r['exact'] for r in row_details),len(row_details),details=row_details),
      'expected_absences':counts(sum(a['verified_absent'] for a in absence),len(absence),violations=sum(a['violation'] for a in absence),surplus_candidates=sum(a['surplus_candidates'] for a in absence),details=absence),
      'page_count':counts(int(len(page_text)==expected['page_count'] and eligible),1,predicted=len(page_text),expected=expected['page_count']),
      'page_sentinels':counts(sum(s['correct'] for s in sentinels),len(sentinels),details=sentinels),
      'adjacency':counts(sum(s['correct'] for s in adjacency),len(adjacency),details=adjacency),
      'cross_page_links':counts(sum(s['correct'] for s in links),len(links),details=links),
      'text':tokens,'reference_coverage':reference['coverage'],'unmapped_content':pred['unmapped'],
      'mapping_coverage':{'fields_with_candidate':sum(d['predicted'] is not None for d in details),'expected_fields':len(details),
        'cells_with_candidate':sum(d['predicted'] is not None for d in cell_details),'expected_cells':ct,
        'unsupported_or_missing_table_rows':missing_rows,'unclassified_content_records':len(pred['unmapped']),
        'unmapped_table_physical_rows':sum(x['kind'] in ('unmapped_table_row','unsupported_spanning_row') for x in pred['unmapped']),
        'unmapped_table_physical_cells':sum(len(x['values']) for x in pred['unmapped'] if x['kind'] in ('unmapped_table_row','unsupported_spanning_row')),
        'short_table_rows':sum(x['kind']=='short_table_row' for x in pred['unmapped']),
        'failure_reasons':(['no_exact_dev_header_or_missing_table_rows'] if missing_rows else [])+(['missing_field_candidates'] if any(d['predicted'] is None for d in details) else [])+(['unsupported_spanning_rows'] if any(x['kind']=='unsupported_spanning_row' for x in pred['unmapped']) else [])+(['short_table_rows'] if any(x['kind']=='short_table_row' for x in pred['unmapped']) else [])+(['native_parse_error'] if pred['parse_errors'] else []),
        'interpretation':'Field/cell mismatches combine extraction/mapping and recognition errors. Unmapped cells are not asserted character-reading errors; raw token errors are reported separately.'},
      'invention_limit':'Unmatched fields/rows/cells and absence violations are schema-relative signals; unrecognized prose is retained, not asserted factual hallucination.'}

def typed_counts(details):
    reasons=defaultdict(int)
    for d in details:
        if d['status']!='parsed':reasons[d['status']]+=1
        if d['reference_status']!='supported':reasons[d['reference_status']]+=1
        if d['status']=='parsed' and d['reference_status']=='supported' and not d['observed_exact']:reasons['different_normalized_value']+=1
        if d['observed_exact'] and not d['credited_exact']:reasons['document_ineligible']+=1
    return counts(sum(d['credited_exact'] for d in details),len(details),parsed_candidates=sum(d['status']=='parsed' for d in details),
                  uncredited_reasons=dict(reasons),details=details,
                  interpretation='Strict typed normalized-value accuracy; printed accuracy, mapping failures and excess accounting remain separate. Quantity units are validated but normalized quantity compares only the number.')

def summarize(scores):
    """Equal document weight within family, then equal family weight; splits never pooled."""
    out={}
    for split in sorted({s['split'] for s in scores}):
        items=[s for s in scores if s['split']==split];family={}
        for fam in sorted({s['family_id'] for s in items}):
            fs=[s for s in items if s['family_id']==fam];metrics={}
            for metric in ['fields','cells','normalized_fields','normalized_cells','rows','expected_absences','page_count','page_sentinels','adjacency','cross_page_links']:
                values=[s[metric]['rate'] for s in fs if s[metric]['rate'] is not None]
                metrics[metric]={'mean':sum(values)/len(values) if values else None,'documents_with_denominator':len(values)}
            values=[s['text']['error_rate'] for s in fs if s['text']['error_rate'] is not None]
            metrics['text_error_rate']={'mean':sum(values)/len(values) if values else None,'documents_with_denominator':len(values)}
            family[fam]={'documents':len(fs),'completed':sum(s['completed_documents'] for s in fs),'metrics':metrics}
        macro={}
        for metric in next(iter(family.values()))['metrics']:
            vals=[f['metrics'][metric]['mean'] for f in family.values() if f['metrics'][metric]['mean'] is not None]
            macro[metric]={'mean':sum(vals)/len(vals) if vals else None,'families_with_denominator':len(vals)}
        variants={}
        for v in sorted({s['variant_kind'] for s in items}):
            group=[s for s in items if s['variant_kind']==v];vm={}
            for metric in macro:
                family_means=[]
                for fam in sorted({s['family_id'] for s in group}):
                    values=[(s['text']['error_rate'] if metric=='text_error_rate' else s[metric]['rate']) for s in group if s['family_id']==fam]
                    values=[x for x in values if x is not None]
                    if values:family_means.append(sum(values)/len(values))
                vm[metric]={'mean':sum(family_means)/len(family_means) if family_means else None,'families_with_denominator':len(family_means)}
            variants[v]={'documents':len(group),'completed':sum(s['completed_documents'] for s in group),'family_macro':vm}
        out[split]={'document_denominator':len(items),'completed_documents':sum(s['completed_documents'] for s in items),'families':family,'family_macro':macro,'variants':variants}
    return out
