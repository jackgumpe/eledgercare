"""Independent CPU reproduction of every exposed full score and diagnostic slot.

Uses unchanged public scoring APIs; independently assembles inputs and compares
complete objects rather than trusting the author's summary or running its main.
"""
import contextlib
from collections import Counter
import datetime
import importlib.abc
import json
from pathlib import Path
import sys
import traceback
import unittest

ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT))
class CPUOnly(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':
            raise RuntimeError('Review prohibits model/renderer imports: '+fullname)
sys.meta_path.insert(0,CPUOnly())
from qualification.coverage_v1.common import HERE,git,sha,write,paired,protocol,verify_frozen_mappers
from qualification.coverage_v1.diagnostics import diagnose
from corpus import reference_for

AUTHOR='docs/research/WP-0011/eld-mapping-author/001'
RUNS=[('dev','docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6'),
      ('heldout','docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d'),
      ('recovery','docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca')]
WP9='docs/evidence/WP-0009/eld-mapping-author/007/attempt-1'
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
inputs={}
def read(path):
    data=(ROOT/path).read_bytes();inputs[path]={'path':path,'bytes':len(data),'sha256':sha(data)};return data
def load(path):return json.loads(read(path))

def verify_inputs():
    inv=load(AUTHOR+'/attempt-2/input-inventory.json')
    for f in inv['files']:
        data=read(f['path']);assert len(data)==f['bytes'] and sha(data)==f['sha256'],f['path']
        assert git('hash-object','--',f['path']).decode().strip()==f['git_blob'],f['path']
    for f in inv['git_objects']:
        data=git('show',f['commit']+':'+f['path']);assert len(data)==f['bytes'] and sha(data)==f['sha256']
    delivery=load(AUTHOR+'/deliverable-inventory.json')
    for f in delivery['files']:
        data=git('show',delivery['deliverable_commit']+':'+f['path'])
        assert len(data)==f['bytes_git'] and sha(data)==f['sha256_git']
        assert git('rev-parse',delivery['deliverable_commit']+':'+f['path']).decode().strip()==f['git_blob']
    def listing(rev):
        result={}
        for row in git('ls-tree','-r','-z',rev).split(b'\0'):
            if row:
                meta,path=row.split(b'\t',1);result[path]=meta
        return result
    base=listing(delivery['base_commit']);head=listing('HEAD')
    assert all(head.get(k)==v for k,v in base.items())
    p=protocol();public=json.loads(git('show',p['public_reservation_commit']+':'+p['public_reservation_path']))
    assert p['fresh_fixtures']==public['fixtures']
    return {'author_input_files':len(inv['files']),'public_objects':len(inv['git_objects']),
            'author_deliverable_files':len(delivery['files']),'protected_base_paths':len(base),
            'public_fixture_descriptors':len(p['fresh_fixtures']),'public_artifact_descriptors':sum(len(f['artifacts']) for f in p['fresh_fixtures'])}

def reproduce():
    old=load('docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json')
    v1={d['fixture_id']:d['mapping_v1_score'] for d in old['documents']}
    fixtures={f['fixture_id']:f for f in load('evaluation/manifests/corpus-manifest.json')['fixtures']}
    candidate=load(AUTHOR+'/attempt-2/diagnostic-ledger.json')
    ledger={d['fixture_id']:d for d in candidate['documents']};recovery=candidate['supplement_separate'][0]
    receipts=[];actual_documents=[];actual_recovery=[]
    def check(fid,raw,expected,reference,completion,comparison,kind,anchors):
        pair=paired(raw or '',expected,reference,completion)
        if kind=='wp9':assert pair==comparison,'Complete prediction/score packet mismatch: '+fid
        else:
            assert {**pair['scores']['b0'],'raw_sha256':sha((raw or '').encode())}==comparison['b0'],'Complete B0 score mismatch: '+fid
            assert {**pair['scores']['mapping_v1'],'raw_sha256':sha((raw or '').encode())}==comparison['mapping_v1'],'Complete v1 score mismatch: '+fid
        diagnostic=diagnose(raw,expected,reference,completion,precomputed=pair);diagnostic.pop('historical_scores');diagnostic['anchors']=anchors
        recorded=recovery if kind=='recovery' else ledger[fid]
        assert diagnostic==recorded,'Complete diagnostic ledger mismatch: '+fid
        receipts.append({'fixture_id':fid,'population':kind,'completion':completion,'raw_available':raw is not None,
                         'raw_sha256':None if raw is None else sha(raw.encode()),'full_pair_sha256_canonical':sha(canonical(pair)),
                         'full_diagnostic_sha256_canonical':sha(canonical(diagnostic)),'recorded_diagnostic_sha256_canonical':sha(canonical(recorded)),
                         'full_scores':pair['scores'],'presence_denominator':diagnostic['presence_denominator'],
                         'old_full_scores_equal':True,'diagnostic_all_fields_equal':True})
        (actual_recovery if kind=='recovery' else actual_documents).append(diagnostic)
    for lane,run in RUNS:
        for score in load(run+'/scores.json')['scores']:
            fid=score['fixture_id'];fx=fixtures[fid];expected=load(fx['expected_ground_truth_path'])
            reference=reference_for(fx,allow_test=True)
            path=run+'/evidence/'+fid+'.measured.raw.txt';raw=read(path) if (ROOT/path).exists() else None
            if raw is not None:
                obs=load(run+'/evidence/'+fid+'.measured.observation.json');assert sha(raw)==obs['raw_output']['sha256_written']
            previous=old['supplement_separate'][0]['mapping_v1_score'] if lane=='recovery' else v1[fid]
            anchors={'raw_path':path,'raw_available':raw is not None,'expected_path':fx['expected_ground_truth_path'],
                     'b0_score_packet':run+'/scores.json','v1_score_packet':'docs/evidence/WP-0009/eld-mapping-author/011/attempt-1/comparison.json'}
            check(fid,None if raw is None else raw.decode(),expected,reference,score['completion'],{'b0':score,'mapping_v1':previous},lane,anchors)
    for packet in load(WP9+'/scores.json')['records']:
        fid=packet['fixture_id'];ep='evaluation/mapping_v1/corpus/r1/expected/'+fid+'.json';rp='evaluation/mapping_v1/corpus/r1/reference/'+fid+'.json'
        path=WP9+'/run/evidence/'+fid+'.measured.raw.txt';raw=read(path)
        obs=load(WP9+'/run/evidence/'+fid+'.measured.observation.json');assert sha(raw)==obs['raw_output']['sha256_written']
        check(fid,raw.decode(),load(ep),load(rp),packet['completion'],{k:v for k,v in packet.items() if k!='fixture_id'},'wp9',
              {'raw_path':path,'raw_available':True,'expected_path':ep,'b0_v1_score_packet':WP9+'/scores.json'})
    assert actual_documents==candidate['documents'] and actual_recovery==candidate['supplement_separate']
    summary={'primary_documents':len(actual_documents),'completed_primary_documents':sum(d['completion']=='completed' for d in actual_documents),
             'expected_field_cell_slots':sum(len(d['slots']) for d in actual_documents),
             'presence_eligible_slots':sum(d['presence_denominator']['eligible_slots'] for d in actual_documents),
             'presence_unavailable_slots':sum(d['presence_denominator']['unavailable_slots'] for d in actual_documents),
             'flags_nonexclusive':{name:dict(Counter(f for d in actual_documents for s in d['slots'] for f in s['mappers'][name]['evidence_flags_nonexclusive'])) for name in ('b0','mapping_v1')}}
    assert all(summary[k]==candidate['summary'][k] for k in summary)
    prior=load('docs/research/WP-0009/eld-mapping-author/diagnosis/results/ledger.json')
    for item in candidate['reused_reviewed_diagnosis']:
        pointer=item['json_pointer'].split('/');record=prior['documents'][int(pointer[2])]['items'][int(pointer[4])]
        assert record==item['item']
    assert candidate['prior_quantity_counterfactual']==prior['quantity_unit_counterfactual']
    return {'summary':summary,'records':receipts,'original_primary_full_scores_reproduced':26,
            'exposed_wp9_full_predictions_scores_reproduced':4,'separate_recovery_reproduced':1,
            'reused_manual_category_anchors_verified':len(candidate['reused_reviewed_diagnosis'])}

def main():
    out=Path(sys.argv[1]).resolve();out.relative_to(Path(__file__).parent)
    assert not out.exists();assert not git('status','--porcelain').strip(),'Freeze reviewer helper first'
    verify_frozen_mappers();assert git('rev-parse','HEAD:qualification/coverage_v1').decode().strip()=='ed07a273a57a71b43b0fed9cea12a2245d7c7958'
    out.mkdir(parents=True)
    receipt={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'executing_head':git('rev-parse','HEAD').decode().strip(),
             'source_commit':'adb51ac317db18950f3f1ef4629864127956eddc','helper_sha256':sha(Path(__file__).read_bytes()),'python':sys.version}
    try:
        with (out/'tests-stdout.txt').open('x',encoding='utf-8',newline='') as stdout,(out/'tests-stderr.txt').open('x',encoding='utf-8',newline='') as stderr:
            with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                result=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.discover(str(HERE/'tests')))
        receipt['tests']={'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
        assert result.wasSuccessful()
        receipt['identity']=verify_inputs()
        full=reproduce();write(out/'reproduction.json',full);receipt['summary']=full['summary'];receipt['status']='PASS'
    except BaseException:
        receipt['status']='FAIL';receipt['traceback']=traceback.format_exc();raise
    finally:
        receipt['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(out/'execution.json',receipt);write(out/'input-inventory.json',{'files':sorted(inputs.values(),key=lambda x:x['path'])})
        print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
