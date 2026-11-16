"""Versioned offline /005 reproduction for the two accepted B0 runtime lineages.

Only completed immutable evidence explicitly bound by the coordinator may be used.
This records verification authority; no flag grants content or runtime permission.
"""
from __future__ import annotations
import argparse, ast, collections, importlib.abc, json, re, sys
from pathlib import Path, PurePosixPath

BLOCKED = ('torch','transformers','triton','q0harness.backend_torch')
class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == x or fullname.startswith(x + '.') for x in BLOCKED):
            raise RuntimeError('Offline reproduction forbids model import: ' + fullname)
sys.meta_path.insert(0, NoModelImports())
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reproduce as original
from reproduce import ROOT, HERE, GitBlobs, require, git, oid, relative, sha, load_json, protocol, retained, accounting, independent_means
from baseline import prediction
from corpus import expected_for, reference_for
from score import score_document, summarize
from release import RECOVERY_BINDING

OLD_SOURCE = 'f807e0ac737df4e9e0aeeb96f716afec57f58ff6'
NEW_SOURCE = '522f15f1f6e399c36b9c6c107fc08f51862f1fc1'
LINEAGES = {
    OLD_SOURCE: {'tree':'df44162c62641596032df04bc834754da38a5f7b','review':'8c208273c2524b0253b046159178a9f5e6788049','sequence':'003'},
    NEW_SOURCE: {'tree':'deae8e826f4770e880374c68e6a56c8c65b6f8a3','review':'b9dc09fa3dc6838c59f519063bb38d2c2a7f44f0','sequence':'010'},
}
SENTINELS = ['SYN-WO-02-v3-hybrid-note','SYN-INV-03-v1-raster300','SYN-MP-02-v0-clean']
CORE = ['native.py','score.py','typed_values.py','corpus.py','mapping.json','protocol.json']
SUPPLEMENT_SCOPE = 'supplemental_single_failed_dev; does not replace original primary scores'

def check_core():
    require(oid('HEAD','qualification/baseline') == LINEAGES[NEW_SOURCE]['tree'], 'Reviewer worktree must retain the new accepted runtime tree')
    checks = []
    for path in ['qualification/baseline/' + x for x in CORE] + ['qualification/q0','evaluation']:
        ids = {rev:oid(rev,path) for rev in (OLD_SOURCE,NEW_SOURCE,'HEAD')}
        require(len(set(ids.values())) == 1, 'Pure core/Q0/corpus changed: ' + path)
        checks.append({'path':path,'objects':ids})
    bodies = []
    for rev in (OLD_SOURCE,NEW_SOURCE,'HEAD'):
        text = git('show',rev + ':qualification/baseline/baseline.py').decode()
        node = next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name == 'prediction')
        bodies.append(ast.get_source_segment(text,node))
    require(len(set(bodies)) == 1, 'Pure prediction entry changed')
    return {'objects':checks,'prediction_sha256':sha(bodies[0].encode())}

def expected_plan(p, r):
    require(r['owner'] in ('author','reviewer') and r['split'] in ('dev','eval_holdout'), 'Unknown owner/split')
    require(r['sentinels'] == SENTINELS, 'Fixed pre-result sentinel selection changed')
    selected = [f for f in p['fixtures'] if f['split'] == r['split']]
    if 'supplemental_recovery' in r:
        require(r['source_commit'] == NEW_SOURCE and r['owner'] == 'author' and r['split'] == 'dev' and r['allow_test_content'] is False and r['supplemental_recovery'] == RECOVERY_BINDING, 'Only the exact accepted failed-dev supplement is supported')
        selected = [f for f in selected if f['fixture_id'] == RECOVERY_BINDING['fixture_id']]
        require(len(selected) == 1, 'Supplement must retain one measured denominator')
    elif r['owner'] == 'reviewer':
        selected = [f for f in selected if f['fixture_id'] in SENTINELS]
        require(len(selected) == (1 if r['split'] == 'dev' else 2), 'Reviewer subset differs')
    else: require(len(selected) == 13, 'Primary split must retain thirteen documents')
    return [{'fixture_id':x,'kind':'warmup','excluded':True} for x in p['warmups']] + [{'fixture_id':f['fixture_id'],'kind':'measured','excluded':False} for f in selected]

