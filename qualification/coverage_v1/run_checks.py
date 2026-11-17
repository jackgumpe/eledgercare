"""Frozen CPU checks and exposed-output diagnosis only; no sealed artifact access."""
import argparse
from collections import Counter
import importlib.abc
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':
            raise RuntimeError('CPU preparation prohibits model/renderer imports: '+fullname)
sys.meta_path.insert(0,NoModelImports())
from qualification.coverage_v1.common import HERE,git,sha,write,protocol,paired,verify_frozen_mappers
from qualification.coverage_v1.diagnostics import diagnose
from corpus import reference_for

OLD_RUNS={'dev':'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6',
    'eval_holdout':'docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d',
    'supplement':'docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca'}
WP9='docs/evidence/WP-0009/eld-mapping-author/007/attempt-1'
OLD_DIAG='docs/research/WP-0009/eld-mapping-author/diagnosis/results/ledger.json'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);out=(ROOT/parser.parse_args().out).resolve()
    out.relative_to(ROOT/'docs/research/WP-0011/eld-mapping-author')
    assert not out.exists(),'New retained attempt required'
    assert not git('status','--porcelain').strip(),'Freeze source/helpers first'
    verify_frozen_mappers();head=git('rev-parse','HEAD').decode().strip()
    suite=unittest.defaultTestLoader.discover(str(HERE/'tests'));result=unittest.TextTestRunner(verbosity=2).run(suite)
    out.mkdir(parents=True)
    tests={'source_commit':head,'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    write(out/'tests.json',tests)
    if not result.wasSuccessful():return 1
    inputs={};objects=[]
    def read(path):
        path=Path(path).as_posix();data=(ROOT/path).read_bytes()
        inputs[path]={'path':path,'bytes':len(data),'sha256':sha(data),'git_blob':git('hash-object','--',path).decode().strip()}
        return data
    def load(path):return json.loads(read(path))
    p=load('qualification/coverage_v1/protocol.json')
    public=git('show',p['public_reservation_commit']+':'+p['public_reservation_path'])
    assert sha(public)==p['public_reservation_sha256'] and json.loads(public)['fixtures']==p['fresh_fixtures']
    objects.append({'commit':p['public_reservation_commit'],'path':p['public_reservation_path'],'bytes':len(public),'sha256':sha(public),'scope':'Public metadata only; no artifact reads'})
    ledger=load(OLD_DIAG);comparison=load('docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json')
    manifest=load('evaluation/manifests/corpus-manifest.json');fixtures={f['fixture_id']:f for f in manifest['fixtures']}
    original={};records=[];supplements=[];reused=[]
    for lane,run in OLD_RUNS.items():original[lane]=load(run+'/scores.json')['scores']
    previous={d['fixture_id']:d for d in comparison['documents']};supplement_previous=comparison['supplement_separate'][0]
    for lane,scores in original.items():
        for old in scores:
            fid=old['fixture_id'];fx=fixtures[fid];expected=load(fx['expected_ground_truth_path'])
            parent=next(f for f in fixtures.values() if f['family_id']==fx['family_id'] and f['variant_kind']=='v0_clean');read(parent['file_path'])
            if fx['variant_kind']=='v3_hybrid':read(fx['source_record_path'])
            reference=reference_for(fx,allow_test=True)
            raw_path=OLD_RUNS[lane]+'/evidence/'+fid+'.measured.raw.txt';available=(ROOT/raw_path).exists();data=read(raw_path) if available else b''
            if available:
                obs=load(OLD_RUNS[lane]+'/evidence/'+fid+'.measured.observation.json');assert sha(data)==obs['raw_output']['sha256_written']
            pair=paired(data.decode(),expected,reference,old['completion'])
            assert {**pair['scores']['b0'],'raw_sha256':sha(data)}==old,'Historical B0 changed: '+fid
            v1=supplement_previous if lane=='supplement' else previous[fid]
            assert {**pair['scores']['mapping_v1'],'raw_sha256':sha(data)}==v1['mapping_v1_score'],'Historical v1 changed: '+fid
            diagnostic=diagnose(data.decode() if available else None,expected,reference,old['completion'],precomputed=pair)
            diagnostic.pop('historical_scores')
            diagnostic['anchors']={'raw_path':raw_path,'raw_available':available,'expected_path':fx['expected_ground_truth_path'],
                'b0_score_packet':OLD_RUNS[lane]+'/scores.json','v1_score_packet':'docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json'}
            (supplements if lane=='supplement' else records).append(diagnostic)
    packet=load(WP9+'/scores.json')
    for old in packet['records']:
        fid=old['fixture_id'];root='evaluation/mapping_v1/corpus/r1/'
        expected=load(root+'expected/'+fid+'.json');reference=load(root+'reference/'+fid+'.json')
        raw_path=WP9+'/run/evidence/'+fid+'.measured.raw.txt';data=read(raw_path)
        obs=load(WP9+'/run/evidence/'+fid+'.measured.observation.json');assert sha(data)==obs['raw_output']['sha256_written']
        pair=paired(data.decode(),expected,reference,old['completion'])
        assert pair=={k:v for k,v in old.items() if k!='fixture_id'},'WP9 published prediction/score changed: '+fid
        diagnostic=diagnose(data.decode(),expected,reference,old['completion'],precomputed=pair);diagnostic.pop('historical_scores')
        diagnostic['anchors']={'raw_path':raw_path,'raw_available':True,'expected_path':root+'expected/'+fid+'.json','b0_v1_score_packet':WP9+'/scores.json'}
        records.append(diagnostic)
    # Reuse already independently reviewed detailed attribution; do not silently relabel it as a new metric.
    seen=set()
    for di,document in enumerate(ledger['documents']):
        for ii,item in enumerate(document['items']):
            for category in item['categories']:
                if category not in seen:
                    seen.add(category);reused.append({'category':category,'fixture_id':document['fixture_id'],
                        'immutable_ledger':OLD_DIAG,'json_pointer':f'/documents/{di}/items/{ii}','item':item,'raw_path':document['raw_path'] or document['missing_raw_path']})
    assert len(records)==30 and len(supplements)==1
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.is_file() and path.suffix=='.py':read(path.relative_to(ROOT))
    for name in ('mapping.json',):read('qualification/baseline/'+name)
    for name in ('README.md','INTERFACE.md'):read('qualification/coverage_v1/'+name)
    read('docs/coordination/WP-0007/gpu-reviewer-heldout-release/host-before.json')
    counts={name:dict(Counter(flag for d in records for slot in d['slots'] for flag in slot['mappers'][name]['evidence_flags_nonexclusive'])) for name in ('b0','mapping_v1')}
    summary={'source_commit':head,'source_tree':git('rev-parse','HEAD:qualification/coverage_v1').decode().strip(),
        'tests':tests,'original_primary_full_scores_reproduced':26,'exposed_wp9_full_predictions_scores_reproduced':4,'separate_recovery_reproduced':1,
        'primary_documents':30,'completed_primary_documents':sum(d['completion']=='completed' for d in records),
        'expected_field_cell_slots':sum(len(d['slots']) for d in records),'presence_eligible_slots':sum(d['presence_denominator']['eligible_slots'] for d in records),
        'presence_unavailable_slots':sum(d['presence_denominator']['unavailable_slots'] for d in records),
        'flags_nonexclusive':counts,'reused_prior_category_counts':ledger['category_item_counts_nonexclusive'],
        'limitations':['Historical and WP9 documents are exposed; no generalization claim.','Exact payload presence is not semantic or association correctness.',
            'No WP11 private payload read.','Original failure stays primary; recovery separate.','Counterfactual and observed unit evidence remain distinct.']}
    write(out/'diagnostic-ledger.json',{'summary':summary,'documents':records,'supplement_separate':supplements,'reused_reviewed_diagnosis':reused,
        'prior_quantity_counterfactual':ledger['quantity_unit_counterfactual']})
    write(out/'input-inventory.json',{'source_commit':head,'files':sorted(inputs.values(),key=lambda x:x['path']),'git_objects':objects,
        'unavailable_original_raw':[d['anchors']['raw_path'] for d in records if not d['raw_available']]})
    write(out/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('flags_nonexclusive','reused_prior_category_counts','limitations')},indent=2))
    print(json.dumps({'consumed_files':len(inputs),'public_git_objects':len(objects),'nonexclusive_flags':counts},indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
