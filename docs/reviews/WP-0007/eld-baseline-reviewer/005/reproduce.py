"""WP-0007 offline reviewer reproduction from completed immutable Git evidence.

Invoke only under the coordinator's separately bound reproduction command. This is
not an author runtime release validator and never calls the live score-run CLI.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, re, subprocess, sys
from fractions import Fraction
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[5]
HERE=ROOT/'qualification/baseline'
SOURCE='f807e0ac737df4e9e0aeeb96f716afec57f58ff6'
TREE='df44162c62641596032df04bc834754da38a5f7b'
REVIEW='8c208273c2524b0253b046159178a9f5e6788049'
sys.path.insert(0,str(HERE))
from baseline import prediction
from corpus import expected_for,reference_for,load_json,sha
from score import score_document,summarize
from release import protocol,schedule,REVIEW_PATH

def require(ok,detail):
    if not ok:raise ValueError(detail)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def oid(revision,path):return git('rev-parse',revision+':'+path).decode().strip()
def relative(path):
    p=PurePosixPath(path.replace('\\','/'))
    require(not p.is_absolute() and '..' not in p.parts and ':' not in str(p),'Unsafe evidence path')
    return str(p)
class GitBlobs:
    def __init__(self,revision):
        require(bool(re.fullmatch('[0-9a-f]{40}',revision)),'Exact evidence commit required')
        self.revision=revision;self.files={};self.reads=[]
        for row in git('ls-tree','-rz',revision).split(b'\0'):
            if row:
                meta,name=row.split(b'\t',1);self.files[name.decode()]=meta.decode().split()[2]
    def __call__(self,path):
        path=relative(path);blob=self.files[path];data=git('cat-file','blob',blob)
        self.reads.append({'path':path,'blob':blob,'bytes':len(data),'sha256':sha(data)})
        return data

def split_gate(split,permit_holdout):
    require(split in ('dev','eval_holdout'),'Unknown split')
    if split=='eval_holdout' and not permit_holdout:raise PermissionError('Separate coordinator holdout permission required')

def validate_original(r,result,plan,original_authority,release_path,p):
    require(r['owner']=='author' and r['source_commit']==SOURCE and r['source_tree']==TREE,'Original author/source binding')
    require(r['accepted_review_commit']==REVIEW and r['accepted_review_path']==REVIEW_PATH,'Original accepted review binding')
    require(result['release']==r and plan['release']==r,'Original release/result/plan differ')
    require(result['executing_head']==plan['executing_head']==r['executing_head'],'Original executing HEAD differs')
    require(plan['authority_commit']==original_authority and plan['release_path']==release_path,'Original authority differs')
    require(oid(r['executing_head'],'qualification/baseline')==TREE and oid('HEAD','qualification/baseline')==TREE,'Exact source tree differs')
    for key,path in [('protocol_sha256',HERE/'protocol.json'),('mapping_sha256',HERE/'mapping.json'),('lock_sha256',ROOT/p['dependency_lock_path'])]:
        require(r[key]==sha(path.read_bytes()),'Original digest mismatch: '+key)
    require(oid('HEAD','qualification/q0/harness/q0harness')==p['q0_core_tree'],'Accepted Q0 tree differs')
    require(sha((ROOT/'evaluation/manifests/corpus-manifest.json').read_bytes())==p['corpus_manifest_sha256'],'Corpus metadata differs')

def validate_schedule(calls,p,split):
    plan=schedule(p,split)
    require([{k:c[k] for k in ('fixture_id','kind','excluded')} for c in calls]==plan,'Missing, duplicated, reordered or spurious planned call')
    require(all(c['status'] in ('completed','failed','not_run_after_failure') for c in calls),'Unknown completion status')
    stopped=False
    for c in calls:
        require(not (stopped and c['status']=='completed'),'Completion after first failed/unexecuted call')
        stopped |= c['status']!='completed'
    return plan

def retained(read,base,record):
    name=relative(record['name']);require('/' not in name,'Evidence filename escapes observation directory')
    data=read(base+'/'+name)
    require(sha(data)==record['sha256_written'] and len(data)==record['bytes_written'],'Retained output digest/length mismatch')
    if not record['truncated_by_writer']:require(sha(data)==record['full_sha256'] and len(data)==record['full_bytes'],'Full output binding differs')
    return data

def accounting(s,e):
    totals={'fields':len(e['expected_fields']),'cells':sum(len(r['cells']) for t in e['expected_tables'] for r in t['rows']),
            'rows':sum(len(t['rows']) for t in e['expected_tables']),'expected_absences':len(e['expected_absences']),
            'page_count':1,'page_sentinels':len(e['page_sentinels']),'adjacency':len(e['expected_adjacent_page_pairs']),'cross_page_links':len(e['cross_page_links'])}
    totals.update(normalized_fields=totals['fields'],normalized_cells=totals['cells'])
    for key,total in totals.items():
        metric=s[key];require(metric['total']==total and 0<=metric['correct']<=total,'Item denominator/numerator: '+key)
        require(metric['rate']==(metric['correct']/total if total else None),'Item rate: '+key)
        if not s['eligible_for_exact_credit']:require(metric['correct']==0,'Ineligible document gained credit: '+key)
    for key in ('fields','cells','normalized_fields','normalized_cells'):
        require(s[key]['correct']==sum(bool(d['credited_exact']) for d in s[key]['details']),'Detail credit sum: '+key)
    require(s['expected_absences']['violations']==sum(bool(a['violation']) for a in s['expected_absences']['details']),'Absence violation sum')
    require(s['expected_absences']['surplus_candidates']==sum(max(0,a['candidate_count']-1) for a in s['expected_absences']['details']),'Absence surplus sum')
    require(all(s['cells'][k]>=0 for k in ('extra_rows','extra_cells','missing_rows')) and s['fields']['unmatched_candidates']>=0,'Negative excess/missing count')
    require(s['mapping_coverage']['expected_fields']==totals['fields'] and s['mapping_coverage']['expected_cells']==totals['cells'],'Mapping denominators')
    return totals

def independent_means(scores,summary):
    def rate(s,key):
        if key=='text_error_rate':return s['text']['error_rate']
        return float(Fraction(s[key]['correct'],s[key]['total'])) if s[key]['total'] else None
    def mean(values):
        values=[v for v in values if v is not None]
        return sum(values)/len(values) if values else None
    def equal(a,b):return a is b if a is None or b is None else math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12)
    for split,report in summary.items():
        docs=[s for s in scores if s['split']==split]
        require(report['document_denominator']==len(docs) and report['completed_documents']==sum(s['completion']=='completed' for s in docs),'Split document counts')
        for metric in report['family_macro']:
            for family,data in report['families'].items():
                require(equal(data['metrics'][metric]['mean'],mean([rate(s,metric) for s in docs if s['family_id']==family])),'Independent family mean')
            require(equal(report['family_macro'][metric]['mean'],mean([d['metrics'][metric]['mean'] for d in report['families'].values()])),'Independent split family macro')
            for variant,data in report['variants'].items():
                subset=[s for s in docs if s['variant_kind']==variant]
                values=[mean([rate(s,metric) for s in subset if s['family_id']==fam]) for fam in {s['family_id'] for s in subset}]
                require(equal(data['family_macro'][metric]['mean'],mean(values)),'Independent variant family macro')

def reproduce(read,run_prefix,result,p,split,permit_holdout=False):
    split_gate(split,permit_holdout);validate_schedule(result['calls'],p,split)
    rules=load_json(HERE/'mapping.json');by_id={f['fixture_id']:f for f in p['fixtures']};scores=[];observations=[];checks=[]
    for call in result['calls']:
        f=by_id[call['fixture_id']];raw=b'';obs=None
        if call['observation']:
            path=run_prefix+'/'+relative(call['observation']);obs=json.loads(read(path));base=str(PurePosixPath(path).parent)
            require(obs['fixture_id']==f['fixture_id'] and obs['page_count_in']==f['page_count'] and obs['kind']==call['kind'],'Observation fixture/kind/pages differ')
            require(obs['label']==f['fixture_id']+'.'+call['kind'] and obs['excluded_from_warm_statistics']==call['excluded'],'Observation label/exclusion differ')
            kwargs={**p['call']['fixed_kwargs'],'max_new_tokens':8000*f['page_count'],'ngram_window':1024 if f['page_count']>1 else 128}
            require(obs['call_kwargs']==kwargs,'Frozen native call settings differ')
            if 'raw_output' in obs:
                raw=retained(read,base,obs['raw_output'])
                require(obs['native']['text_sha256']==obs['raw_output']['full_sha256'],'Native/raw text identity differs')
                tokens=json.loads(retained(read,base,obs['token_ids_file']))
                require(sha(json.dumps(tokens).encode())==obs['native']['token_ids_sha256'] and len(tokens)==obs['native']['output_tokens'],'Native token identity/count differs')
            if call['status']=='completed':
                require(raw and not obs.get('flags') and not obs.get('error') and not obs['raw_output']['truncated_by_writer'],'Completed call has missing/failed raw')
                require(obs['native']['finish_reason']=='stop' and obs['native']['num_pages_out']==f['page_count'],'Completed finish/pages differ')
            observations.append({'fixture_id':f['fixture_id'],'kind':call['kind'],'observation_sha256':sha(read(path)),
                **{k:obs.get(k) for k in ('timing','cuda_memory','host_memory','prefill_memory','kernel_path','page_markers','error','flags')}})
        else:require(call['status']!='completed','Completed call lacks observation')
        if call['excluded']:continue
        e=expected_for(f,permit_holdout);ref=reference_for(f,permit_holdout)
        s=score_document(prediction(raw.decode('utf-8'),rules),e,ref,call['status']);s['raw_sha256']=sha(raw)
        checks.append({'fixture_id':f['fixture_id'],'totals':accounting(s,e)});scores.append(s)
    summary=summarize(scores);independent_means(scores,summary)
    return {'scores':scores,'summary':summary}, {'accounting':checks,'observations':observations,'completion_counts':dict(collections.Counter(c['status'] for c in result['calls'] if not c['excluded']))}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ('verification-authority','original-authority','release-path','evidence-commit','run-prefix','scores-path','split','output'):parser.add_argument('--'+option,required=True)
    parser.add_argument('--permit-holdout',action='store_true');args=parser.parse_args()
    split_gate(args.split,args.permit_holdout)
    require(not git('status','--porcelain').strip(),'Reviewer worktree must be clean before reproduction')
    require(bool(re.fullmatch('[0-9a-f]{40}',args.verification_authority)),'Exact separate coordinator verification authority required')
    git('cat-file','-e',args.verification_authority+'^{commit}')
    authority=GitBlobs(args.original_authority);evidence=GitBlobs(args.evidence_commit);p=protocol()
    r=json.loads(authority(args.release_path));require(r['split']==args.split and (args.split=='dev' or r['allow_test_content'] is True),'Original split permission differs')
    prefix=relative(args.run_prefix);result_bytes=evidence(prefix+'/run-result.json');result=json.loads(result_bytes);plan=json.loads(evidence(prefix+'/plan.json'))
    validate_original(r,result,plan,args.original_authority,args.release_path,p)
    require(plan['calls']==schedule(p,args.split),'Parent plan differs from frozen schedule')
    reproduced,checks=reproduce(evidence,prefix,result,p,args.split,args.permit_holdout)
    reproduced['run_result_sha256']=sha(result_bytes);published=json.loads(evidence(args.scores_path))
    require(reproduced==published,'Published per-document scores or aggregates differ from exact reproduction')
    report={'original_binding':vars(args),'reviewer_head':git('rev-parse','HEAD').decode().strip(),'accepted_source':SOURCE,'source_tree':TREE,
        'same_code_score_reproduction_equal':True,'independent_numeric_accounting_passed':True,'checks':checks,'reproduced':reproduced,
        'original_runtime_status':{k:result.get(k) for k in ('failure','child_launcher_pid','child_returncode','observed_child_exit','elapsed_s','owned_bytes_after','free_bytes_after')},
        'immutable_artifacts_read':authority.reads+evidence.reads,'limit':'Timing/memory are retained observations, not independently rerun measurements. Model sentinels require a separate GPU release. Verification authority is recorded from the explicit coordinator assignment; no author runtime CLI is invoked.'}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'documents':len(reproduced['scores']),'equal':True,'output':args.output}))

if __name__=='__main__':main()
