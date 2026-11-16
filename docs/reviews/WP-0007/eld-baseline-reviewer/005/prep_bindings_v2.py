"""Focused CPU/dev-only preparation; all new-lineage result records are test doubles."""
from __future__ import annotations
import copy, datetime, json, sys, traceback
from pathlib import Path

OWN = Path(__file__).resolve().parent
sys.path.insert(0,str(OWN))
import reproduce_v2 as r

AUTHORITY = '44f1bb72ad41623f5f7955c61a71838aacee5115'
OLD_AUTHORITY = 'a6f8f2a17fc8f3db68e11d2971423f78b2dc7861'
NEW_AUTHORITY = '934d6a204bea0a61eb30c33a395b5c616dd00063'
OLD_PATH = 'docs/coordination/WP-0007/releases/author-dev.json'
NEW_PATH = 'docs/coordination/WP-0007/releases/author-dev-recovery.json'
EVIDENCE = '1d6a681f09b0eaf233f838c54465c36a042ec326'
PREFIX = 'docs/evidence/WP-0007/eld-rd-astra/runtime-dev/20261116T051059Z-eda73dc6'

def main():
    output = Path(sys.argv[1]); r.require(not r.git('status','--porcelain').strip(),'Freeze helpers before decisive checks')
    p = r.protocol(); allowed = {str((r.ROOT / f[k]).resolve()).casefold() for f in p['fixtures'] if f['split'] == 'dev' for k in ('file_path','expected_ground_truth_path','source_record_path')}; seen = []
    def audit(event,args):
        if event == 'open' and isinstance(args[0],str):
            path = Path(args[0]).resolve()
            if '/evaluation/synthetic/' in path.as_posix():
                if str(path).casefold() not in allowed: raise PermissionError('Preparation permits dev contents only')
                seen.append(str(path))
    sys.addaudithook(audit)
    checks = []
    def check(name, action):
        try: checks.append({'name':name,'passed':True,'detail':action()})
        except Exception as e: checks.append({'name':name,'passed':False,'error':repr(e),'traceback':traceback.format_exc()})
    def refuses(action):
        try: action()
        except (ValueError,PermissionError,KeyError) as e: return {'type':type(e).__name__,'reason':str(e)}
        raise AssertionError('Invalid test input was accepted')
    core = r.check_core(); old_authority = r.GitBlobs(OLD_AUTHORITY); new_authority = r.GitBlobs(NEW_AUTHORITY); evidence = r.GitBlobs(EVIDENCE)
    old = json.loads(old_authority(OLD_PATH)); new = json.loads(new_authority(NEW_PATH))
    result_bytes = evidence(PREFIX+'/run-result.json'); result = json.loads(result_bytes); plan = json.loads(evidence(PREFIX+'/plan.json'))
    lineage = r.validate_lineage(old,result,plan,OLD_AUTHORITY,OLD_PATH,p,'dev','author')
    packet, detail = r.reproduce(evidence,PREFIX,result,p,old)
    packet = r.verify_envelope(packet,json.loads(evidence(PREFIX+'/scores.json')),result_bytes)
    check('original_complete_dev_envelope_and_honest_old_lineage',lambda:{'lineage':lineage,'documents':len(packet['scores']),'completion_counts':detail['completion_counts'],'excluded_warmups':detail['excluded_warmups'],'whole_envelope_equal':True,'packet_sha256':r.sha(json.dumps(packet,sort_keys=True).encode())})
    check('accepted_core_identity_across_both_runtime_sources',lambda:core)
    def double(release):
        calls = [{**c,'status':'failed' if i == 0 else 'not_run_after_failure','observation':None} for i,c in enumerate(r.expected_plan(p,release))]
        return {'release':release,'executing_head':release['executing_head'],'calls':calls,'failure':'CPU_PREPARATION_ONLY_NO_NEW_RUNTIME_RESULT'}, {'release':release,'executing_head':release['executing_head'],'authority_commit':NEW_AUTHORITY,'release_path':NEW_PATH,'calls':r.expected_plan(p,release)}
    new_result, new_plan = double(new)
    check('new_release_metadata_lineage_test_double_only',lambda:r.validate_lineage(new,new_result,new_plan,NEW_AUTHORITY,NEW_PATH,p,'dev','author'))
    check('supplement_prior_actual_immutable_failed_record',lambda:r.verify_prior_recovery(new,p))
    def matrix():
        counts = {}
        for owner in ('author','reviewer'):
            for split in ('dev','eval_holdout'):
                value = {k:v for k,v in new.items() if k != 'supplemental_recovery'}; value.update(owner=owner,split=split)
                planned = r.expected_plan(p,value); counts[owner+'/'+split] = sum(not c['excluded'] for c in planned)
                r.require(sum(c['excluded'] for c in planned) == 2,'Warmups changed')
        r.require(counts == {'author/dev':13,'author/eval_holdout':13,'reviewer/dev':1,'reviewer/eval_holdout':2},'Matrix denominators changed')
        return {'counts':counts,'heldout_scope':'public metadata only; no content access','fixed_sentinels':r.SENTINELS}
    check('ordinary_and_reviewer_schedule_metadata',matrix)
    def supplemental():
        score, counts = r.reproduce(lambda path: (_ for _ in ()).throw(AssertionError('Test has no raw blobs')), 'CPU-PREPARATION-ONLY',new_result,p,new)
        item = score['scores'][0]
        r.require(len(score['scores']) == 1 and score['summary']['dev']['document_denominator'] == 1 and item['fields']['total'] == 15 and item['cells']['total'] == 180 and not item['eligible_for_exact_credit'],'Supplement missing-output denominator changed')
        r.require(score['scope'] == r.SUPPLEMENT_SCOPE and score['supplemental_recovery'] == r.RECOVERY_BINDING,'Supplement lineage/scope missing')
        encoded = json.dumps(new_result).encode(); valid = {**score,'run_result_sha256':r.sha(encoded)}
        r.verify_envelope(score,valid,encoded)
        changed = copy.deepcopy(valid); changed.pop('scope'); refuses(lambda:r.verify_envelope(score,changed,encoded))
        changed = copy.deepcopy(valid); changed['supplemental_recovery']['prior_run_result_sha256'] = '0'*64; refuses(lambda:r.verify_envelope(score,changed,encoded))
        return {'test_double':True,'completed_new_outputs':0,'denominator':1,'fields':15,'cells':180,'scope_and_lineage_refusals':2,'counts':counts['completion_counts']}
    check('supplemental_failed_unexecuted_denominators_and_whole_envelope',supplemental)
    def reviewer_dev():
        value = {k:v for k,v in new.items() if k != 'supplemental_recovery'}; value['owner'] = 'reviewer'
        fake,_ = double(value); score,counts = r.reproduce(lambda p:None,'CPU-PREPARATION-ONLY',fake,p,value)
        r.require([s['fixture_id'] for s in score['scores']] == [r.SENTINELS[0]] and score['summary']['dev']['document_denominator'] == 1,'Reviewer dev subset changed')
        return {'test_double':True,'fixture':score['scores'][0]['fixture_id'],'fields':score['scores'][0]['fields']['total'],'cells':score['scores'][0]['cells']['total']}
    check('reviewer_dev_only_missing_output_subset',reviewer_dev)
    def bindings():
        rejected = []
        for base, key, value in [(old,'accepted_review_commit',r.LINEAGES[r.NEW_SOURCE]['review']),(new,'accepted_review_commit',r.LINEAGES[r.OLD_SOURCE]['review']),(new,'source_commit','f11fcd1141c08d49ac538858354f3b5d87277038'),(new,'source_tree','0'*40)]:
            changed = copy.deepcopy(base); changed[key] = value
            original_result, original_plan, auth, path = (result,plan,OLD_AUTHORITY,OLD_PATH) if base is old else (new_result,new_plan,NEW_AUTHORITY,NEW_PATH)
            rejected.append(refuses(lambda:r.validate_lineage(changed,original_result,original_plan,auth,path,p,'dev','author')))
        changed_result = copy.deepcopy(result); changed_result['executing_head'] = new['executing_head']
        rejected.append(refuses(lambda:r.validate_lineage(old,changed_result,plan,OLD_AUTHORITY,OLD_PATH,p,'dev','author')))
        for value in ('SYN-WO-01-v0-clean','SYN-MP-02-v0-clean','unknown',[r.RECOVERY_BINDING['fixture_id']]*2):
            changed = copy.deepcopy(new); changed['supplemental_recovery']['fixture_id'] = value; rejected.append(refuses(lambda:r.expected_plan(p,changed)))
        for field in ('prior_evidence_commit','prior_run_result_sha256','prior_authority_commit'):
            changed = copy.deepcopy(new); changed['supplemental_recovery'][field] = '0'*40; rejected.append(refuses(lambda:r.verify_prior_recovery(changed,p)))
        changed = copy.deepcopy(new); changed['sentinels'].reverse(); rejected.append(refuses(lambda:r.expected_plan(p,changed)))
        return rejected
    check('lineage_review_source_head_recovery_and_sentinel_refusals',bindings)
    def plans():
        rejected = []
        for calls in (result['calls'][:-1],result['calls']+[result['calls'][-1]],result['calls'][::-1]):
            rejected.append(refuses(lambda:r.validate_calls({**result,'calls':calls},p,old)))
        changed = copy.deepcopy(result); changed['calls'][0]['observation'] = None; rejected.append(refuses(lambda:r.validate_calls(changed,p,old)))
        value = {k:v for k,v in new.items() if k != 'supplemental_recovery'}
        changed = copy.deepcopy(result); changed['release'] = value; target = changed['calls'][2]; target.update(status='failed',observation=None,observation_status='unavailable')
        changed['finalization_errors'] = [{'stage':'call_observation:'+target['fixture_id']+'.'+target['kind']}]
        r.validate_calls(changed,p,value)
        changed['finalization_errors'] = []; rejected.append(refuses(lambda:r.validate_calls(changed,p,value)))
        return {'refusals':rejected,'unavailable_earlier_record_with_actual_finalization_stage':'accepted; subsequent valid observations remain distinguishable'}
    check('incomplete_duplicate_and_finalization_record_provenance',plans)
    def native_mutations():
        first = result['calls'][0]; path = PREFIX+'/'+r.relative(first['observation']); observation = json.loads(evidence(path)); outcomes = []
        for mutation in ('raw_bytes','token_bytes','native_token_hash','finish','flags','page_count','prompt','truncated_tokens'):
            obs = copy.deepcopy(observation)
            if mutation == 'native_token_hash': obs['native']['token_ids_sha256'] = '0'*64
            if mutation == 'finish': obs['native']['finish_reason'] = 'length'
            if mutation == 'flags': obs['flags'] = [{'code':'CPU_TEST_FAILURE'}]
            if mutation == 'page_count': obs['native']['num_pages_out'] += 1
            if mutation == 'prompt': obs['native']['prompt'] += 'changed'
            if mutation == 'truncated_tokens': obs['token_ids_file']['truncated_by_writer'] = True
            def read(name):
                if name == path: return json.dumps(obs).encode()
                data = evidence(name)
                suffix = obs['raw_output']['name'] if mutation == 'raw_bytes' else obs['token_ids_file']['name']
                return data+b'!' if mutation in ('raw_bytes','token_bytes') and name.endswith('/'+suffix) else data
            outcomes.append({'mutation':mutation,**refuses(lambda:r.reproduce(read,PREFIX,result,p,old))})
        return outcomes
    check('raw_token_finish_prompt_page_and_failure_refusals',native_mutations)
    def independent_accounting():
        altered = copy.deepcopy(packet['summary']); altered['dev']['families']['F01']['metrics']['fields']['mean'] += 0.01
        mean = refuses(lambda:r.independent_means(packet['scores'],altered))
        item = copy.deepcopy(packet['scores'][0]); item['fields']['total'] -= 1
        expected = r.expected_for(p['fixtures'][0]); denominator = refuses(lambda:r.accounting(item,expected))
        wrong = copy.deepcopy(packet); wrong['unexpected'] = 'extra'; envelope = refuses(lambda:r.verify_envelope({k:v for k,v in packet.items() if k != 'run_result_sha256'},wrong,result_bytes))
        return {'altered_mean':mean,'altered_denominator':denominator,'extra_envelope_key':envelope}
    check('independent_numeric_and_complete_envelope_refusals',independent_accounting)
    def heldout():
        value = {k:v for k,v in new.items() if k != 'supplemental_recovery'}; value['split'] = 'eval_holdout'
        return refuses(lambda:r.reproduce(lambda path: (_ for _ in ()).throw(AssertionError('Read before heldout gate')),'NO-READ',{},p,value))
    check('heldout_refused_before_any_evidence_or_content_read',heldout)
    protected = {path:r.oid('HEAD',path) == r.oid('b9dc09fa3dc6838c59f519063bb38d2c2a7f44f0',path) for path in ['qualification/baseline','qualification/q0','evaluation','src','tests','web','workers','docs/reviews/WP-0007/eld-baseline-reviewer/005/reproduce.py','docs/reviews/WP-0007/eld-baseline-reviewer/005/dev-first-run/reproduction.json']}
    final = {'authority':AUTHORITY,'helper_head':r.git('rev-parse','HEAD').decode().strip(),'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'checks':checks,'preserved':protected,
        'passed':all(c['passed'] for c in checks) and all(protected.values()),'immutable_original_dev_reads':old_authority.reads+evidence.reads,'current_recovery_metadata_reads_only':new_authority.reads,'dev_content_paths':sorted(set(seen)),
        'model_modules':[name for name in sys.modules if any(name == x or name.startswith(x+'.') for x in r.BLOCKED)],
        'limits':'Preparation only. The only actual raw/score evidence read is immutable original dev. All new-lineage result/plan records are explicitly CPU test doubles, not completed recovery evidence. Heldout checks use public schedule metadata/refusal only. No active run/external runtime/model/GPU/services were accessed; canonical /005 stays held.'}
    r.require(not final['model_modules'],'Model import occurred')
    with output.open('x',encoding='utf-8',newline='\n') as out: json.dump(final,out,indent=2);out.write('\n')
    print(json.dumps({'passed':final['passed'],'groups':len(checks),'dev_content_paths':len(set(seen)),'output':str(output)}))
    return int(not final['passed'])

if __name__ == '__main__': raise SystemExit(main())
