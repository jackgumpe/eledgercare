"""Frozen, Git-only heldout capture and primary consolidation audit. No inference."""
from __future__ import annotations
import argparse, collections, json, re, sys
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reproduce_v2 as r

AUTHORITY = '542bd4f0045adba256637d4b237dc92fc5cae7d4'
RUN_AUTHORITY = '2ce3366d6aada92068088090bb026d4579b20e61'
BASE = '9a8ae5293899d3f17b5cd240c29ce43270e93e2d'
RAW = 'a2fd6d872f973635e25be123da44a9e34ba029cd'
DELIVERABLE = '9dd4d0d8317253e929c324201cc0760b75619fe4'
PUBLICATION = 'd1858bec883ab4066ae6a05096ed4bf3c85230e3'
PREFIX = 'docs/evidence/WP-0007/eld-rd-astra/runtime-heldout/20261116T145728Z-07a28a6d/'
DEV = ('1d6a681f09b0eaf233f838c54465c36a042ec326', 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6/')
SUP = ('414b24d7a1752698fc9bb3bd95e06715b8ebb677', 'docs/evidence/WP-0007/eld-rd-astra/runtime-recovery/20261116T142841Z-284039ca/')
SCORE_HASHES = {'dev': '8cc924888baf65ebcb3ee867891402ede6dd0b0224768c6931592a9a3cce710e',
    'heldout': 'd0c1abdea5f603c8e34ae538aa26fba892d63388986d2ca785725a460526ecc8',
    'supplement_separate': 'b0d3f61144245acfd10f96eada4447255f4585086f3d51b726dbb7185308fb31'}
METRICS = ['fields','cells','normalized_fields','normalized_cells','rows','expected_absences','page_count','page_sentinels','adjacency','cross_page_links']


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True); args = parser.parse_args()
    r.require(not r.git('status','--porcelain').strip(), 'Freeze audit helper before execution')
    r.git('cat-file','-e', AUTHORITY+'^{commit}'); core = r.check_core(); p = r.protocol()
    read = r.GitBlobs(DELIVERABLE); raw_tree = r.GitBlobs(RAW)
    files = {name[len(PREFIX):]: read(name) for name in read.files if name.startswith(PREFIX)}
    def obj(name): return json.loads(files[name.replace('\\','/')])
    capture = obj('capture.json'); inv = obj('publication-inventory.json'); verification = obj('verification.json')
    r.require(len(files) == 170 and len(inv['files']) == 169 and inv['base'] == BASE and not inv['source_changes'], 'Publication size/base differs')
    r.require({x['path'] for x in inv['files']} == {PREFIX+n for n in files if n != 'publication-inventory.json'} and len({x['path'] for x in inv['files']}) == 169, 'Publication inventory incomplete/duplicated')
    for item in inv['files']:
        data = files[item['path'][len(PREFIX):]]
        r.require(item['action'] == 'A' and item['bytes'] == len(data) and item['sha256'] == r.sha(data), 'Publication bytes/hash differ')
    changes = r.git('diff','--name-status',BASE,DELIVERABLE).decode().splitlines()
    r.require(set(changes) == {'A\t'+PREFIX+n for n in files}, 'Undisclosed author changes')
    r.require(r.git('diff','--name-status',DELIVERABLE,PUBLICATION).decode().splitlines() == ['A\t'+inv['later_metadata']], 'Author report-only publication differs')
    copies = capture['copies']; copied_names = {x['relative_path'] for x in copies}
    raw_names = {name[len(PREFIX):] for name in raw_tree.files if name.startswith(PREFIX)}
    r.require(len(copies) == len(copied_names) == capture['copy_count'] == 161 and raw_names == copied_names | {'capture.json','summarize_primary.py'}, 'Raw capture coverage differs')
    r.require(sum(x['bytes'] for x in copies) == capture['copy_bytes'], 'Capture byte count differs')
    for item in copies:
        data = files[item['relative_path']]
        r.require(item['path'] == PREFIX+item['relative_path'] and len(data) == item['bytes'] and r.sha(data) == item['sha256'], 'Capture bytes/hash differ')
    for name in raw_names:
        r.require(raw_tree.files[PREFIX+name] == read.files[PREFIX+name], 'Raw capture changed during consolidation')
    r.require(capture['protected_git_objects'] == verification['protected_git_objects'], 'Protected object records differ')
    for path, identity in capture['protected_git_objects'].items():
        r.require(r.oid(BASE,path) == r.oid(RAW,path) == r.oid(DELIVERABLE,path) == identity, 'Protected author identity changed')
        if not path.startswith('docs/evidence/'):
            r.require(r.oid('HEAD',path) == identity, 'Reviewer protected source changed')
    for item in verification['derived_files']:
        data = files[item['path'][len(PREFIX):]]
        r.require(len(data) == item['bytes'] and r.sha(data) == item['sha256'], 'Derived file record differs')
    r.require(verification['frozen_evidence_and_helper'] == RAW and all(x['exit_code'] == 0 for x in verification['commands']), 'Consolidation execution binding differs')
    result = obj('run-result.json'); release = result['release']; pre = obj('evidence/preflight.json'); load = obj('evidence/load.json'); post = obj('author-model-after.json')
    r.require(capture['authority'] == post['authority'] == RUN_AUTHORITY and capture['executing_head'] == result['executing_head'] == BASE, 'Heldout capture authority/HEAD differs')
    r.require(capture['source'] == release['source_commit'] == r.NEW_SOURCE and capture['independent_acceptance'] == release['accepted_review_commit'] == r.LINEAGES[r.NEW_SOURCE]['review'], 'Heldout source/review differs')
    r.require(pre['release'] == release and release['split'] == 'eval_holdout' and release['owner'] == 'author', 'Preflight release differs')
    r.validate_calls(result,p,release)
    manifest = r.load_json(r.ROOT/p['model_manifest_path']); models = []
    for stage,record in [('preflight',pre),('post',post)]:
        model = {x['path']:x for x in record['model']['files']}
        r.require(len(record['model']['files']) == len(model) == len(manifest['files']) and set(model) == {x['path'] for x in manifest['files']}, 'Model set differs')
        for expected in manifest['files']:
            actual = model[expected['path']]; digest = 'sha256' if expected['digest_kind'] == 'lfs_sha256' else 'git_blob_sha1'
            r.require(actual['ok'] and actual['size'] == expected['size'] and actual[digest] == expected[digest], 'Archived model identity differs')
        notices = {x['path']:x for x in record['notice']['notices']}
        r.require(set(notices) == {x['path'] for x in manifest['notices']}, 'Notice set differs')
        for expected in manifest['notices']:
            actual = notices[expected['path']]
            r.require(actual['ok'] and actual['size'] == expected['size'] and actual['git_blob_sha1'] == expected['git_blob_sha1'], 'Notice identity differs')
        models.append(model)
    r.require(models[0] == models[1], 'Archived pre/post model records differ')
    for item in load['module_cache']['modules']:
        r.require(item['identical'] and item['cache_sha256'] == item['model_sha256'] == models[0][item['file']]['sha256'], 'Module cache differs')
    r.require(all(x['payload_ok'] and x['metadata']['ok'] and x['metadata']['requires_match'] for x in pre['wheels']['wheels']), 'Wheel check failed')
    r.require(pre['renderer']['distribution_version'] == p['renderer']['version'] and p['renderer']['pdfium_version'] in pre['renderer']['PDFIUM_INFO'], 'Renderer identity differs')
    fixtures = {f['fixture_id']:f for f in p['fixtures']}; observations = []; renders = []
    raw_records = {x['path']:x for x in capture['raw_observations']}
    r.require(len(raw_records) == len(capture['raw_observations']) == len(result['calls']) == 15, 'Native observation coverage differs')
    for call in result['calls']:
        f = fixtures[call['fixture_id']]; name = f['fixture_id']+'.'+call['kind']; observation_path = call['observation'].replace('\\','/')
        obs = obj(observation_path); render = obj('evidence/'+name+'.render.json'); saved = raw_records[PREFIX+observation_path]
        r.require(call['status'] == 'completed' and not obs['flags'] and not obs.get('error') and obs['native']['finish_reason'] == 'stop', 'Incomplete native call')
        r.require(saved['fixture_id'] == f['fixture_id'] and saved['kind'] == call['kind'] and saved['raw_sha256'] == obs['raw_output']['full_sha256'] and saved['raw_bytes'] == obs['raw_output']['full_bytes'], 'Capture native digest/count differs')
        r.require(saved['flags'] == [] and saved['utf8_lossless'] and not saved['truncated'] and saved['kernel_path'] == obs['kernel_path']['label'], 'Capture native flags/path differ')
        r.require(render['pdf_sha256'] == f['sha256'] and [x['page'] for x in render['raster']] == list(range(1,f['page_count']+1)), 'Rendered input/pages differ')
        r.require(all(x['width'] > 0 and x['height'] > 0 and re.fullmatch('[0-9a-f]{64}',x['rgb_sha256']) for x in render['raster']), 'Malformed raster metadata')
        r.require(all(x['starts'] == 0 for x in obs['targets'].values() if x['role'] in ('forbidden_save_path','forbidden_eval_site')), 'Forbidden native site entered')
        observations.append({'call':name,'excluded':call['excluded'],**{k:obs[k] for k in ('native','timing','cuda_memory','host_memory','prefill_memory','kernel_path','page_markers')}})
        renders.append({'call':name,**render})
    for item in result['observers']:
        name = PureWindowsPath(item['path']).name
        r.require(item['returncode'] == 0 and item['bytes'] == len(files[name]), 'Observer result differs')
    events = [json.loads(line) for line in files['evidence/events.jsonl'].splitlines()]
    r.require([x['phase'] for x in events] == ['preflight','load']+[phase for c in result['calls'] for phase in ('render:'+c['fixture_id'],'call:'+c['fixture_id']+'.'+c['kind'])], 'Phase sequence differs')
    outcome = obj('evidence/worker-outcome.json'); heartbeat = obj('heartbeat.json'); start = obj('author-process-start.json'); receipt = obj('author-process-exit-and-lease-return.json')
    r.require(outcome['failure'] is None and outcome['no_retry'] and outcome['active_call'] == result['calls'][-1]['fixture_id']+'.measured', 'Worker outcome differs')
    r.require(heartbeat['phase'] == 'finished' and heartbeat['pid'] == outcome['worker_pid'] == pre['worker_pid'], 'Final worker identity differs')
    processes = {x['ProcessId']:x for x in start['processes']}; worker = processes[outcome['worker_pid']]; launcher = processes[result['child_launcher_pid']]
    r.require(worker['ParentProcessId'] == launcher['ProcessId'] and launcher['ParentProcessId'] in processes and set(receipt['owned_process_ids']) == set(processes), 'Process lineage differs')
    r.require(receipt['authority'] == start['authority'] == RUN_AUTHORITY and receipt['lease'] == start['lease_id'] == release['lease_id'] == capture['lease'], 'Lease authority differs')
    r.require(start['run'] == result['run'] == capture['run'] and receipt['run_id'] == PureWindowsPath(result['run']).name and receipt['executing_head'] == BASE, 'Run identity differs')
    r.require(receipt['lease_returned'] and receipt['no_retry'] and not receipt['remaining_processes'] and not receipt['git_status'] and receipt['execute_exit'] == receipt['score_exit'] == receipt['model_verification_exit'] == 0, 'Archived exit receipt incomplete')
    r.require(result['failure'] is None and result['supervisor_error'] is None and not result['secondary_errors'] and not result['finalization_errors'] and all(x == 'available' for x in result['final_observation_status'].values()) and result['child_returncode'] == 0 and result['observed_child_exit'], 'Finalization incomplete')

    dev_read = r.GitBlobs(DEV[0]); sup_read = r.GitBlobs(SUP[0]); dev_bytes = dev_read(DEV[1]+'scores.json'); sup_bytes = sup_read(SUP[1]+'scores.json')
    packets = {'dev':json.loads(dev_bytes),'heldout':obj('scores.json'),'supplement_separate':json.loads(sup_bytes)}
    for name,data in [('dev',dev_bytes),('heldout',files['scores.json']),('supplement_separate',sup_bytes)]:
        r.require(r.sha(data) == SCORE_HASHES[name], 'Bound score packet changed')
    proof_specs = [('dev','b87728b5b3c10d4a5633a11ed8c1e1988e32c231','dev-first-run/reproduction.json'),('supplement_separate','10d4f3ab350ac82487e46f815fdf82a8e842ed66','dev-recovery/reproduction.json')]
    proofs = {'heldout':r.load_json(Path(__file__).with_name('reproduction.json'))}; proof_identities = []
    for name,commit,relative in proof_specs:
        path = 'docs/reviews/WP-0007/eld-baseline-reviewer/005/'+relative
        identity = r.oid(commit,path); r.require(identity == r.oid('HEAD',path), 'Previous proof rewritten')
        proofs[name] = r.load_json(r.ROOT/path); proof_identities.append({'packet':name,'commit':commit,'path':path,'blob':identity})
    for name,packet in packets.items():
        proof = proofs[name]
        r.require(proof['reproduced'] == packet and proof['same_code_score_reproduction_equal'] and proof['independent_numeric_accounting_passed'], 'Packet differs from independent proof')
    primary = obj('primary-results.json'); scores = packets['dev']['scores'] + packets['heldout']['scores']
    r.require(len(scores) == len({s['fixture_id'] for s in scores}) == primary['primary_document_denominator'] == 26 and primary['primary_completed_documents'] == sum(s['completed_documents'] for s in scores) == 25, 'Primary denominator/completion differs')
    r.require(primary['primary_scores'] == scores and primary['supplement_separate'] == packets['supplement_separate'], 'Primary replacement or supplement alteration')
    r.require(primary['summary_by_split'] == {**packets['dev']['summary'],**packets['heldout']['summary']} == r.summarize(scores), 'Split/family/variant summaries changed')
    r.independent_means(scores,primary['summary_by_split'])
    failed = [s for s in scores if s['completion'] != 'completed']
    r.require(len(failed) == 1 and failed[0]['fixture_id'] == r.RECOVERY_BINDING['fixture_id'] and failed[0]['fields']['total'] == 15 and failed[0]['cells']['total'] == 180 and all(failed[0][k]['correct'] == 0 for k in METRICS), 'Original failed denominator lost')
    r.require(primary['helper_commit'] == RAW and primary['helper_sha256'] == r.sha(files['summarize_primary.py']) and primary['baseline_tree'] == r.LINEAGES[r.NEW_SOURCE]['tree'], 'Author consolidation helper binding differs')
    expected_inputs = {'dev':{'commit':DEV[0],'path':DEV[1]+'scores.json','sha256':SCORE_HASHES['dev']},'heldout':{'path':PREFIX+'scores.json','sha256':SCORE_HASHES['heldout']},'supplement_separate':{'commit':SUP[0],'path':SUP[1]+'scores.json','sha256':SCORE_HASHES['supplement_separate']}}
    r.require(primary['input_packets'] == expected_inputs, 'Consolidation input binding differs')
    compact = []
    for s in scores:
        entry = {k:s[k] for k in ('fixture_id','family_id','split','variant_kind','completion','eligible_for_exact_credit','parse_errors','mapping_coverage','reference_coverage','text')}
        entry['metrics'] = {k:{a:b for a,b in s[k].items() if a not in ('details','interpretation')} for k in METRICS}; compact.append(entry)
    r.require(primary['per_document_compact'] == compact and primary['reference_coverage_status_counts'] == {'complete_for_admitted_writer':26} and all(s['reference_coverage']['status'] == 'complete_for_admitted_writer' for s in scores), 'Compact/coverage summary differs')
    stdout = json.loads(files['consolidation.stdout.txt'])
    r.require(stdout == {'primary_denominator':26,'primary_completed':25,'copies_verified':161,'summary_by_split':primary['summary_by_split']} and files['consolidation.stderr.txt'] == b'', 'Consolidation transcript differs')
    runtime = obj('runtime-summary.json'); runtime_checks = []; measured_times = {1:[],3:[]}
    runtime_note = 'Descriptive individual attempts; warmups excluded; sampled host peaks are lower bounds, lifetime peaks are not per-call. CPU/RAM/WDDM and observer overhead confound timing.'
    for name,reader,prefix in [('dev_primary',dev_read,DEV[1]),('heldout_primary',read,PREFIX),('supplement_separate',sup_read,SUP[1])]:
        def read_json(relative): return json.loads(reader(prefix+relative.replace('\\','/')))
        original = read_json('run-result.json'); calls = []
        for call in original['calls']:
            item = dict(call)
            if call.get('observation'):
                observed = read_json(call['observation'])
                item['observed'] = {k:observed.get(k) for k in ('timing','native','raw_output','cuda_memory','host_memory','kernel_path','flags','page_count_in')}
                if name != 'supplement_separate' and not call['excluded']:
                    measured_times[observed['page_count_in']].append(observed['timing']['external_synchronized_wall_s']['value'])
            calls.append(item)
        expected = {k:original[k] for k in ('run','executing_head','elapsed_s','failure','child_returncode','free_bytes_after','owned_bytes_after')}
        expected.update(load=read_json('evidence/load.json'),calls=calls,interpretation=runtime_note)
        r.require(runtime[name] == expected, 'Runtime consolidation changed immutable record: '+name)
        runtime_checks.append({'set':name,'calls':len(calls),'completed_measured':sum(c['status']=='completed' and not c['excluded'] for c in calls),'executing_head':original['executing_head'],'elapsed_s':original['elapsed_s'],'failure':original['failure']})
    rules = r.load_json(r.HERE/'mapping.json'); unmapped_examples = []; typed_deltas = []
    for s in packets['heldout']['scores']:
        if s['family_id'] in ('F03','F08'):
            raw = files['evidence/'+s['fixture_id']+'.measured.raw.txt'].decode('utf-8'); pred = r.prediction(raw,rules)
            r.require(not pred['tables'] and s['mapping_coverage']['cells_with_candidate'] == 0 and s['cells']['correct'] == 0 and s['cells']['total'] == (56 if s['family_id']=='F03' else 112), 'Unmapped table explanation differs')
            headers = [{'page':page['page'],'first_row':[c['text'] for c in block['rows'][0]]} for page in pred['pages'] for block in page['blocks'] if block['kind']=='table' and block['rows']]
            unmapped_examples.append({'fixture_id':s['fixture_id'],'family':s['family_id'],'table_first_rows':headers,'mapping':s['mapping_coverage'],'page_sentinels':s['page_sentinels']['correct'],'adjacency':s['adjacency']['correct'],'cross_page_links':s['cross_page_links']['correct']})
        for printed,typed in zip(s['cells']['details'],s['normalized_cells']['details']):
            if printed['credited_exact'] != typed['credited_exact']:
                r.require(s['family_id'] == 'F06' and printed['credited_exact'] and not typed['credited_exact'] and printed['predicted'] == printed['expected_printed'] == typed['raw'] and typed['raw'] in ('2.00 GL','5.00 ST') and typed['status'] == 'invalid_or_unsupported_quantity_unit', 'Typed delta interpretation differs')
                typed_deltas.append({'fixture_id':s['fixture_id'],'printed':printed,'typed':typed})
    r.require(len(typed_deltas) == 6, 'Typed delta count differs')
    absences = [a for s in packets['heldout']['scores'] for a in s['expected_absences']['details']]
    r.require(len(absences) == 13 and all(a['unmapped'] and not a['violation'] and not a['verified_absent'] and a['candidate_count'] == 0 for a in absences), 'Absence classification differs')
    r.require(all(s['text']['alignment'] == 'SequenceMatcher-autojunk=False; not minimum Levenshtein WER' for s in scores), 'Token metric definition differs')
    env_keys = []
    def walk(value,path):
        if isinstance(value,dict):
            for key,item in value.items():
                if re.search(r'(^|_)(env|environment|environ)(_|$)',key,re.I): env_keys.append(path+'/'+key)
                walk(item,path+'/'+key)
        elif isinstance(value,list):
            for i,item in enumerate(value): walk(item,path+'/'+str(i))
    for name,data in files.items():
        if name.endswith('.json'): walk(json.loads(data),name)
    report = {'verification_authority':AUTHORITY,'helper_head':r.git('rev-parse','HEAD').decode().strip(),'source':r.NEW_SOURCE,'tree':r.LINEAGES[r.NEW_SOURCE]['tree'],'all_checks_passed':True,
        'capture_copies':161,'capture_bytes':capture['copy_bytes'],'publication_files':170,'raw_freeze_files':len(raw_names),'core':core,'proof_identities':proof_identities,'input_packets':expected_inputs,
        'primary_denominator':26,'primary_completed':25,'original_failed_fixture':failed[0]['fixture_id'],'summary_by_split':primary['summary_by_split'],'reference_coverage':primary['reference_coverage_status_counts'],
        'archived_preflight':{'model_objects':len(models[0]),'notices':len(manifest['notices']),'installed':pre['installed'],'wheel_records':len(pre['wheels']['wheels']),'renderer':pre['renderer'],'module_cache_copies':len(load['module_cache']['modules'])},
        'native_observations':observations,'renders':renders,'observer_records':len(result['observers']),'phase_records':len(events),'final_observation_status':result['final_observation_status'],'worker_outcome':outcome,'heartbeat':heartbeat,'exit_receipt':receipt,
        'runtime_summary_verified':runtime_checks,'primary_completed_wall_ranges_s':{str(k):{'count':len(v),'minimum':min(v),'maximum':max(v)} for k,v in measured_times.items()},
        'unmapped_table_diagnostics':unmapped_examples,'typed_quantity_deltas':typed_deltas,'heldout_absences':{'total':13,'unmapped':13,'verified_absent':0,'detected_nonempty_violations':0},
        'environment_snapshot':{'matching_key_paths':env_keys,'complete_per_child_environment_name_snapshot':'absent'},'stderr':files['stderr.txt'].decode(errors='replace'),
        'immutable_artifacts_read':read.reads+dev_read.reads+sup_read.reads,
        'limits':['Same frozen scorer reproduction plus independent accounting; no alternative tuned metric.','Reference completeness applies to admitted synthetic writer; reading-order/representation affect SequenceMatcher token error.','Mapping failures and unsupported GL/ST typed conversions are separate from raw recognition error; unverified absence is not detected invention.','Original failed primary record remains; supplemental recovery is excluded from all primary summaries.','Archived runtime/model/renderer/lease records were inspected, not freshly measured. Sampled memory lower bounds, WDDM/shared CPU/RAM, cold-cache and observer confounders remain.','Complete child environment-name snapshot absent; local torchvision SHA256 TOFU provenance remains.','No model/ML/GPU import or query, external runtime path, live process or service access.']}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out: json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'passed':True,'capture_copies':161,'publication_files':170,'primary_denominator':26,'primary_completed':25,'native_observations':len(observations),'typed_deltas':len(typed_deltas),'absence_violations':0}))


if __name__ == '__main__': main()