def validate_lineage(r, result, plan, authority, release_path, p, split, owner):
    require(r['source_commit'] in LINEAGES, 'Unaccepted source lineage')
    lineage = LINEAGES[r['source_commit']]
    review_path = 'docs/agent-reports/eld-baseline-reviewer/WP-0007/' + lineage['sequence'] + '_2026-11-16_review_eld-baseline-reviewer.md'
    require(r['source_tree'] == lineage['tree'] and r['accepted_review_commit'] == lineage['review'] and r['accepted_review_path'] == review_path, 'Source/review lineage relabeled')
    require(r['owner'] == owner and r['split'] == split, 'Run owner/split differ from assignment')
    require(split == 'dev' or r['allow_test_content'] is True, 'Original heldout release permission missing')
    require(result['release'] == plan['release'] == r, 'Release/result/plan mismatch')
    require(result['executing_head'] == plan['executing_head'] == r['executing_head'], 'Original executing HEAD differs')
    require(oid(r['source_commit'],'qualification/baseline') == oid(r['executing_head'],'qualification/baseline') == lineage['tree'], 'Original source/executing tree differs')
    require(plan['authority_commit'] == authority and plan['release_path'] == release_path, 'Original authority/path differs')
    require(oid(r['accepted_review_commit'],review_path), 'Actual accepted review object missing')
    if r['source_commit'] == OLD_SOURCE:
        require(owner == 'author' and split == 'dev' and r['executing_head'] == 'e22c6730d19a6d616f0e7afb00b9416635799c16' and 'supplemental_recovery' not in r, 'Original lineage supports only the immutable primary dev run')
    for key,path in [('protocol_sha256',HERE/'protocol.json'),('mapping_sha256',HERE/'mapping.json'),('lock_sha256',ROOT/p['dependency_lock_path'])]:
        require(r[key] == sha(path.read_bytes()), 'Original digest differs: ' + key)
    require(r['runtime_root'] == p['runtime_roots'][owner] and r['gpu_uuid'] == p['gpu']['uuid'], 'Original resource identity differs')
    require(oid('HEAD','qualification/q0/harness/q0harness') == p['q0_core_tree'], 'Accepted Q0 core changed')
    require(sha((ROOT/'evaluation/manifests/corpus-manifest.json').read_bytes()) == p['corpus_manifest_sha256'], 'Corpus metadata changed')
    require(plan['calls'] == expected_plan(p,r), 'Parent plan differs from exact released scope')
    return {'source_commit':r['source_commit'],'source_tree':lineage['tree'],'accepted_review_commit':lineage['review'],'accepted_review_path':review_path,'executing_head':r['executing_head'],'owner':owner,'split':split}

def verify_prior_recovery(r, p):
    if 'supplemental_recovery' not in r: return []
    expected_plan(p,r)
    b = r['supplemental_recovery']; evidence = GitBlobs(b['prior_evidence_commit']); authority = GitBlobs(b['prior_authority_commit'])
    raw = evidence(b['prior_run_result_path']); require(sha(raw) == b['prior_run_result_sha256'], 'Immutable prior run digest differs')
    prior = json.loads(raw); prior_release = json.loads(authority(b['prior_release_path']))
    require(prior['release'] == prior_release and prior_release['source_commit'] == OLD_SOURCE and prior['executing_head'] == prior_release['executing_head'] == 'e22c6730d19a6d616f0e7afb00b9416635799c16' and prior['failure'], 'Prior failed-run identity differs')
    require([{k:c[k] for k in ('fixture_id','kind','excluded')} for c in prior['calls']] == expected_plan(p,prior_release), 'Prior complete matrix differs')
    for c in prior['calls']:
        selected = not c['excluded'] and c['fixture_id'] == b['fixture_id']
        require(c['status'] == ('failed' if selected else 'completed'), 'Prior selected record is not the sole failed measurement')
    return evidence.reads + authority.reads

