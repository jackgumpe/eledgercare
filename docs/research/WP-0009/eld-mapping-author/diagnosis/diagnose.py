"""WP-0009 finite saved-output audit. No prediction mutation or model imports.

Expected answers are used ONLY for diagnostic comparisons and row audit alignment.
This is not an alternative mapper, scorer, treatment, or selected implementation.
Run from the repository root with host Python -I -B; output stays in owned paths.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OWN = Path(__file__).resolve().parent
AUTHORITY = '22b88bc32d053231678aef88e6b7f76d3e61910a'
SOURCE = '522f15f1f6e399c36b9c6c107fc08f51862f1fc1'
EVIDENCE = Path('docs/evidence/WP-0007/eld-rd-astra')
RUNS = {'dev': EVIDENCE/'runtime-dev/20261116T051059Z-eda73dc6',
        'eval_holdout': EVIDENCE/'runtime-heldout/20261116T145728Z-07a28a6d',
        'supplement': EVIDENCE/'runtime-recovery/20261116T142841Z-284039ca'}
CATEGORIES = ['text_recognition_or_omission', 'native_parse_or_structure',
              'field_table_mapping', 'typed_conversion_or_scoring',
              'runtime_unavailable_output', 'ambiguous_unadjudicated']
METRICS = ['fields','cells','normalized_fields','normalized_cells','rows',
           'expected_absences','page_count','page_sentinels','adjacency','cross_page_links']
inputs = {}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def read(path):
    p = (ROOT/path).resolve()
    p.relative_to(ROOT)
    data = p.read_bytes()
    rel = p.relative_to(ROOT).as_posix()
    inputs[rel] = {'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                   'git_blob': git('hash-object', '--', rel)}
    return data


def load(path):
    return json.loads(read(path))


def source_identity():
    for name in ['corpus.py','native.py','score.py','typed_values.py','mapping.json','protocol.json']:
        path = 'qualification/baseline/'+name
        read(path)
        assert git('hash-object','--',path) == git('rev-parse',SOURCE+':'+path), path
    assert git('rev-parse','HEAD:qualification/baseline') == git('rev-parse',SOURCE+':qualification/baseline')


def locations(parsed):
    """Every text occurrence retains page/block/cell context, including unmapped text."""
    out=[]
    for page in parsed['pages']:
        for bi,b in enumerate(page['blocks']):
            if b['rows']:
                for ri,row in enumerate(b['rows']):
                    for ci,cell in enumerate(row):
                        out.append({'page':page['page'],'block':bi,'row':ri,'cell':ci,'quote':cell['text']})
            else:
                out.append({'page':page['page'],'block':bi,'quote':b['text']})
    return out


def diagnostic_bindings(fid):
    """Manually inspected finite table bindings, never supplied to extraction."""
    if fid.startswith('SYN-WO-03'):
        return [('safety_checklist',1,7 if '-v2-' in fid else 13,0)]
    if fid.startswith('SYN-MP-02'):
        return [('containment_checklist',1,7 if '-v2-' in fid else 11,0),
                ('equipment_deployment',2,7 if '-v2-' in fid else 4,0),
                ('equipment_deployment',3,7 if '-v2-' in fid else 4,0),
                ('equipment_retrieval',3,8 if '-v2-' in fid else 6,0)]
    if fid in ('SYN-MP-01-v0-clean','SYN-MP-01-v1-raster300'):
        return [('line_items',2,2,2),('line_items',3,2,2)]
    return []


def audit_document(original, run, fixture, mapping, supplemental=False):
    fid=fixture['fixture_id']; raw_path=run/'evidence'/(fid+'.measured.raw.txt')
    raw_available=(ROOT/raw_path).is_file()
    raw=read(raw_path).decode('utf-8') if raw_available else ''
    if raw_available:
        observation=load(run/'evidence'/(fid+'.measured.observation.json'))
        assert observation['raw_output']['sha256_written']==hashlib.sha256(raw.encode('utf-8')).hexdigest()
    parsed=parse_native(raw); pred=extract_prediction(parsed,mapping)
    expected=load(fixture['expected_ground_truth_path'])
    assert inputs[fixture['expected_ground_truth_path']]['sha256'] == fixture['expected_ground_truth_sha256']
    parent=next(f for f in fixtures if f['family_id']==fixture['family_id'] and f['variant_kind']=='v0_clean')
    read(parent['file_path'])
    if fixture['variant_kind']=='v3_hybrid':read(fixture['source_record_path'])
    reference=reference_for(fixture,allow_test=True)
    reproduced=score_document(pred,expected,reference,original['completion'])
    reproduced['raw_sha256']=hashlib.sha256(raw.encode('utf-8')).hexdigest()
    assert reproduced==original, 'Score mismatch: '+fid
    known={r['label']:r['field_id'] for r in mapping['labels']}
    locs=locations(parsed)
    # Raw offsets refer to decoded Unicode text (not byte offsets); native indices are zero-based.
    def evidence(loc, why):
        return {**loc,'raw_path':raw_path.as_posix(),'reason':why}
    def raw_quote(needle,why):
        offset=raw.find(needle)
        assert offset>=0,(fid,needle)
        return {'raw_path':raw_path.as_posix(),'character_offset':offset,
                'line':raw[:offset].count('\n')+1,'quote':needle,'reason':why}
    items=[]; adjacent=[]
    for kind,typed_kind in [('fields','normalized_fields'),('cells','normalized_cells')]:
        for ordinal,(detail,typed) in enumerate(zip(original[kind]['details'],original[typed_kind]['details'])):
            if kind=='fields':
                page,ident=detail['key'];item_id=f'field:p{page}:{ident}:{ordinal}'
            else:
                page=detail['page'];ident=detail['column'];item_id=f"cell:p{page}:{detail['table']}:{detail['row_id']}:{ident}"
            rec={'item_id':item_id,'kind':kind,'page':page,'expected':detail['expected_printed'],
                 'baseline_predicted':detail['predicted'],'printed_credit':detail['credited_exact'],
                 'typed_credit':typed['credited_exact'],'typed_status':typed['status'],
                 'categories':[],'evidence':[]}
            failed=not rec['printed_credit'] or not rec['typed_credit']
            if failed and not raw_available:
                rec['categories'].append('runtime_unavailable_output')
            elif failed and original['parse_errors']:
                rec['categories'].append('native_parse_or_structure')
            # Only full cell equality at an inspected row binding establishes this local cause.
            if kind=='cells' and raw_available:
                for table,pn,bi,header_row in diagnostic_bindings(fid):
                    if table!=detail['table'] or pn!=page:continue
                    block=parsed['pages'][pn-1]['blocks'][bi]
                    et=next(t for t in expected['expected_tables'] if t['table_id']==table)
                    er=next(r for r in et['rows'] if r['row_id']==detail['row_id'] and r['page_number']==pn)
                    first=et['column_ids'][0];key=er['cells'][first]['printed_text'];ci=et['column_ids'].index(ident)
                    matches=[(ri,r) for ri,r in enumerate(block['rows']) if r and r[0]['text']==key]
                    assert len(matches)<=1
                    if matches:
                        ri,row=matches[0]
                        assert len(row)>=len(et['column_ids']) and all(c['colspan']==1 for c in row)
                        actual=row[ci]['text']
                        if not detail['credited_exact']:
                            rec['categories'].append('field_table_mapping')
                            if actual!=detail['expected_printed']:rec['categories'].append('text_recognition_or_omission')
                            rec['evidence'].append(evidence({'page':pn,'block':bi,'row':ri,'cell':ci,'quote':actual,
                                  'header_quote':[c['text'] for c in block['rows'][header_row]]},
                                  'Inspected keyed native row/column; frozen mapper supplies no candidate. Equality is local, not whole-document reading accuracy.'))
                    elif table=='equipment_deployment' and pn==3:
                        assert len(block['rows'])==1 and key not in raw
                        rec['categories']+=['text_recognition_or_omission','field_table_mapping']
                        rec['evidence'].append(evidence({'page':pn,'block':bi,'row':0,
                            'quote':block['native_body'],'missing_expected_row_key':key},
                            'Native continuation contains header only; no deployment row E07/E08 anywhere in raw. Serial reappearance in retrieval is not the missing deployment record.'))
            if kind=='cells' and detail['predicted'] is not None and not detail['observed_exact']:
                # Source extraction is verbatim; the location is found in the baseline mapped row.
                table_rows=[(t,r) for t in pred['tables'] if t['page']==page and t['table_id']==detail['table'] for r in t['rows']]
                t,r=table_rows[detail['row_ordinal']];ci=t['columns'].index(ident)
                rec['categories'].append('text_recognition_or_omission')
                rec['evidence'].append(evidence({'page':page,'block':t['block'],'row':r['native_row'],
                    'cell':ci,'quote':detail['predicted']},'Raw native mapped cell differs from admitted expected text; mapper did not create the character substitution.'))
            if kind=='fields' and raw_available:
                ef=expected['expected_fields'][ordinal]
                for pg in parsed['pages']:
                    if pg['page']!=page:continue
                    for bi,b in enumerate(pg['blocks']):
                        if b['kind']!='table':continue
                        for ri,row in enumerate(b['rows']):
                            for ci,c in enumerate(row[:-1]):
                                label=c['text'].rstrip(':')
                                nxt=row[ci+1]
                                if (label in known and known[label]==ident and c['colspan']==nxt['colspan']==1
                                    and nxt['text']==ef['printed_text'] and not detail['credited_exact']):
                                    ev=evidence({'page':page,'block':bi,'row':ri,'cell':ci,
                                      'quote':[c['text'],nxt['text']],'value_cell':ci+1},
                                      'Exact known label and correct value are adjacent in same native row; baseline chose another row or no candidate.')
                                    rec['categories'].append('field_table_mapping');rec['evidence'].append(ev)
                                    adjacent.append({'item_id':item_id,'baseline_predicted':detail['predicted'],**ev})
                if detail['predicted'] is not None and not detail['observed_exact']:
                    if detail['predicted'].replace('\n',', ')==ef['printed_text']:
                        rec['categories'].append('typed_conversion_or_scoring')
                        rec['evidence'].append({'reason':'Admitted target joins address lines with comma-space; native candidate uses newline. This is a representation/scoring mismatch, not evidence of unread characters.', 'quote':detail['predicted']})
                if ident=='hybrid_field_addendum':
                    rec['categories']+=['text_recognition_or_omission','field_table_mapping']
                    rec['evidence'].append(raw_quote('FIELD-ADDENHUM RISER VALVE VLV-02B TAGGED CLOSED',
                        'Addendum content exists with corrupted label/value spelling and punctuation; not a complete text omission. Exact dev label rule cannot match.'))
                if ident=='hybrid_holdover_stamp':
                    rec['categories']+=['text_recognition_or_omission','field_table_mapping']
                    rec['evidence'].append(raw_quote('RASTER STAMP: HOLD EQUIP DH-00855 - 24H - AUTH J. RIVERA',
                        'Expected +24H appears as - 24H; unknown field label also prevents mapping.'))
            if detail['observed_exact'] and not typed['observed_exact']:
                rec['categories'].append('typed_conversion_or_scoring')
                rec['evidence'].append({'reason':'Printed candidate is exact but frozen typed conversion rejects it.',
                                        'quote':detail['predicted'],'typed_status':typed['status']})
            if failed and not rec['categories']:rec['categories'].append('ambiguous_unadjudicated')
            rec['categories']=sorted(set(rec['categories']))
            # Exact substring occurrences are a search aid only, never used to assign a cause.
            if failed and raw_available:
                rec['exact_text_occurrences_same_page']=[loc for loc in locs if loc['page']==page and rec['expected'] and rec['expected'] in loc['quote']]
            items.append(rec)
    # Span structure has a distinct demonstrated cause, without fabricating repaired cells.
    if fid=='SYN-WO-02-v2-skew-neg3deg':
        span=parsed['pages'][0]['blocks'][10]
        assert span['rows'][0][2]['colspan']==2
        for rec in items:
            if rec['kind']=='cells':
                rec['categories']=sorted(set(rec['categories'])-{'ambiguous_unadjudicated'}|{'native_parse_or_structure','field_table_mapping'})
                rec['evidence'].append(evidence({'page':1,'block':10,'row':0,'quote':span['native_body']},
                   'Native parser accepts colspan=2, but exact header matcher requires unit colspan; expanded five-cell rows cannot be silently scored as four columns. No recovery is attempted.'))
    absences=[]
    for target,detail in zip(expected['expected_absences'],original['expected_absences']['details']):
        hits=[loc for loc in locs if loc['page']==target['page_number'] and target['label_printed'] in loc['quote']]
        absences.append({'expected':target,'baseline':detail,'label_locations':hits,
                         'causal_status':'runtime_unavailable' if not raw_available else 'unadjudicated_absence_semantics' if detail['unmapped'] else 'baseline_candidate_observed',
                         'limit':'A blank candidate or an unmapped label is not a comprehensive search for invented values elsewhere.'})
    counts={c:sum(c in i['categories'] for i in items) for c in CATEGORIES}
    return {'fixture_id':fid,'family_id':fixture['family_id'],'split':fixture['split'],'supplemental':supplemental,
            'completion':original['completion'],'raw_available':raw_available,'raw_path':raw_path.as_posix() if raw_available else None,
            'missing_raw_path':None if raw_available else raw_path.as_posix(),
            'parse_errors':original['parse_errors'],'score_reproduced_exactly':True,
            'metrics':{m:{k:original[m][k] for k in ('correct','total','rate')} for m in METRICS},
            'mapping_coverage':original['mapping_coverage'],'category_item_counts_nonexclusive':counts,
            'failed_field_or_cell_items':sum(not i['printed_credit'] or not i['typed_credit'] for i in items),
            'unknown_field_or_cell_items':counts['ambiguous_unadjudicated'],
            'unmapped_unverified_absence_slots':sum(a['baseline']['unmapped'] for a in absences),
            'same_row_diagnostic_opportunities':adjacent,'items':items,'absences':absences,
            'schema_relative_excess':{'unmatched_field_candidates':original['fields']['unmatched_candidates'],
                                     'extra_rows':original['cells']['extra_rows'],'extra_cells':original['cells']['extra_cells'],
                                     'absence_violations':original['expected_absences']['violations']}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args()
    out=(ROOT/args.out).resolve();out.relative_to(OWN)
    assert out!=OWN
    source_identity()
    global parse_native,extract_prediction,score_document,reference_for,fixtures
    sys.path.insert(0,str(ROOT/'qualification/baseline'))
    from native import parse_native,extract_prediction
    from score import score_document,summarize
    from corpus import reference_for
    from typed_values import compare
    manifest=load('evaluation/manifests/corpus-manifest.json');fixtures=manifest['fixtures']
    assert len(fixtures)==26
    mapping=load('qualification/baseline/mapping.json')
    packets={key:load(run/'scores.json') for key,run in RUNS.items()}
    runs={key:load(run/'run-result.json') for key,run in RUNS.items()}
    for key,packet in packets.items():
        assert packet['run_result_sha256']==inputs[(RUNS[key]/'run-result.json').as_posix()]['sha256']
    primary=packets['dev']['scores']+packets['eval_holdout']['scores']
    original_consolidation=load(RUNS['eval_holdout']/'primary-results.json')
    assert primary==original_consolidation['primary_scores']
    summary=summarize(primary)
    assert summary==original_consolidation['summary_by_split']
    assert summarize(packets['dev']['scores'])==packets['dev']['summary']
    assert summarize(packets['eval_holdout']['scores'])==packets['eval_holdout']['summary']
    records=[audit_document(s,RUNS[s['split']],next(f for f in fixtures if f['fixture_id']==s['fixture_id']),mapping) for s in primary]
    supplement=[audit_document(s,RUNS['supplement'],next(f for f in fixtures if f['fixture_id']==s['fixture_id']),mapping,True) for s in packets['supplement']['scores']]
    assert len(records)==26 and sum(r['raw_available'] for r in records)==25
    totals={split:{m:{k:sum(r['metrics'][m][k] for r in records if r['split']==split) for k in ('correct','total')} for m in METRICS} for split in ('dev','eval_holdout')}
    cat={c:sum(r['category_item_counts_nonexclusive'][c] for r in records) for c in CATEGORIES}
    adjacent=[{'fixture_id':r['fixture_id'],**op} for r in records for op in r['same_row_diagnostic_opportunities']]
    # Counterfactual probes diagnose existing semantics only, not model behavior or new measured rows.
    probe=compare('2.00 HR',{'value_type':'decimal_2','normalized_value':'2.00'},True,'qty_unit')
    assert probe['credited_exact'] and probe['quantity_unit_observed']=='HR'
    revisions={'initial_base':'5e1241d6d365d664f12619d415f48ec3d3b7ddca','authority':AUTHORITY,
               'baseline_source':SOURCE,'baseline_author_report':'d1858bec883ab4066ae6a05096ed4bf3c85230e3',
               'baseline_independent_report':'38f00f46d6a37f26cc7d34d02a1015101269e865',
               'baseline_tree':git('rev-parse',SOURCE+':qualification/baseline'),
               'helper_commit':git('log','-1','--format=%H','--',str(Path(__file__).relative_to(ROOT))),
               'executing_head':git('rev-parse','HEAD')}
    for path in ['docs/coordination/WP-0007/final-disposition/README.md',
                 'docs/agent-reports/eld-rd-astra/WP-0007/004_2026-11-16_verification_eld-rd-astra.md',
                 'docs/agent-reports/eld-baseline-reviewer/WP-0007/005_2026-11-16_review_eld-baseline-reviewer.md',
                 'docs/coordination/WP-0008-0009-authority.md',
                 'docs/kickoffs/WP-0009-eld-mapping-author-diagnosis.md',
                 Path(__file__).relative_to(ROOT)]:read(path)
    payload={'schema':'eld-wp0009-diagnosis/1','revisions':revisions,
             'method':'CPU-only exact unchanged B0 score and summary reproduction; finite local causal adjudications with explicit residual unknowns. No proposed mapping executed.',
             'category_counts_are_nonexclusive':True,'categories':CATEGORIES,
             'primary_document_denominator':26,'primary_completed':25,'split_denominators':totals,
             'original_summary_reproduced':summary,'category_item_counts_nonexclusive':cat,
             'same_row_observed_opportunities':adjacent,'documents':records,
             'supplemental_recovery_excluded_from_primary':supplement,
             'original_run_failures':{key:run.get('failure') for key,run in runs.items()},
             'quantity_unit_counterfactual':{'input':'2.00 HR','numeric_target':'2.00','result':probe,
               'interpretation':'Supported units are validated lexically but not compared to a unit target. This probe is not an observed model error and is excluded from all denominators.'},
             'limits':['Known exposed corpus is regression data, never a fresh holdout.',
               'Categories overlap; counts are affected field/cell slots, not exhaustive causal percentages.',
               'Exact raw substring occurrence is not field/table provenance or proof of full recognition.',
               'Reference text uses admitted clean-parent vector data plus declared hybrid text, not visual re-adjudication of each transformed PDF.',
               'All26 absence slots retain baseline diagnostics; unmatched candidates/excess do not exhaust hallucination.',
               'No complete attribution for row/page/link metrics; original denominators and results retained.']}
    out.mkdir(parents=True,exist_ok=True)
    (out/'ledger.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    inventory={'authority':AUTHORITY,'baseline_source':SOURCE,'files':list(sorted(inputs.values(),key=lambda x:x['path'])),
               'missing_inputs':[r['missing_raw_path'] for r in records if r['missing_raw_path']],
               'scope':'Exact files consumed by helper. PDF reads are clean-parent reference construction only; original transformed PDFs and token IDs are not needed to rescore saved raw text.'}
    (out/'input-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    lines=['# Frozen CPU diagnosis accounting','',f"Helper {revisions['helper_commit']}; executing HEAD {revisions['executing_head']}.",'',
           'All 26 primary score objects and original split/family summaries reproduced exactly. Supplement is separate.',
           'Counts below use printed credit. Unknown is unadjudicated failed printed/typed field or cell items; category counts overlap.','',
           '| Document | State | Fields | Cells | Typed cells | Unknown items | Unverified absence |',
           '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in records:
        def frac(m):return str(r['metrics'][m]['correct'])+'/'+str(r['metrics'][m]['total'])
        lines.append(f"| {r['fixture_id']} | {r['completion']} | {frac('fields')} | {frac('cells')} | {frac('normalized_cells')} | {r['unknown_field_or_cell_items']} | {r['unmapped_unverified_absence_slots']} |")
    lines+=['','Nonexclusive affected field/cell counts: '+json.dumps(cat)+'.','',
            f'Same-row exact known-label/value diagnostic opportunities: {len(adjacent)}. This is evidence for a proposed change, not a measured improvement.',
            '',f'Input inventory: {len(inputs)} present files; one unavailable original raw output.']
    (out/'accounting.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'pass':True,'score_objects_reproduced':len(records),'supplemental_scores_reproduced':len(supplement),
                      'inputs':len(inputs),'categories_nonexclusive':cat,'same_row_opportunities':len(adjacent)},indent=2))


if __name__=='__main__':main()
