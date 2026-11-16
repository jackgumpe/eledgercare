"""Frozen completed heldout sentinel capture audit and honest author comparison; no model imports."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path, PureWindowsPath

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import reproduce_v2 as r

AUTHORITY = 'e135ef5b69a96d3f509e86171f70f4724fcc0695'
EXECUTING_HEAD = '7b4be52d51194e94ee0bd3b4137d4f36e4102d29'
PREFIX = 'docs/reviews/WP-0007/eld-baseline-reviewer/005/runtime-heldout/20261116T164236Z-34d7b740/'
AUTHOR = 'a2fd6d872f973635e25be123da44a9e34ba029cd'
AUTHOR_PREFIX = 'docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d/'
SENTINELS = ['SYN-INV-03-v1-raster300','SYN-MP-02-v0-clean']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence-commit',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    r.require(not r.git('status','--porcelain').strip(),'Freeze comparison helper and proof before execution')
    core=r.check_core();p=r.protocol();read=r.GitBlobs(args.evidence_commit)
    r.require(r.oid(args.evidence_commit,PREFIX+'verify_sentinels.py')==r.oid('HEAD',PREFIX+'verify_sentinels.py'),'Comparison helper changed since capture freeze')
    files={path[len(PREFIX):]:read(path) for path in read.files if path.startswith(PREFIX)}
    def obj(name):return json.loads(files[name.replace('\\','/')])
    capture=obj('capture.json');copies=capture['copies'];copied={x['relative_path'] for x in copies}
    r.require(len(copies)==len(copied)==capture['copy_count']==60 and set(files)==copied|{'capture.json','runtime-commands.json','verify_sentinels.py'},'Incomplete/duplicated capture inventory')
    r.require(sum(x['bytes'] for x in copies)==capture['copy_bytes'],'Capture byte count differs')
    for entry in copies:
        data=files[entry['relative_path']]
        r.require(entry['path']==PREFIX+entry['relative_path'] and len(data)==entry['bytes'] and r.sha(data)==entry['sha256'],'Capture byte/hash mismatch')
    authority=r.GitBlobs(AUTHORITY);release=json.loads(authority('docs/coordination/WP-0007/releases/reviewer-heldout.json'))
    for entry in release['observed_gpu_state'].values():r.require(r.sha(authority(entry['path']))==entry['sha256'],'Release observation digest differs')
    result=obj('run-result.json');pre=obj('evidence/preflight.json');post=obj('reviewer-model-after.json');load=obj('evidence/load.json');proof=r.load_json(Path(__file__).with_name('reproduction.json'))
    r.require(result['release']==pre['release']==release and result['executing_head']==capture['executing_head']==EXECUTING_HEAD,'Runtime release/HEAD differs')
    r.require(capture['authority']==AUTHORITY and capture['source']==r.NEW_SOURCE and capture['tree']==r.LINEAGES[r.NEW_SOURCE]['tree'] and capture['accepted_review']==r.LINEAGES[r.NEW_SOURCE]['review'],'Source/acceptance differs')
    r.require(proof['binding']['evidence_commit']==args.evidence_commit and proof['binding']['original_authority']==AUTHORITY and proof['binding']['owner']=='reviewer' and proof['binding']['split']=='eval_holdout' and proof['same_code_score_reproduction_equal'] and proof['independent_numeric_accounting_passed'] and proof['reproduced']==obj('scores.json'),'Frozen raw-score reproduction differs')
    r.validate_calls(result,p,release)
    r.require([c['fixture_id'] for c in result['calls'] if not c['excluded']]==SENTINELS and len(result['calls'])==4 and all(c['status']=='completed' for c in result['calls']),'Fixed sentinel matrix/completion differs')
    manifest=r.load_json(r.ROOT/p['model_manifest_path']);models=[]
    for record in (pre,post):
        model={x['path']:x for x in record['model']['files']};r.require(len(model)==len(record['model']['files'])==len(manifest['files']) and set(model)=={x['path'] for x in manifest['files']},'Model set differs')
        for expected in manifest['files']:
            actual=model[expected['path']];digest='sha256' if expected['digest_kind']=='lfs_sha256' else 'git_blob_sha1'
            r.require(actual['ok'] and actual['size']==expected['size'] and actual[digest]==expected[digest],'Model identity differs')
        notices={x['path']:x for x in record.get('notice',record.get('notices'))['notices']};r.require(set(notices)=={x['path'] for x in manifest['notices']},'Notice set differs')
        for expected in manifest['notices']:
            actual=notices[expected['path']];r.require(actual['ok'] and actual['size']==expected['size'] and actual['git_blob_sha1']==expected['git_blob_sha1'],'Notice identity differs')
        models.append(model)
    r.require(models[0]==models[1],'Pre/post model records differ')
    for entry in load['module_cache']['modules']:r.require(entry['identical'] and entry['cache_sha256']==entry['model_sha256']==models[0][entry['file']]['sha256'],'Module cache differs')
    r.require(all(x['payload_ok'] and x['metadata']['ok'] and x['metadata']['requires_match'] for x in pre['wheels']['wheels']),'Wheel check failed')
    r.require(pre['renderer']['distribution_version']==p['renderer']['version'] and p['renderer']['pdfium_version'] in pre['renderer']['PDFIUM_INFO'],'Renderer differs')
    fixtures={f['fixture_id']:f for f in p['fixtures']};renders=[];observations=[]
    for call in result['calls']:
        f=fixtures[call['fixture_id']];obs=obj(call['observation']);render=obj('evidence/'+f['fixture_id']+'.'+call['kind']+'.render.json')
        r.require(render['pdf_sha256']==f['sha256'] and [x['page'] for x in render['raster']]==list(range(1,f['page_count']+1)) and all(re.fullmatch('[0-9a-f]{64}',x['rgb_sha256']) and x['width']>0 and x['height']>0 for x in render['raster']),'Render identity/pages differ')
        r.require(obs['native']['finish_reason']=='stop' and not obs['flags'] and not obs.get('error') and all(x['starts']==0 for x in obs['targets'].values() if x['role'] in ('forbidden_save_path','forbidden_eval_site')),'Native completion/guard differs')
        observations.append({'call':f['fixture_id']+'.'+call['kind'],'excluded':call['excluded'],**{k:obs[k] for k in ('native','timing','cuda_memory','host_memory','prefill_memory','kernel_path','page_markers')}});renders.append(render)
    for entry in result['observers']:r.require(entry['returncode']==0 and entry['bytes']==len(files[PureWindowsPath(entry['path']).name]),'Observer record differs')
    events=[json.loads(line) for line in files['evidence/events.jsonl'].splitlines()]
    r.require([x['phase'] for x in events]==['preflight','load']+[phase for c in result['calls'] for phase in ('render:'+c['fixture_id'],'call:'+c['fixture_id']+'.'+c['kind'])],'Phase sequence differs')
    start=obj('reviewer-process-start.json');receipt=obj('reviewer-process-exit-and-lease-return.json');outcome=obj('evidence/worker-outcome.json');heartbeat=obj('heartbeat.json')
    processes={x['ProcessId']:x for x in start['processes']};worker=processes[outcome['worker_pid']];launcher=processes[result['child_launcher_pid']]
    r.require(worker['ParentProcessId']==launcher['ProcessId'] and launcher['ParentProcessId'] in processes and {x['ProcessId'] for x in receipt['recorded_process_identities']}==set(processes),'Process lineage differs')
    r.require(receipt['authority']==start['authority']==AUTHORITY and receipt['lease_id']==start['lease_id']==release['lease_id'] and receipt['run']==start['run']==result['run']==capture['run'],'Lease/run binding differs')
    r.require(receipt['executing_head']==EXECUTING_HEAD and receipt['lease_returned'] and receipt['no_retry'] and not receipt['remaining_processes'] and not receipt['worktree_porcelain'] and receipt['execute_exit_code'] is None and receipt['execute_exit_limitation'] and receipt['observed_child_exit'] and receipt['child_returncode']==receipt['score_exit_code']==receipt['model_notice_verify_exit_code']==0,'Exit/return receipt incomplete')
    r.require(outcome['failure'] is None and outcome['no_retry'] and outcome['active_call']==SENTINELS[-1]+'.measured' and heartbeat['phase']=='finished' and heartbeat['pid']==outcome['worker_pid']==pre['worker_pid'],'Worker completion differs')
    r.require(result['failure'] is None and result['supervisor_error'] is None and not result['secondary_errors'] and not result['finalization_errors'] and all(v=='available' for v in result['final_observation_status'].values()) and result['observed_child_exit'] and result['child_returncode']==0,'Runtime finalization incomplete')
    author=r.GitBlobs(AUTHOR);author_result=json.loads(author(AUTHOR_PREFIX+'run-result.json'));author_packet=json.loads(author(AUTHOR_PREFIX+'scores.json'));comparisons=[]
    for call in result['calls']:
        prior=next(c for c in author_result['calls'] if (c['fixture_id'],c['kind'])==(call['fixture_id'],call['kind']))
        current=obj(call['observation']);previous=json.loads(author(AUTHOR_PREFIX+prior['observation'].replace('\\','/')))
        current_raw=files['evidence/'+current['raw_output']['name']];previous_raw=r.retained(author,AUTHOR_PREFIX.rstrip('/')+'/evidence',previous['raw_output'])
        current_tokens=json.loads(files['evidence/'+current['token_ids_file']['name']]);previous_tokens=json.loads(r.retained(author,AUTHOR_PREFIX.rstrip('/')+'/evidence',previous['token_ids_file']))
        r.require(r.sha(json.dumps(previous_tokens).encode())==previous['native']['token_ids_sha256'] and len(previous_tokens)==previous['native']['output_tokens'],'Author native token binding differs')
        comparisons.append({'fixture_id':call['fixture_id'],'kind':call['kind'],'excluded':call['excluded'],'raw_equal':current_raw==previous_raw,'reviewer_raw_sha256':r.sha(current_raw),'author_raw_sha256':r.sha(previous_raw),'reviewer_raw_bytes':len(current_raw),'author_raw_bytes':len(previous_raw),'token_ids_equal':current_tokens==previous_tokens,'reviewer_output_tokens':len(current_tokens),'author_output_tokens':len(previous_tokens),'first_token_difference':next((i for i,(a,b) in enumerate(zip(current_tokens,previous_tokens)) if a!=b),min(len(current_tokens),len(previous_tokens)) if len(current_tokens)!=len(previous_tokens) else None),'reviewer_external_wall_s':current['timing']['external_synchronized_wall_s']['value'],'author_external_wall_s':previous['timing']['external_synchronized_wall_s']['value']})
    score_comparisons=[]
    for score in obj('scores.json')['scores']:
        prior_score=next(s for s in author_packet['scores'] if s['fixture_id']==score['fixture_id'])
        score_comparisons.append({'fixture_id':score['fixture_id'],'equal':score==prior_score,'different_top_level_keys':[k for k in sorted(set(score)|set(prior_score)) if score.get(k)!=prior_score.get(k)],'reviewer_score':score,'author_score_sha256':r.sha(json.dumps(prior_score,sort_keys=True).encode()),'reviewer_score_sha256':r.sha(json.dumps(score,sort_keys=True).encode())})
    report={'authority':AUTHORITY,'reviewer_execution_head':EXECUTING_HEAD,'capture_helper_freeze':args.evidence_commit,'comparison_head':r.git('rev-parse','HEAD').decode().strip(),'source':r.NEW_SOURCE,'tree':r.LINEAGES[r.NEW_SOURCE]['tree'],'core':core,'capture_entries_verified':len(copies),'captured_bytes':capture['copy_bytes'],'all_integrity_checks_passed':True,'comparisons':comparisons,'measured_score_comparisons':score_comparisons,'primary_author_packet_unchanged':r.sha(author(AUTHOR_PREFIX+'scores.json'))=='d0c1abdea5f603c8e34ae538aa26fba892d63388986d2ca785725a460526ecc8','observations':observations,'renders':renders,'load':load,'preflight_counts':{'model_objects':len(models[0]),'notice_objects':len(manifest['notices']),'wheel_records':len(pre['wheels']['wheels']),'module_cache_copies':len(load['module_cache']['modules'])},'observer_count':len(result['observers']),'events':events,'final_observation_status':result['final_observation_status'],'worker_outcome':outcome,'heartbeat':heartbeat,'lease_return':receipt,'immutable_artifacts_read':read.reads+authority.reads+author.reads,'stderr':files['stderr.txt'].decode(errors='replace'),'limits':['Actual fixed independent runtime: two excluded warmups and two measured heldout sentinels, no retries. Original execute tool exit is unavailable after usage interruption; recorded child exit0 and process absence are proven.','Comparisons record equality or difference without selecting attempts or altering source; reviewer result does not replace or join author primary scores.','Timing/memory are descriptive independent attempts, not paired performance or a distribution; shared CPU/RAM, desktop WDDM, observer overhead and OS caches remain confounders.','Complete actual per-child environment-name snapshot absent; local torchvision SHA256 TOFU provenance remains.','This verification helper is CPU-only and reads immutable Git evidence, not live processes, external runtime paths or model files.']}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'integrity_passed':True,'captured_files':len(copies),'raw_equal':[x['raw_equal'] for x in comparisons],'tokens_equal':[x['token_ids_equal'] for x in comparisons],'measured_scores_equal':[x['equal'] for x in score_comparisons]}))


if __name__=='__main__':main()