def validate_calls(result, p, r):
    calls = result['calls']; planned = expected_plan(p,r)
    require([{k:c[k] for k in ('fixture_id','kind','excluded')} for c in calls] == planned, 'Missing/duplicate/reordered/spurious planned call')
    stages = {e.get('stage') for e in result.get('finalization_errors',[])}; stopped = False
    for c in calls:
        require(c['status'] in ('completed','failed','not_run_after_failure'), 'Unknown call completion status')
        unavailable = c.get('observation_status') == 'unavailable'
        if unavailable:
            require(r['source_commit'] == NEW_SOURCE and c['status'] == 'failed' and c['observation'] is None and result.get('failure') and 'call_observation:' + c['fixture_id'] + '.' + c['kind'] in stages, 'Unavailable record lacks its finalization provenance')
        if c['status'] == 'completed':
            require(c['observation'] and c.get('observation_status','available') == 'available' and not stopped, 'Completed call lacks observation or follows stopped execution')
        if not unavailable and c['status'] != 'completed': stopped = True
    return planned

def reproduce(read, prefix, result, p, r, permit_holdout=False):
    original.split_gate(r['split'],permit_holdout)  # Before any raw, expected or reference read.
    validate_calls(result,p,r)
    fixtures = {f['fixture_id']:f for f in p['fixtures']}; rules = load_json(HERE/'mapping.json'); scores = []; observations = []; totals = []
    for c in result['calls']:
        f = fixtures[c['fixture_id']]; raw = b''
        if c['observation']:
            path = prefix + '/' + relative(c['observation']); data = read(path); obs = json.loads(data); base = str(PurePosixPath(path).parent)
            require(obs['fixture_id'] == f['fixture_id'] and obs['family_id'] == f['family_id'] and obs['kind'] == c['kind'] and obs['page_count_in'] == f['page_count'], 'Observation input identity differs')
            require(obs['label'] == f['fixture_id'] + '.' + c['kind'] and obs['excluded_from_warm_statistics'] == c['excluded'], 'Observation label/exclusion differs')
            kwargs = {**p['call']['fixed_kwargs'],'max_new_tokens':8000*f['page_count'],'ngram_window':1024 if f['page_count'] > 1 else 128}
            require(obs['call_kwargs'] == kwargs, 'Native call settings changed')
            if 'raw_output' in obs:
                raw = retained(read,base,obs['raw_output']); tokens = json.loads(retained(read,base,obs['token_ids_file'])); native = obs['native']
                require(native['text_sha256'] == obs['raw_output']['full_sha256'], 'Raw/native text identity differs')
                require(isinstance(tokens,list) and all(type(t) is int and t >= 0 for t in tokens), 'Invalid token IDs')
                require(sha(json.dumps(tokens).encode()) == native['token_ids_sha256'] and len(tokens) == native['output_tokens'], 'Native token identity/count differs')
                if c['status'] == 'completed':
                    require(raw and not obs.get('flags') and not obs.get('error') and obs['raw_output']['utf8_lossless'] and not obs['raw_output']['truncated_by_writer'] and not obs['token_ids_file']['truncated_by_writer'], 'Completed call has failed/lossy/truncated output')
                    require(native['provenance'] == 'native' and native['finish_reason'] == 'stop' and native['num_pages_out'] == native['expected_pages'] == f['page_count'], 'Completed native finish/page provenance differs')
                    require(native['prompt'] == '<PAGE><image>' * f['page_count'] + p['call']['prompt'] and native['prompt_len'] + kwargs['max_new_tokens'] <= kwargs['max_length'], 'Native prompt/context differs')
                    positions = [i for i,t in enumerate(tokens) if t == p['call']['page_token_id']]
                    require(obs['page_markers']['marker_token_positions'] == positions and len(positions) == obs['page_markers']['out'] == obs['page_markers']['expected'] == f['page_count'], 'Completed page marker evidence differs')
            else: require(c['status'] != 'completed', 'Completed call lacks retained native output')
            observations.append({'fixture_id':f['fixture_id'],'kind':c['kind'],'status':c['status'],'observation_sha256':sha(data),**{k:obs.get(k) for k in ('native','raw_output','token_ids_file','timing','cuda_memory','host_memory','prefill_memory','kernel_path','page_markers','error','flags')}})
        if c['excluded']: continue
        expected = expected_for(f,permit_holdout); reference = reference_for(f,permit_holdout)
        score = score_document(prediction(raw.decode('utf-8'),rules),expected,reference,c['status']); score['raw_sha256'] = sha(raw)
        totals.append({'fixture_id':f['fixture_id'],'totals':accounting(score,expected)}); scores.append(score)
    summary = summarize(scores); independent_means(scores,summary)
    packet = {'scores':scores,'summary':summary}
    if 'supplemental_recovery' in r: packet.update(scope=SUPPLEMENT_SCOPE,supplemental_recovery=r['supplemental_recovery'])
    return packet, {'accounting':totals,'observations':observations,'completion_counts':dict(collections.Counter(c['status'] for c in result['calls'] if not c['excluded'])),'excluded_warmups':sum(c['excluded'] for c in result['calls'])}

