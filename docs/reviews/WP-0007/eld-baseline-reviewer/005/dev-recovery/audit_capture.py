"""Independent immutable completed recovery capture audit; never opens recorded runtime paths."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path, PureWindowsPath

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import reproduce_v2 as r
AUTHORITY = '2ce3366d6aada92068088090bb026d4579b20e61'
RUN_AUTHORITY = '934d6a204bea0a61eb30c33a395b5c616dd00063'
EVIDENCE = '414b24d7a1752698fc9bb3bd95e06715b8ebb677'
PREFIX = 'docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca/'
PRIMARY_COMMIT = '1d6a681f09b0eaf233f838c54465c36a042ec326'
PRIMARY_PATH = 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6/scores.json'

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output',required=True); args = parser.parse_args()
    r.require(not r.git('status','--porcelain').strip(),'Freeze audit helper before execution')
    core = r.check_core(); read = r.GitBlobs(EVIDENCE)
    files = {p[len(PREFIX):]:read(p) for p in read.files if p.startswith(PREFIX)}
    def obj(name): return json.loads(files[name.replace('\\','/')])
    capture = obj('capture.json'); inventory = capture['files']
    r.require(len(inventory) == len({x['relative_path'] for x in inventory}) and {x['relative_path'] for x in inventory} == set(files)-{'capture.json'},'Incomplete/duplicate capture inventory')
    for item in inventory:
        data = files[item['relative_path']]
        r.require(item['path'] == PREFIX+item['relative_path'] and item['bytes'] == len(data) and item['sha256'] == r.sha(data),'Captured Git bytes/size/hash differ')
    for item in capture['protected_objects']:
        r.require(r.oid(EVIDENCE,item['path']) == r.oid('HEAD',item['path']) == item['object'],'Protected source/evidence object changed')
    result = obj('run-result.json'); release = result['release']; preflight = obj('evidence/preflight.json'); load = obj('evidence/load.json'); post = obj('author-model-after.json')
    r.require(capture['authority'] == post['authority'] == RUN_AUTHORITY and capture['source'] == release['source_commit'] == r.NEW_SOURCE and capture['accepted_review'] == release['accepted_review_commit'] == r.LINEAGES[r.NEW_SOURCE]['review'],'Capture source/review/authority differs')
    r.require(capture['scope'] == r.SUPPLEMENT_SCOPE and capture['supplemental_recovery'] == release['supplemental_recovery'] == r.RECOVERY_BINDING,'Supplement scope/lineage differs')
    r.require(preflight['release'] == release and capture['execute_exit_code'] == capture['score_exit_code'] == 0 and capture['no_retry'],'Capture/preflight completion differs')
    p = r.protocol(); manifest = r.load_json(r.ROOT/p['model_manifest_path'])
    models = []
    for stage,record in [('preflight',preflight),('post',post)]:
        model = {x['path']:x for x in record['model']['files']}
        r.require(set(model) == {x['path'] for x in manifest['files']},'Model object set differs')
        for expected in manifest['files']:
            actual = model[expected['path']]; digest = 'sha256' if expected['digest_kind'] == 'lfs_sha256' else 'git_blob_sha1'
            r.require(actual['ok'] and actual['size'] == expected['size'] and actual[digest] == expected[digest],'Archived model identity differs')
        notices = {x['path']:x for x in record['notice']['notices']}
        for expected in manifest['notices']:
            actual = notices[expected['path']]
            r.require(actual['ok'] and actual['size'] == expected['size'] and actual['git_blob_sha1'] == expected['git_blob_sha1'],'Archived notice identity differs')
        models.append(model)
    r.require(models[0] == models[1],'Pre/post archived model records differ')
    for item in load['module_cache']['modules']:
        r.require(item['identical'] and item['cache_sha256'] == item['model_sha256'] == models[0][item['file']]['sha256'],'Loaded module cache differs')
    r.require(all(x['payload_ok'] and x['metadata']['ok'] and x['metadata']['requires_match'] for x in preflight['wheels']['wheels']),'Archived wheel check failed')
    r.require(preflight['renderer']['distribution_version'] == p['renderer']['version'] and p['renderer']['pdfium_version'] in preflight['renderer']['PDFIUM_INFO'],'Renderer identity differs')
    fixtures = {f['fixture_id']:f for f in p['fixtures'] if f['split'] == 'dev'}; renders = []; observations = []
    r.validate_calls(result,p,release)
    for call in result['calls']:
        f = fixtures[call['fixture_id']]; name = f['fixture_id']+'.'+call['kind']; render = obj('evidence/'+name+'.render.json'); obs = obj(call['observation'])
        r.require(call['status'] == 'completed' and not obs.get('flags') and not obs.get('error'),'Unexpected incomplete recovery call')
        r.require(render['pdf_sha256'] == f['sha256'] and [x['page'] for x in render['raster']] == list(range(1,f['page_count']+1)),'Input digest/page order differs')
        r.require(all(x['width'] > 0 and x['height'] > 0 and re.fullmatch('[0-9a-f]{64}',x['rgb_sha256']) for x in render['raster']),'Raster record malformed')
        r.require(all(x['starts'] == 0 for x in obs['targets'].values() if x['role'] in ('forbidden_save_path','forbidden_eval_site')),'Forbidden native site entered')
        renders.append({'call':name,**render}); observations.append({'call':name,**{key:obs[key] for key in ('native','timing','cuda_memory','host_memory','prefill_memory','kernel_path','page_markers')}})
    observers = []
    for item in result['observers']:
        name = PureWindowsPath(item['path']).name
        r.require(item['returncode'] == 0 and item['bytes'] == len(files[name]),'Archived observer result differs')
        observers.append({'tag':item['tag'],'index':item['index'],'bytes':len(files[name]),'sha256':r.sha(files[name])})
    events = [json.loads(line) for line in files['evidence/events.jsonl'].splitlines()]
    expected_phases = ['preflight','load'] + [phase for c in result['calls'] for phase in ('render:'+c['fixture_id'],'call:'+c['fixture_id']+'.'+c['kind'])]
    r.require([x['phase'] for x in events] == expected_phases,'Phase transcript differs')
    outcome = obj('evidence/worker-outcome.json'); heartbeat = obj('heartbeat.json'); start = obj('author-process-start.json'); receipt = obj('author-process-exit-and-lease-return.json')
    r.require(outcome['failure'] is None and outcome['no_retry'] and outcome['active_call'] == r.RECOVERY_BINDING['fixture_id']+'.measured','Worker outcome differs')
    r.require(heartbeat['phase'] == 'finished' and heartbeat['pid'] == outcome['worker_pid'] == preflight['worker_pid'],'Worker/heartbeat/preflight identity differs')
    processes = {x['ProcessId']:x for x in start['processes']}; worker = processes[outcome['worker_pid']]; launcher = processes[result['child_launcher_pid']]
    r.require(worker['ParentProcessId'] == launcher['ProcessId'] and launcher['ParentProcessId'] in processes,'Archived process chain differs')
    r.require(receipt['authority'] == start['authority'] == RUN_AUTHORITY and receipt['lease_id'] == start['lease_id'] == release['lease_id'] and receipt['run'] == start['run'] == result['run'],'Archived lease/run identity differs')
    r.require(receipt['lease_returned'] and not receipt['observed_owned_processes'] and receipt['supervisor_exit_code'] == receipt['score_exit_code'] == receipt['model_notice_verify_exit_code'] == 0,'Archived exit/lease return incomplete')
    r.require(result['failure'] is None and result['supervisor_error'] is None and not result['secondary_errors'] and not result['finalization_errors'] and all(x == 'available' for x in result['final_observation_status'].values()) and result['child_returncode'] == 0 and result['observed_child_exit'],'Runtime/finalization did not complete')
    primary = capture['original_primary_score']; r.require(primary['commit'] == PRIMARY_COMMIT and primary['path'] == PRIMARY_PATH and primary['still_primary'],'Primary lineage changed')
    old = r.GitBlobs(PRIMARY_COMMIT); primary_bytes = old(PRIMARY_PATH)
    r.require(primary['sha256'] == r.sha(primary_bytes) and r.oid(PRIMARY_COMMIT,PRIMARY_PATH) == r.oid(EVIDENCE,PRIMARY_PATH) == r.oid('HEAD',PRIMARY_PATH),'Original thirteen-document primary result changed')
    scores = obj('scores.json'); proof = r.load_json(Path(__file__).with_name('reproduction.json'))
    r.require(scores == proof['reproduced'] and proof['same_code_score_reproduction_equal'] and proof['independent_numeric_accounting_passed'],'Published score envelope differs from frozen independent reproduction')
    score = scores['scores'][0]; exact = {}
    for key in ('fields','cells','normalized_fields','normalized_cells'):
        exact[key] = {'credited':score[key]['correct'],'total':score[key]['total'],'observed_exact_uncredited':sum(bool(x['observed_exact']) and not x['credited_exact'] for x in score[key]['details'])}
        r.require(exact[key]['credited'] == 0 and exact[key]['observed_exact_uncredited'] == capture['raw_observed_exact_uncredited'][key],'Parser-gated/candidate counts differ')
    measured = result['calls'][-1]; measured_obs = obj(measured['observation']); raw = files['evidence/'+measured_obs['raw_output']['name']].decode('utf-8')
    pages = raw.split('<PAGE>'); r.require(len(pages) == 4,'Unexpected raw page markers')
    spans = re.findall(r'(?:rowspan|colspan)="[^"]+"',pages[3]); r.require(spans == capture['page3_span_attributes'],'Captured page-three span diagnostic differs')
    r.require(score['parse_errors'] == ['page_3:table:unsupported_span'] and not score['eligible_for_exact_credit'] and score['completion'] == 'completed','Whole-document parser gate differs')
    env_keys = []
    def walk_keys(value,path):
        if isinstance(value,dict):
            for key,item in value.items():
                if re.search(r'(^|_)(env|environment|environ)(_|$)',key,re.I): env_keys.append(path+'/'+key)
                walk_keys(item,path+'/'+key)
        elif isinstance(value,list):
            for i,item in enumerate(value): walk_keys(item,path+'/'+str(i))
    for name,data in files.items():
        if name.endswith('.json'): walk_keys(json.loads(data),name)
    report = {'authority':AUTHORITY,'audit_helper_head':r.git('rev-parse','HEAD').decode().strip(),'author_evidence':EVIDENCE,'source':r.NEW_SOURCE,'tree':r.LINEAGES[r.NEW_SOURCE]['tree'],'all_checks_passed':True,
        'capture_entries_verified':len(inventory),'published_files_read':len(files),'immutable_artifacts_read':read.reads+old.reads,'core':core,
        'archived_preflight':{'model_objects':len(models[0]),'notice_objects':len(post['notice']['notices']),'wheel_records':len(preflight['wheels']['wheels']),'installed':preflight['installed'],'renderer':preflight['renderer'],'module_cache_copies':len(load['module_cache']['modules'])},
        'load':load,'renders':renders,'observations':observations,'observers':observers,'events':events,'worker_outcome':outcome,'heartbeat':heartbeat,'exit_receipt':receipt,
        'parser_gate':{'completion':score['completion'],'parse_errors':score['parse_errors'],'eligible_for_exact_credit':score['eligible_for_exact_credit'],'exact_metrics':exact,'mapping_coverage':score['mapping_coverage'],'text':score['text'],'page3_span_attributes':spans},
        'environment_snapshot':{'matching_archived_key_paths':env_keys,'complete_per_child_environment_name_snapshot':'absent; command lines and accepted launch/audit source do not substitute for a retained per-child name snapshot'},
        'original_primary_sha256':r.sha(primary_bytes),'stderr':files['stderr.txt'].decode(errors='replace'),
        'limits':'Immutable completed dev-recovery capture only. Archived native timings, model/environment verification, render hashes and process/lease observations were not freshly measured. Full score reproduction uses the frozen accepted scorer without repair. Zero exact credit is whole-document parser gating, not evidence that every readable token/candidate was wrong. No external runtime, live/heldout data or GPU/model access.'}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out: json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'passed':True,'capture_entries':len(inventory),'files':len(files),'environment_keys':env_keys,'observed_exact_uncredited':capture['raw_observed_exact_uncredited']}))

if __name__ == '__main__': main()
