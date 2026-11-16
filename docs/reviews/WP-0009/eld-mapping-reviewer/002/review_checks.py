"""Independent finite CPU diagnosis review; no treatment or prediction mutation."""
from pathlib import Path
from collections import Counter
import hashlib, importlib.util, json, re, subprocess, sys

ROOT = Path(__file__).resolve().parents[5]
OWN = Path(__file__).resolve().parent
SCRATCH = ROOT / '.scratch/wp0009-reviewer/diagnosis'
AUTHOR = ROOT / 'docs/research/WP-0009/eld-mapping-author/diagnosis'
BASE = '8549ecd92eae045b15cd04a068cb7cb54ed9716c'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    assert not git('status','--porcelain'), 'Freeze must execute from clean worktree'
    head=git('rev-parse','HEAD')
    assert git('rev-parse','HEAD:qualification/baseline')==git('rev-parse','522f15f1f6e399c36b9c6c107fc08f51862f1fc1:qualification/baseline')
    sys.path.insert(0,str(ROOT/'qualification/baseline'))
    from native import parse_native, extract_prediction
    from score import score_document, summarize
    from corpus import reference_for
    mapping=load(ROOT/'qualification/baseline/mapping.json')
    manifest=load(ROOT/'evaluation/manifests/corpus-manifest.json')
    expected_by_id={f['fixture_id']:f for f in manifest['fixtures']}
    ledger=load(AUTHOR/'results/ledger.json')
    ev=ROOT/'docs/evidence/WP-0007/eld-rd-astra'
    runs={'dev':ev/'runtime-dev/20261116T051059Z-eda73dc6',
          'eval_holdout':ev/'runtime-heldout/20261116T145728Z-07a28a6d',
          'supplement':ev/'runtime-recovery/20261116T142841Z-284039ca'}
    packets={key:load(path/'scores.json') for key,path in runs.items()}
    primary=packets['dev']['scores']+packets['eval_holdout']['scores']
    assert len(primary)==26 and len({s['fixture_id'] for s in primary})==26
    parsed_by_id={}; recomputed=[]; supplement=[]; evidence_records=[]
    for key,packet in packets.items():
        for score in packet['scores']:
            fixture=expected_by_id[score['fixture_id']]
            rawpath=runs[key]/'evidence'/(fixture['fixture_id']+'.measured.raw.txt')
            raw=rawpath.read_text(encoding='utf-8') if rawpath.exists() else ''
            parsed=parse_native(raw)
            prediction=extract_prediction(parsed,mapping)
            expected=load(ROOT/fixture['expected_ground_truth_path'])
            got=score_document(prediction,expected,reference_for(fixture,allow_test=True),score['completion'])
            got['raw_sha256']=hashlib.sha256(raw.encode()).hexdigest()
            assert got==score,fixture['fixture_id']
            (supplement if key=='supplement' else recomputed).append(got)
            if key!='supplement':parsed_by_id[fixture['fixture_id']]=parsed
            evidence_records.append({'fixture_id':fixture['fixture_id'],'split':key,'raw_exists':rawpath.exists(),'raw_sha256':got['raw_sha256'],'full_score_equal':True})
    assert recomputed==primary
    assert summarize(recomputed)==load(runs['eval_holdout']/'primary-results.json')['summary_by_split']
    original_failure=[s for s in recomputed if s['completion']!='completed']
    assert len(original_failure)==1 and original_failure[0]['fields']['total']==15 and original_failure[0]['cells']['total']==180
    assert len(supplement)==1 and supplement[0]['fixture_id']==original_failure[0]['fixture_id']
    assert supplement[0]['completion']=='completed' and not supplement[0]['eligible_for_exact_credit']
    # Run the exact author's helper with only its output-root guard redirected to owned scratch.
    spec=importlib.util.spec_from_file_location('author_diagnosis',AUTHOR/'diagnose.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OWN=SCRATCH.parent
    sys.argv=[str(AUTHOR/'diagnose.py'),'--out',str(SCRATCH)]
    module.main()
    repeated=load(SCRATCH/'ledger.json')
    differences=[k for k in ledger if ledger[k]!=repeated[k]]
    assert differences==['revisions']
    assert {k:v for k,v in ledger['revisions'].items() if k!='executing_head'}=={k:v for k,v in repeated['revisions'].items() if k!='executing_head'}
    assert load(AUTHOR/'results/input-inventory.json')==load(SCRATCH/'input-inventory.json')
    known={r['label']:r['field_id'] for r in mapping['labels']}
    pattern=re.compile('|'.join(re.escape(s) for s in sorted(known,key=lambda x:(-len(x),x))))
    def hits(text):
        return [m[0] for m in pattern.finditer(text) if (m.start()==0 or not text[m.start()-1].isalpha()) and (m.end()==len(text) or text[m.end()] in ': \n[')]
    opportunities=[]
    for op in ledger['same_row_observed_opportunities']:
        fixture=expected_by_id[op['fixture_id']]
        fields=load(ROOT/fixture['expected_ground_truth_path'])['expected_fields']
        expected=fields[int(op['item_id'].split(':')[-1])]
        block=parsed_by_id[op['fixture_id']]['pages'][op['page']-1]['blocks'][op['block']]
        row=block['rows'][op['row']]; left=row[op['cell']]; right=row[op['value_cell']]
        assert [left['text'],right['text']]==op['quote']
        assert right['text']==expected['printed_text'] and known[left['text'].rstrip(':')]==expected['field_id']
        assert expected['page_number']==op['page']
        active_headers=[i for i,r in enumerate(block['rows'][:op['row']+1]) if any([c['text'] for c in r]==t['headers'] and all(c['colspan']==1 for c in r) for t in mapping['tables'])]
        assert not active_headers
        flags={'unit_spans':left['colspan']==right['colspan']==1,'nonempty_neighbor':bool(right['text']),
               'neighbor_not_colon_label':not right['text'].endswith(':'),'neighbor_has_no_known_label_match':not hits(right['text'])}
        opportunities.append({**op,'expected_field':expected['field_id'],'guard_observations':flags,'same_label_occurrences_in_block':sum(c['text'].rstrip(':')==left['text'].rstrip(':') for r in block['rows'] for c in r)})
    assert len(opportunities)==27 and all(all(o['guard_observations'].values()) for o in opportunities)
    # Inspect real raw contexts for negative guard cases, without implementing the new mapper.
    contexts=[]
    for fid,parsed in parsed_by_id.items():
        for page in parsed['pages']:
            for bi,block in enumerate(page['blocks']):
                for ri,row in enumerate(block['rows']):
                    for ci,cell in enumerate(row):
                        if cell['text'].rstrip(':') not in known:continue
                        neighbor=row[ci+1] if ci+1<len(row) else None
                        cases=[]
                        if neighbor is None:cases.append('no_right_neighbor')
                        elif not neighbor['text']:cases.append('empty_right_neighbor')
                        elif neighbor['text'].endswith(':') or hits(neighbor['text']):cases.append('label_like_right_neighbor')
                        if cell['colspan']!=1 or (neighbor and neighbor['colspan']!=1):cases.append('spanning_pair')
                        if sum(c['text'].rstrip(':')==cell['text'].rstrip(':') for r in block['rows'] for c in r)>1:cases.append('repeated_label_in_block')
                        if cases:contexts.append({'fixture_id':fid,'page':page['page'],'block':bi,'row':ri,'cell':ci,'values':[c['text'] for c in row],'cases':cases})
    items=[i for d in ledger['documents'] for i in d['items']]
    assert len(items)==2162 and sum(i['kind']=='fields' for i in items)==361
    assert sum(i['kind']=='cells' for i in items)==1801
    category_counts=Counter(c for i in items for c in i['categories'])
    assert dict(category_counts)==ledger['category_item_counts_nonexclusive']
    assert sum(not i['printed_credit'] or not i['typed_credit'] for i in items)==1245
    assert category_counts['ambiguous_unadjudicated']==150
    assert sum(d['unmapped_unverified_absence_slots'] for d in ledger['documents'])==17
    local_evidence=Counter()
    for doc in ledger['documents']:
        parsed=parsed_by_id[doc['fixture_id']]
        for item in doc['items']:
            for evidence in item['evidence']:
                if all(k in evidence for k in ['page','block','row','cell']) and isinstance(evidence.get('quote'),str):
                    actual=parsed['pages'][evidence['page']-1]['blocks'][evidence['block']]['rows'][evidence['row']][evidence['cell']]['text']
                    assert actual==evidence['quote'],(doc['fixture_id'],item['item_id'])
                    local_evidence['exact_to_expected' if actual==item['expected'] else 'different_from_expected']+=1
    results={'status':'PASS','executing_head':head,'review_input_merge':BASE,'independent_full_scores':evidence_records,
             'author_reproduction_differences':differences,'primary_documents':26,'completed':25,'supplemental_excluded':1,
             'fields':361,'cells':1801,'failed_printed_or_typed':1245,'categories_nonexclusive':dict(category_counts),
             'unverified_absences':17,'split_denominators':ledger['split_denominators'],
             'same_row_opportunities':opportunities,'guard_contexts':contexts,'guard_context_counts':dict(Counter(c for r in contexts for c in r['cases'])),
             'independently_verified_cell_evidence':dict(local_evidence),'no_treatment_implemented':True,
             'protected_trees':{p:git('rev-parse','HEAD:'+p) for p in ['qualification/baseline','qualification/q0','evaluation','src','workers','web','research'] if git('ls-tree','HEAD','--',p)},
             'scratch_files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(SCRATCH.rglob('*')) if p.is_file()]}
    (OWN/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({k:results[k] for k in ['status','executing_head','primary_documents','completed','fields','cells','guard_context_counts','independently_verified_cell_evidence']},indent=2))

if __name__=='__main__':main()