def verify_envelope(packet, published, result_bytes):
    packet = {**packet,'run_result_sha256':sha(result_bytes)}
    require(packet == published, 'Complete published score envelope differs')
    return packet

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('verification-authority','original-authority','release-path','evidence-commit','run-prefix','scores-path','split','owner','output'): parser.add_argument('--'+option,required=True)
    parser.add_argument('--permit-holdout',action='store_true'); args = parser.parse_args()
    original.split_gate(args.split,args.permit_holdout)
    require(not git('status','--porcelain').strip(), 'Freeze reviewer helper before reproduction')
    require(re.fullmatch('[0-9a-f]{40}',args.verification_authority), 'Exact separate verification authority required')
    git('cat-file','-e',args.verification_authority+'^{commit}')
    core = check_core(); authority = GitBlobs(args.original_authority); evidence = GitBlobs(args.evidence_commit); p = protocol()
    release_path = relative(args.release_path); require(release_path.startswith('docs/coordination/WP-0007/'), 'Coordinator release path required')
    r = json.loads(authority(release_path)); prefix = relative(args.run_prefix); result_bytes = evidence(prefix+'/run-result.json'); result = json.loads(result_bytes); plan = json.loads(evidence(prefix+'/plan.json'))
    lineage = validate_lineage(r,result,plan,args.original_authority,release_path,p,args.split,args.owner)
    prior_reads = verify_prior_recovery(r,p); packet,checks = reproduce(evidence,prefix,result,p,r,args.permit_holdout)
    reproduced = verify_envelope(packet,json.loads(evidence(args.scores_path)),result_bytes)
    report = {'binding':vars(args),'reviewer_head':git('rev-parse','HEAD').decode().strip(),'original_runtime_lineage':lineage,'pure_core':core,
        'same_code_score_reproduction_equal':True,'independent_numeric_accounting_passed':True,'checks':checks,'reproduced':reproduced,
        'original_runtime_status':{k:result.get(k) for k in ('failure','supervisor_error','secondary_errors','finalization_errors','final_observation_status','child_launcher_pid','child_returncode','observed_child_exit','elapsed_s','owned_bytes_after','free_bytes_after')},
        'immutable_artifacts_read':authority.reads+evidence.reads+prior_reads,
        'limits':'Offline exact accepted pure-function reproduction, not author CLI execution. Original authority/source/review and reviewer verification are separate. Timing/memory remain archived observations. Supplemental scores never replace primary scores. Content/model access requires separate explicit coordinator authority; flags do not grant it.'}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out: json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'equal':True,'documents':len(reproduced['scores']),'source':r['source_commit'],'output':args.output}))

if __name__ == '__main__': main()
