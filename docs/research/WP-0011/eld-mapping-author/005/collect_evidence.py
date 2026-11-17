"""Frozen CPU-only collection of the single released WP11 author execution.

No inference, scoring rerun, source mutation or model/cache publication. Every
external run file is copied with its relative name or inventoried retained-only.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
BASE='65f24d33be9eb4571a8372a28e3bf2114173d928'
SOURCE='253519e07e7d45cf1f5ecb3e03053582f7f7d4cc'
TREE='6bdab544c9fe26cbf093cc765212db2a2e7a97a5'
AUTHORITY='56b36b52e682a7396b02c34cf40c85a4f31f9329'
RELEASE='docs/coordination/WP-0011/releases/author.json'
RUN=Path('C:/Users/jackg/eLedgerCare-Coverage/WP-0011/author/runs/author/20261117T095427Z-75adb724')
SCRATCH=ROOT/'.scratch/wp0011-coverage-execution/005-attempt-1'
EV='docs/evidence/WP-0011/eld-mapping-author/005/'
DOS='docs/research/WP-0011/eld-mapping-author/005/'
CACHES={'cuda-cache','hf-home','hf-modules','home','inductor-cache','tmp','torch-home'}
METRICS=('fields','cells','normalized_fields','normalized_cells','rows','expected_absences','page_count')

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads(path.read_bytes().decode('utf-8-sig'))
def obj(rev,path):return git('show',rev+':'+path)
def ident(rev,path):return git('rev-parse',rev+':'+path).decode().strip()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(data,f,indent=2,ensure_ascii=False);f.write('\n')
def tree_entries(rev):
    result={}
    for line in git('ls-tree','-r','-z',rev).split(b'\0'):
        if line:
            meta,path=line.split(b'\t',1);result[path.decode()]=tuple(meta.decode().split())
    return result

def aggregate(records):
    stage={}
    for kind in ('field','cell'):
        stage[kind]={}
        for metric in ('exact_visible_payload_presence','schema_supported'):
            stage[kind][metric]={key:sum(r['diagnostic']['stage_metrics'][kind][metric][key] for r in records) for key in ('numerator','denominator','unavailable')}
        stage[kind]['ambiguous_value_occurrences_or_reuse']=sum(r['diagnostic']['stage_metrics'][kind]['ambiguous_value_occurrences_or_reuse'] for r in records)
        for name in ('b0','mapping_v1'):
            stage[kind][name]={metric:{key:sum(r['diagnostic']['stage_metrics'][kind][name][metric][key] for r in records)
                for key in ('numerator','denominator','unavailable')} for metric in ('printed_correct_given_supported_exact_payload','typed_correct_given_printed_exact')}
            stage[kind][name]['excluded_from_supported_payload_condition']=sum(r['diagnostic']['stage_metrics'][kind][name]['excluded_from_supported_payload_condition'] for r in records)
    return {'documents':len(records),'families':len({r['scores']['b0']['family_id'] for r in records}),
        'counts':{name:{metric:{key:sum(r['scores'][name][metric][key] for r in records) for key in ('correct','total')}
                       for metric in METRICS} for name in ('b0','mapping_v1')},'stage_metrics':stage,
        'nonexclusive_flags':{name:dict(Counter(flag for r in records for slot in r['diagnostic']['slots'] for flag in slot['mappers'][name]['evidence_flags_nonexclusive'])) for name in ('b0','mapping_v1')},
        'unit_evidence':{name:dict(Counter(slot['mappers'][name]['literal_unit']['status'] for r in records for slot in r['diagnostic']['slots'])) for name in ('b0','mapping_v1')},
        'identifier_evidence':{name:dict(Counter(str(slot['mappers'][name]['identifier_printed_exact']) for r in records for slot in r['diagnostic']['slots'] if slot['value_type']=='identifier')) for name in ('b0','mapping_v1')}}

def collect(out,return_commit):
    assert not out.exists() and not git('status','--porcelain').strip(),'Freeze helper; retain every attempt'
    head=git('rev-parse','HEAD').decode().strip();assert ident('HEAD','qualification/coverage_v1')==TREE
    git('merge-base','--is-ancestor',BASE,head)
    release=json.loads(obj(AUTHORITY,RELEASE));result=load(RUN/'run-result.json');scores=load(SCRATCH/'scores.json')
    assert result['release']==release and result['executing_head']==BASE
    assert scores['run_result_sha256']==sha((RUN/'run-result.json').read_bytes())
    assert load(SCRATCH/'completion.json')['supervisor_exit_code']==0
    assert load(SCRATCH/'score-execution.json')['exit_code']==0 and load(SCRATCH/'score-execution.json')['executing_head']==BASE
    assert load(SCRATCH/'cleanup-complete.json')['matching_count']==0
    assert len(result['calls'])==14 and sum(not c['excluded'] for c in result['calls'])==12
    assert all(c['status']=='completed' for c in result['calls']) and result['failure'] is None
    assert result['child_returncode']==0 and result['observed_child_exit'] and not result['finalization_errors']
    assert len(scores['records'])==12 and scores['diagnostic_pairing']['paired_comparisons']==9
    copied=[];retained=[];run_manifest=[]
    def copy_bytes(data,relative,origin):
        dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(data)
        assert dest.read_bytes()==data
        row={'source':origin,'destination':dest.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)};copied.append(row);return row
    for path in sorted(RUN.rglob('*')):
        assert not path.is_symlink() and not getattr(path.stat(),'st_file_attributes',0)&0x400,'Unexpected runtime reparse point'
        if not path.is_file():continue
        rel=path.relative_to(RUN);data=path.read_bytes();record={'run_relative_path':rel.as_posix(),'bytes':len(data),'sha256':sha(data)}
        if rel.parts[0] in CACHES:
            record.update(storage='retained_only_cache',published_path=None);retained.append({'source':str(path),**record})
        else:
            assert len(rel.parts)==1 or rel.parts[0]=='evidence',rel
            item=copy_bytes(data,'run/'+rel.as_posix(),str(path));record.update(storage='published_run_copy',published_path=item['destination'])
        run_manifest.append(record)
    for path in sorted(SCRATCH.iterdir()):
        assert path.is_file(),path
        copy_bytes(path.read_bytes(),'scores.json' if path.name=='scores.json' else 'launch/'+path.name,str(path))
    proofs=[{'commit':AUTHORITY,'path':RELEASE,'sha256':sha(obj(AUTHORITY,RELEASE))},release['source_review'],release['admission_review'],release['unseal'],*release['lease']['observations']]
    return_paths=git('ls-tree','-r','--name-only',return_commit,'--','docs/coordination/WP-0011/author-after').decode().splitlines()
    assert 'docs/coordination/WP-0011/author-after/lease-return.json' in return_paths,'Root return receipt missing'
    proofs += [{'commit':return_commit,'path':path,'sha256':sha(obj(return_commit,path))} for path in return_paths]
    for i,binding in enumerate(proofs):
        data=obj(binding['commit'],binding['path']);assert sha(data)==binding['sha256']
        copy_bytes(data,f"bindings/{i:02d}-{Path(binding['path']).name}",binding['commit']+':'+binding['path'])
    p=load(ROOT/'qualification/coverage_v1/protocol.json');inputs=[]
    for fx in p['fresh_fixtures']:
        for a in fx['artifacts']:
            path=p['publication_prefix']+a['sealed_relative_path'];data=(ROOT/path).read_bytes()
            assert len(data)==a['bytes'] and sha(data)==a['sha256'] and obj(release['corpus_commit'],path)==data
            inputs.append({'fixture_id':fx['fixture_id'],'path':path,'role':a['role'],'bytes':len(data),'sha256':sha(data),'git_blob':ident(release['corpus_commit'],path)})
    for fx in p['historical_warmups']:
        data=(ROOT/fx['file_path']).read_bytes();assert len(data)==fx['size_bytes'] and sha(data)==fx['sha256']
        inputs.append({'fixture_id':fx['fixture_id'],'path':fx['file_path'],'role':'excluded_warmup_pdf','bytes':len(data),'sha256':sha(data),'git_blob':ident(BASE,fx['file_path'])})
    observations=[]
    for c in result['calls']:
        obs=load(RUN/c['observation']);render=load(RUN/'evidence'/f"{c['fixture_id']}.{c['kind']}.render.json")
        for key in ('raw_output','token_ids_file'):
            data=(RUN/'evidence'/obs[key]['name']).read_bytes()
            assert len(data)==obs[key]['bytes_written'] and sha(data)==obs[key]['sha256_written'] and not obs[key]['truncated_by_writer']
        tokens=load(RUN/'evidence'/obs['token_ids_file']['name']);assert sha(json.dumps(tokens).encode())==obs['native']['token_ids_sha256']
        assert not obs['flags'] and obs['native']['finish_reason']=='stop'
        assert len(render['raster'])==obs['page_count_in']==obs['native']['num_pages_out']
        observations.append({**c,'native':obs['native'],'timing':obs['timing'],'host_memory':obs['host_memory'],'cuda_memory':obs['cuda_memory'],
            'render':render,'flags':obs['flags'],'raw':obs['raw_output'],'tokens':obs['token_ids_file']})
    assert [c['fixture_id'] for c in result['calls'] if not c['excluded']]==[r['fixture_id'] for r in scores['records']]
    documents=[];changes=[]
    for ri,r in enumerate(scores['records']):
        d=r['diagnostic'];b0=r['scores']['b0'];v1=r['scores']['mapping_v1']
        for metric in ('fields','normalized_fields'):
            for i,(left,right) in enumerate(zip(b0[metric]['details'],v1[metric]['details'])):
                assert left['key']==right['key']
                if left!=right:changes.append({'fixture_id':r['fixture_id'],'metric':metric,'score_pointer':f'/records/{ri}/scores','slot_ordinal':i,
                    'before':left,'after':right,'gain':right['credited_exact'] and not left['credited_exact'],'loss':left['credited_exact'] and not right['credited_exact']})
        documents.append({'fixture_id':r['fixture_id'],'condition':d['condition'],'family_id':d['family_id'],'completion':r['completion'],
            'score_pointer':f'/records/{ri}','raw_path':'run/evidence/'+r['fixture_id']+'.measured.raw.txt',
            'parse_errors':d['parse_errors'],'visibility_errors':d['visibility_errors'],'presence_denominator':d['presence_denominator'],
            'stage_metrics':d['stage_metrics'],'metrics':{name:{m:{k:v for k,v in r['scores'][name][m].items() if k!='details'} for m in METRICS} for name in ('b0','mapping_v1')},
            'text_metric':b0['text'],'absence_details':{name:r['scores'][name]['expected_absences']['details'] for name in ('b0','mapping_v1')},
            'mapping_coverage':{name:r['scores'][name]['mapping_coverage'] for name in ('b0','mapping_v1')},
            'ideal_control_reference_counterfactual':{name:{m:d['ideal_witness_scores'][name][m] for m in ('fields','cells','rows')} for name in ('b0','mapping_v1')},
            'accepted_right_neighbor_count':sum(f.get('association')=='immediate_right_neighbor' for f in r['predictions']['mapping_v1']['fields'])})
    summary={'source_commit':SOURCE,'source_tree':TREE,'executing_head':BASE,'collection_helper':head,'runtime_authority':AUTHORITY,
        'root_lease_return_commit':return_commit,'run':str(RUN),'documents':documents,'full_scores_path':(out/'scores.json').relative_to(ROOT).as_posix(),
        'overall':aggregate(scores['records']),'conditions':{c:aggregate([r for r in scores['records'] if r['diagnostic']['condition']==c]) for c in ('control','layout','vocabulary','degraded')},
        'historical_summary':scores['historical_summary'],'paired_conditions':scores['diagnostic_pairing'],'field_changes':changes,
        'gain_loss':{metric:{'gains':sum(x['gain'] for x in changes if x['metric']==metric),'losses':sum(x['loss'] for x in changes if x['metric']==metric)} for metric in ('fields','normalized_fields')},
        'calls':observations,'load':load(RUN/'evidence/load.json'),'runtime_elapsed_s':result['elapsed_s'],'child_returncode':result['child_returncode'],
        'observed_child_exit':result['observed_child_exit'],'final_observation_status':result['final_observation_status'],'observer_returncodes':[x['returncode'] for x in result['observers']],
        'limits':['Three matched families, not twelve independent generalization samples.','Fixed call order/time and desktop/WDDM activity confound latency and condition attribution.',
            'Exact visible expected-value presence is not complete OCR character accuracy or semantic association.','Repeated values remain ambiguous; table local row identity is separately recorded.',
            'Ideal native witnesses are reference-only support checks, not actual model output.','Typed quantities retain numeric-only historical semantics after supported-unit validation.',
            'Mapped absence violations and extra candidates are not comprehensive invention detection.','Single composite degradation severity and finite clean-layout set; no retries or source tuning.']}
    write(out/'analysis.json',summary)
    write(out/'run-copy-manifest.json',{'schema':'eld-coverage-run-copy/1','external_run':str(RUN),'run_prefix':(out/'run').relative_to(ROOT).as_posix(),
        'entries':run_manifest,'total_run_files':len(run_manifest),'published_run_files':sum(x['storage']=='published_run_copy' for x in run_manifest),
        'retained_only_files':len(retained),'note':'All run files covered. Cache files remain external and are inventoried, not published.'})
    write(out/'collection.json',{'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'helper_commit':head,'executing_head':BASE,'runtime_authority':AUTHORITY,
        'root_lease_return_commit':return_commit,'run':str(RUN),'copied_file_count':len(copied),'copied_files':copied,
        'retained_only_count':len(retained),'retained_only_bytes':sum(x['bytes'] for x in retained),'retained_only_files':retained,
        'empty_cache_directories':[n for n in sorted(CACHES) if not any((RUN/n).rglob('*'))],'inference_input_files':inputs,
        'checks':{'all_copied_bytes_match':True,'complete_run_file_manifest':True,'raw_token_render_bindings':True,'complete_fourteen_calls':True,'twelve_primary_nine_pairs':True}})
    print(json.dumps({'helper':head,'copied_files':len(copied),'retained_only_files':len(retained),'run_files':len(run_manifest),'inference_input_files':len(inputs),
        'overall':summary['overall'],'gain_loss':summary['gain_loss']},indent=2))

def verify(deliverable,out):
    assert not out.exists() and not git('status','--porcelain').strip() and git('rev-parse','HEAD').decode().strip()==deliverable
    before=tree_entries(BASE);after=tree_entries(deliverable);assert all(after.get(k)==v for k,v in before.items()),'Prior path changed'
    changed=[]
    for path in sorted(set(after)-set(before)):
        assert path.startswith(EV) or path.startswith(DOS),path
        data=obj(deliverable,path);local=(ROOT/path).read_bytes()
        if path.startswith(EV):assert data==local,'Evidence byte normalization'
        changed.append({'path':path,'git_blob':after[path][2],'bytes_git':len(data),'sha256_git':sha(data),'bytes_worktree':len(local),'sha256_worktree':sha(local)})
    collection=load(ROOT/EV/'attempt-1/collection.json')
    for row in collection['copied_files']:
        data=(ROOT/row['destination']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
        source=row['source'];original=obj(source[:40],source[41:]) if len(source)>41 and source[40]==':' else Path(source).read_bytes()
        assert original==data
    for row in collection['retained_only_files']:
        data=Path(row['source']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    for row in collection['inference_input_files']:
        data=(ROOT/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    manifest=load(ROOT/EV/'attempt-1/run-copy-manifest.json');assert {r['run_relative_path'] for r in manifest['entries']}=={p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file()}
    write(out,{'base':BASE,'source':SOURCE,'source_tree':TREE,'deliverable':deliverable,'collection_helper':collection['helper_commit'],
        'runtime_authority':AUTHORITY,'root_lease_return_commit':collection['root_lease_return_commit'],'changed_file_count':len(changed),'changed_files':changed,
        'unchanged_base_paths':len(before),'all_base_mode_type_blob_identities_unchanged':True,'all_evidence_git_bytes_exact':True,
        'all_copied_external_or_git_bytes_reverified':True,'all_retained_cache_and_input_hashes_reverified':True,'complete_run_manifest_reverified':True})
    print(json.dumps({'deliverable':deliverable,'added':len(changed),'unchanged_base_paths':len(before),'copied_reverified':len(collection['copied_files'])},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['collect','verify']);p.add_argument('--out',required=True);p.add_argument('--return-authority');p.add_argument('--deliverable');a=p.parse_args()
    out=(ROOT/a.out).resolve();out.relative_to(ROOT/(EV if a.mode=='collect' else DOS))
    if a.mode=='collect':collect(out,a.return_authority)
    else:verify(a.deliverable,out)
