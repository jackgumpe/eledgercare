"""Frozen CPU-only collection/verification of the one released author run; no inference."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
BASE='2a3781745cb120f6e3eb22b234c111241ba8d8c9'
SOURCE='23e023045b335540d830ce01b75be247552a63f1'
TREE='59f66d0d3d9be145a43efcc9258eb260d3ef2f00'
AUTHORITY='6343ded1cd79b7c5b67b34893fe4516dc6845eb9'
RETURN='70d45a144f44b74e562c1dbe8fdcea16662e970b'
RELEASE='docs/coordination/WP-0009/releases/author.json'
RUN=Path('C:/Users/jackg/eLedgerCare-Mapping/WP-0009/author/runs/author/20261116T205320Z-67b42d6e')
SCRATCH=ROOT/'.scratch/wp0009-mapping/007-launch'
EV='docs/evidence/WP-0009/eld-mapping-author/007/'
DOS='docs/research/WP-0009/eld-mapping-author/fresh-comparison/'
CACHES={'cuda-cache','hf-home','hf-modules','home','inductor-cache','tmp','torch-home'}


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads(path.read_bytes())
def obj(rev,path):return git('show',rev+':'+path)
def ident(rev,path):return git('rev-parse',rev+':'+path).decode().strip()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
def blobs(rev):
    return {row.split('\t')[1]:row.split('\t')[0].split()[2] for row in git('ls-tree','-r',rev).decode().splitlines()}


def collect(out):
    assert not out.exists(),'Retain every collection attempt'
    assert not git('status','--porcelain').strip(),'Freeze collection helper first'
    head=git('rev-parse','HEAD').decode().strip()
    assert ident('HEAD','qualification/mapping_v1')==TREE
    git('merge-base','--is-ancestor',BASE,head)
    release=json.loads(obj(AUTHORITY,RELEASE));result=load(RUN/'run-result.json');scores=load(SCRATCH/'scores.json')
    assert result['release']==release and result['executing_head']==BASE
    assert scores['run_result_sha256']==sha((RUN/'run-result.json').read_bytes())
    assert load(SCRATCH/'exit.json')['exit']==0 and load(SCRATCH/'score-execution.json')['exit']==0
    assert load(SCRATCH/'score-execution.json')['executing_head']==BASE
    assert load(SCRATCH/'cleanup.json')['matching_count']==0
    assert len(result['calls'])==6 and sum(not c['excluded'] for c in result['calls'])==4
    assert all(c['status']=='completed' for c in result['calls']) and result['failure'] is None
    copied=[];retained=[]
    def copy(path,relative,origin=None):
        data=path.read_bytes();dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        assert dest.read_bytes()==data
        copied.append({'source':origin or str(path),'destination':dest.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)})
    for path in sorted(RUN.rglob('*')):
        assert not path.is_symlink(),'Unexpected runtime link'
        if not path.is_file():continue
        relative=path.relative_to(RUN)
        if relative.parts[0] in CACHES:
            data=path.read_bytes();retained.append({'path':str(path),'relative_path':relative.as_posix(),'bytes':len(data),'sha256':sha(data),'reason':'Retained task-local cache; not inference evidence'})
        else:
            assert len(relative.parts)==1 or relative.parts[0]=='evidence',relative
            copy(path,'run/'+relative.as_posix())
    for path in sorted(SCRATCH.iterdir()):
        assert path.is_file(),path
        copy(path,'scores.json' if path.name=='scores.json' else 'launch/'+path.name)
    proofs=[{'commit':AUTHORITY,'path':RELEASE,'sha256':sha(obj(AUTHORITY,RELEASE))},release['source_review'],release['admission_review'],release['unseal'],*release['lease']['observations']]
    for path in git('ls-tree','-r','--name-only',RETURN,'--','docs/coordination/WP-0009/author-after').decode().splitlines():
        proofs.append({'commit':RETURN,'path':path,'sha256':sha(obj(RETURN,path))})
    for i,binding in enumerate(proofs):
        data=obj(binding['commit'],binding['path']);assert sha(data)==binding['sha256']
        dest=out/'bindings'/f"{i:02d}-{Path(binding['path']).name}";dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        copied.append({'source':binding['commit']+':'+binding['path'],'destination':dest.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':sha(data)})
    protocol=load(ROOT/'qualification/mapping_v1/protocol.json');inputs=[]
    for fixture in protocol['fresh_fixtures']:
        for artifact in fixture['artifacts']:
            path=protocol['publication_prefix']+artifact['sealed_relative_path'];data=(ROOT/path).read_bytes()
            assert len(data)==artifact['bytes'] and sha(data)==artifact['sha256']
            assert obj(release['corpus_commit'],path)==data
            inputs.append({'path':path,'role':artifact['role'],'bytes':len(data),'sha256':sha(data),'git_blob':ident(release['corpus_commit'],path)})
    observations=[]
    for call in result['calls']:
        obs=load(RUN/call['observation']);render=load(RUN/'evidence'/f"{call['fixture_id']}.{call['kind']}.render.json")
        for key in ('raw_output','token_ids_file'):
            data=(RUN/'evidence'/obs[key]['name']).read_bytes()
            assert sha(data)==obs[key]['sha256_written'] and len(data)==obs[key]['bytes_written']
            assert not obs[key]['truncated_by_writer']
        tokens=load(RUN/'evidence'/obs['token_ids_file']['name'])
        assert sha(json.dumps(tokens).encode())==obs['native']['token_ids_sha256']
        assert not obs['flags'] and obs['native']['finish_reason']=='stop'
        assert len(render['raster'])==obs['page_count_in']==obs['native']['num_pages_out']
        observations.append({'fixture_id':call['fixture_id'],'kind':call['kind'],'excluded':call['excluded'],'status':call['status'],
            'native':obs['native'],'timing':obs['timing'],'host_memory':obs['host_memory'],'cuda_memory':obs['cuda_memory'],
            'render':render,'flags':obs['flags'],'raw':obs['raw_output'],'tokens':obs['token_ids_file']})
    assert [c['fixture_id'] for c in result['calls'] if not c['excluded']]==[r['fixture_id'] for r in scores['records']]
    documents=[];gain=loss=typed_gain=typed_loss=0
    for record in scores['records']:
        b0=record['scores']['b0'];v1=record['scores']['mapping_v1'];changes=[]
        for metric in ('fields','normalized_fields'):
            for left,right in zip(b0[metric]['details'],v1[metric]['details']):
                assert left['key']==right['key']
                won=int(right['credited_exact'] and not left['credited_exact']);lost=int(left['credited_exact'] and not right['credited_exact'])
                if metric=='fields':gain+=won;loss+=lost
                else:typed_gain+=won;typed_loss+=lost
                if left!=right:changes.append({'metric':metric,'before':left,'after':right})
        metrics={key:{k:v for k,v in b0[key].items() if k!='details'} for key in ('fields','cells','normalized_fields','normalized_cells','rows','expected_absences','page_count','page_sentinels','adjacency','cross_page_links','text')}
        documents.append({'fixture_id':record['fixture_id'],'family_id':b0['family_id'],'completion':record['completion'],
            'scores_identical':b0==v1,'predictions_identical':record['predictions']['b0']==record['predictions']['mapping_v1'],
            'metrics_b0':metrics,'mapping_coverage':b0['mapping_coverage'],'field_changes':changes,
            'predicted_fields':record['predictions']['mapping_v1']['fields'],'expected_absence_details':b0['expected_absences']['details'],
            'accepted_right_neighbor_count':sum(f.get('association')=='immediate_right_neighbor' for f in record['predictions']['mapping_v1']['fields'])})
    summary={'source_commit':SOURCE,'executing_head':BASE,'collection_helper':head,'runtime_authority':AUTHORITY,'lease_return_receipt':RETURN,'run':str(RUN),
        'full_scores_path':(out/'scores.json').relative_to(ROOT).as_posix(),'documents':documents,'original_summary':scores['summary'],
        'field_gains':gain,'field_losses':loss,'typed_field_gains':typed_gain,'typed_field_losses':typed_loss,
        'calls':observations,'load':load(RUN/'evidence/load.json'),'runtime_elapsed_s':result['elapsed_s'],
        'child_returncode':result['child_returncode'],'observed_child_exit':result['observed_child_exit'],
        'observer_returncodes':[o['returncode'] for o in result['observers']],
        'limits':['Four clean digital families; no mapping changes after exposure.','Same raw output; no model recognition/latency treatment.',
                  'Text metric is SequenceMatcher token alignment, not character accuracy or minimum Levenshtein WER.',
                  'Unmatched candidates/unmapped prose are not automatically factual hallucinations; absent fields remain unverified when unmapped.',
                  'Quantity normalization compares numeric values after unit validation; host peaks are sampled lower bounds and WDDM device memory includes desktop sharing.']}
    write(out/'analysis.json',summary)
    write(out/'collection.json',{'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'helper_commit':head,'executing_head':BASE,
        'runtime_authority':AUTHORITY,'run':str(RUN),'copied_file_count':len(copied),'copied_bytes':sum(f['bytes'] for f in copied),
        'copied_files':copied,'retained_only_count':len(retained),'retained_only_bytes':sum(f['bytes'] for f in retained),'retained_only_files':retained,
        'empty_cache_directories':[name for name in sorted(CACHES) if not any((RUN/name).rglob('*'))],
        'fresh_input_files':inputs,'checks':{'all_copied_bytes_match':True,'raw_token_render_bindings_pass':True,'complete_six_call_schedule':True,'four_primary_denominators':True}})
    print(json.dumps({'helper':head,'copied_files':len(copied),'retained_cache_files':len(retained),'fresh_input_files':len(inputs),'field_gains':gain,'field_losses':loss,'typed_field_gains':typed_gain,'typed_field_losses':typed_loss},indent=2))


def verify(deliverable,out):
    assert not out.exists() and not git('status','--porcelain').strip()
    assert git('rev-parse','HEAD').decode().strip()==deliverable
    before=blobs(BASE);after=blobs(deliverable)
    assert all(after.get(path)==blob for path,blob in before.items()),'Prior file changed'
    changed=[]
    for path in sorted(set(after)-set(before)):
        assert path.startswith(EV) or path.startswith(DOS),path
        data=obj(deliverable,path);local=(ROOT/path).read_bytes()
        if path.startswith(EV):assert data==local,'Evidence Git normalization'
        changed.append({'path':path,'git_blob':after[path],'published_bytes':len(data),'published_sha256':sha(data),'worktree_bytes':len(local),'worktree_sha256':sha(local)})
    collection=load(ROOT/EV/'attempt-1/collection.json')
    for entry in collection['copied_files']:
        local=(ROOT/entry['destination']).read_bytes();assert len(local)==entry['bytes'] and sha(local)==entry['sha256']
        if ':' in entry['source'] and entry['source'][:40].isalnum() and len(entry['source'].split(':',1)[0])==40:
            rev,path=entry['source'].split(':',1);original=obj(rev,path)
        else:original=Path(entry['source']).read_bytes()
        assert original==local,entry['source']
    for entry in collection['retained_only_files']:
        data=Path(entry['path']).read_bytes();assert len(data)==entry['bytes'] and sha(data)==entry['sha256']
    for entry in collection['fresh_input_files']:
        data=(ROOT/entry['path']).read_bytes();assert len(data)==entry['bytes'] and sha(data)==entry['sha256']
    write(out,{'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':BASE,'source':SOURCE,'source_tree':TREE,
        'deliverable':deliverable,'collection_helper':collection['helper_commit'],'runtime_authority':AUTHORITY,
        'changed_file_count':len(changed),'changed_files':changed,'protected_file_count':len(before),'protected_files':[{'path':p,'git_blob':v} for p,v in before.items()],
        'checks':{'all_base_files_identical':True,'all_published_evidence_bytes_exact':True,'all_copied_external_or_git_bytes_still_identical':True,
                  'all_retained_cache_hashes_verified':True,'all_20_fresh_input_hashes_verified':True}})
    print(json.dumps({'deliverable':deliverable,'changed':len(changed),'protected':len(before),'copied_reverified':len(collection['copied_files'])},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['collect','verify']);parser.add_argument('--out',required=True);parser.add_argument('--deliverable')
    args=parser.parse_args();out=(ROOT/args.out).resolve();out.relative_to(ROOT/EV if args.mode=='collect' else ROOT/DOS)
    if args.mode=='collect':collect(out)
    else:verify(args.deliverable,out)
