"""Frozen CPU guard tests plus paired retained-output regression; no fresh inputs."""
import argparse
import hashlib
import importlib.abc
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','triton','pypdfium2') or fullname=='q0harness.backend_torch':
            raise RuntimeError('CPU checks prohibit model/renderer imports: '+fullname)
sys.meta_path.insert(0,NoModelImports())
from qualification.mapping_v1.common import HERE,git,sha,write,mapping,verify_comparator,summarize
from qualification.mapping_v1.scoring import paired
from corpus import reference_for

RUNS={'dev':'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6',
      'eval_holdout':'docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d',
      'supplement':'docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca'}


def main():
    args=argparse.ArgumentParser();args.add_argument('--out',required=True);out=(ROOT/args.parse_args().out).resolve()
    out.relative_to(ROOT/'docs/evidence/WP-0009/eld-mapping-author')
    assert not out.exists(),'Use a new retained evidence directory for every decisive attempt'
    assert not git('status','--porcelain').strip(),'Freeze clean source/helper before decisive checks'
    verify_comparator();head=git('rev-parse','HEAD').decode().strip()
    suite=unittest.defaultTestLoader.discover(str(HERE/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out.mkdir(parents=True)
    tests={'executing_head':head,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    write(out/'tests.json',tests)
    if not result.wasSuccessful():return 1
    inputs={}
    def read(relative):
        relative=Path(relative).as_posix();data=(ROOT/relative).read_bytes()
        inputs[relative]={'path':relative,'bytes':len(data),'sha256':sha(data),'git_blob':git('hash-object','--',relative).decode().strip()}
        return data
    def load(relative):return json.loads(read(relative))
    manifest=load('evaluation/manifests/corpus-manifest.json');fixtures=manifest['fixtures']
    rules=mapping();read('qualification/baseline/mapping.json')
    packets={key:load(Path(run)/'scores.json') for key,run in RUNS.items()}
    original=packets['dev']['scores']+packets['eval_holdout']['scores']
    consolidated=load(Path(RUNS['eval_holdout'])/'primary-results.json')
    assert original==consolidated['primary_scores'] and summarize(original)==consolidated['summary_by_split']
    documents=[];supplements=[];primary_new=[];gain_count=loss_count=typed_gain=typed_loss=0
    for lane,packet in packets.items():
        run=Path(RUNS[lane]);result_bytes=read(run/'run-result.json');assert sha(result_bytes)==packet['run_result_sha256']
        for old in packet['scores']:
            fid=old['fixture_id'];fx=next(f for f in fixtures if f['fixture_id']==fid)
            e=load(fx['expected_ground_truth_path']);assert inputs[fx['expected_ground_truth_path']]['sha256']==fx['expected_ground_truth_sha256']
            parent=next(f for f in fixtures if f['family_id']==fx['family_id'] and f['variant_kind']=='v0_clean');read(parent['file_path'])
            if fx['variant_kind']=='v3_hybrid':read(fx['source_record_path'])
            ref=reference_for(fx,allow_test=True);raw_path=run/'evidence'/(fid+'.measured.raw.txt')
            available=(ROOT/raw_path).exists();data=read(raw_path) if available else b''
            if available:
                observation=load(run/'evidence'/(fid+'.measured.observation.json'))
                assert observation['raw_output']['sha256_written']==sha(data)
            pair=paired(data.decode('utf-8'),e,ref,old['completion'],rules)
            b0=pair['scores']['b0'];b0['raw_sha256']=sha(data);assert b0==old,fid+' B0 reproduction mismatch'
            new=pair['scores']['mapping_v1'];new['raw_sha256']=sha(data)
            for key in ('cells','normalized_cells','rows','text','page_count','page_sentinels','adjacency','cross_page_links','expected_absences','eligible_for_exact_credit','parse_errors'):
                assert old[key]==new[key],(fid,'unchanged invariant',key)
            assert pair['predictions']['b0']['tables']==pair['predictions']['mapping_v1']['tables']
            changes=[]
            for ordinal,(a,b,at,bt) in enumerate(zip(old['fields']['details'],new['fields']['details'],old['normalized_fields']['details'],new['normalized_fields']['details'])):
                assert a['key']==b['key']
                if a!=b or at!=bt:
                    changes.append({'ordinal':ordinal,'key':a['key'],'old':a,'new':b,'old_typed':at,'new_typed':bt})
                if lane!='supplement':
                    gain_count+=int(b['credited_exact'] and not a['credited_exact']);loss_count+=int(a['credited_exact'] and not b['credited_exact'])
                    typed_gain+=int(bt['credited_exact'] and not at['credited_exact']);typed_loss+=int(at['credited_exact'] and not bt['credited_exact'])
            record={'fixture_id':fid,'family_id':fx['family_id'],'split':fx['split'],'completion':old['completion'],
                    'raw_available':available,'raw_path':raw_path.as_posix() if available else None,'raw_sha256':sha(data),
                    'original_full_score_reproduced':True,'unchanged_table_absence_text_page_link_semantics':True,
                    'field_changes':changes,'mapping_v1_fields':pair['predictions']['mapping_v1']['fields'],'mapping_v1_score':new,
                    'baseline_fields':old['fields']['correct'],'candidate_fields':new['fields']['correct'],'field_denominator':old['fields']['total']}
            if lane=='supplement':supplements.append(record)
            else:documents.append(record);primary_new.append(new)
    assert len(documents)==26 and sum(d['raw_available'] for d in documents)==25
    assert len(supplements)==1
    # Losses remain reported even if they fail the acceptance requirement; never tune a score silently.
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.is_file() and path.suffix=='.py':read(path.relative_to(ROOT))
    for name in ('protocol.json','README.md'):read(Path('qualification/mapping_v1')/name)
    read('docs/coordination/WP-0007/gpu-reviewer-heldout-release/host-before.json')
    payload={'schema':'eld-mapping-v1-regression/1','source_commit':head,'source_tree':git('rev-parse','HEAD:qualification/mapping_v1').decode().strip(),
             'comparator_source':'522f15f1f6e399c36b9c6c107fc08f51862f1fc1','comparator_tree':'deae8e826f4770e880374c68e6a56c8c65b6f8a3',
             'primary_documents':26,'primary_completed':25,'field_gains':gain_count,'field_losses':loss_count,
             'typed_field_gains':typed_gain,'typed_field_losses':typed_loss,
             'baseline_summary':summarize(original),'mapping_v1_summary':summarize(primary_new),
             'documents':documents,'supplement_separate':supplements,
             'limits':['Old heldout is exposed regression data.','One mapping treatment; no model recognition or latency claim.',
                       'Unsupported units, identifier errors, absent deployment rows and partial-label blind spots remain unchanged.','No fresh or sealed content was read.']}
    write(out/'comparison.json',payload)
    write(out/'input-inventory.json',{'source_commit':head,'files':sorted(inputs.values(),key=lambda x:x['path']),
          'missing_original_raw':'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6/evidence/SYN-MP-01-v2-skew-pos4deg.measured.raw.txt',
          'protected_trees':{p:git('rev-parse','HEAD:'+p).decode().strip() for p in ('qualification/baseline','qualification/q0','evaluation')}})
    lines=['# Frozen CPU paired regression','',f'Source: {head}. All26 primary full B0 scores and original summaries reproduced; recovery separate.','',
           '| Document | State | B0 fields | v1 fields | Denominator |','| --- | --- | ---: | ---: | ---: |']
    for d in documents:lines.append(f"| {d['fixture_id']} | {d['completion']} | {d['baseline_fields']} | {d['candidate_fields']} | {d['field_denominator']} |")
    lines+=['',f'Printed field gains {gain_count}; losses {loss_count}. Typed field gains {typed_gain}; losses {typed_loss}.',
            'Table cells, rows, typed cells, text, pages, cross-page links and expected-absence objects are exactly unchanged.']
    (out/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'source':head,'tests':tests,'primary_full_scores_reproduced':26,'supplement':1,'field_gains':gain_count,'field_losses':loss_count,
                      'typed_field_gains':typed_gain,'typed_field_losses':typed_loss,'inputs':len(inputs)},indent=2))
    return int(bool(loss_count or typed_loss))


if __name__=='__main__':raise SystemExit(main())
